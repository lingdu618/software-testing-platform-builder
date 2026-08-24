# ZenTao (禅道) Integration

## Open API v1 基础

- 文档：禅道 OpenAPI v1（基于 token 鉴权）
- 根地址：`http://host:port/zentao`（**必须是根目录，不能填登录页 URL**）
- 登录：`POST /api.php/v1/tokens`，body `{account, password}` → **HTTP 201** + `{token, ...}`

### 坑位 1：登录返回码是 201，不是 200

```python
# services/zentao.py
if resp.status_code in (200, 201):  # 两个都算成功
    return resp.json()
raise ZenTaoError(...)
```

### 坑位 2：base_url 必须能正常裁剪到根目录

`POST /api.php/v1/tokens` 的完整 URL 是 `f"{base}/api.php/v1/tokens"`，如果 base 填了 `http://x/zentao/user-login.html` 会拼成错误的路径。后端启动时可加自动裁剪：

```python
# 收到 base_url 后
import re
m = re.search(r'^(.*?/zentao)', base_url)
if m: base_url = m.group(1)
```

### 坑位 3：错误账密返回 HTTP 400，不是 401

响应体 `{"error": "登录失败..."}`。区分成功（201）和失败（400）。

## ZenTaoClient 实现要点

```python
class ZenTaoClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.token = None

    def auth(self):
        resp = httpx.post(f"{self.base_url}/api.php/v1/tokens",
                          json={"account": self.username, "password": self.password})
        if resp.status_code not in (200, 201):
            raise ZenTaoError(f"登录失败 HTTP {resp.status_code}")
        self.token = resp.json()["token"]

    def _get(self, path):
        if not self.token:
            self.auth()
        headers = {"Token": self.token}  # 鉴权头是 Token 不是 Authorization
        return httpx.get(f"{self.base_url}{path}", headers=headers)
```

## 字段映射（**最坑的部分**）

禅道 severity/pri 返回值可能是：
- 整数 `1` / `2` / `3` / `4`
- 字符串 `"2"` / `" 2 "`
- 自定义等级（可能越界到 `5`、`6`）

必须统一归一：

```python
SEV = {1: "fatal", 2: "serious", 3: "major", 4: "minor"}
PRI = {1: "urgent", 2: "high", 3: "mid", 4: "low"}
ST = {"active": "open", "resolved": "resolved", "closed": "closed"}

def _level(raw):
    """兼容 int / str / 带空格，归一到 1-4 整数。"""
    if raw is None or raw == "" or isinstance(raw, bool): return None
    try: n = int(str(raw).strip())
    except: return None
    return min(4, max(1, n))  # 越界向最近有效等级收敛

def _map_level(raw, table, code_set, default):
    lv = _level(raw)
    if lv is not None: return table[lv]
    # 兼容已是平台内部编码的入参
    s = str(raw).strip().lower()
    return s if s in code_set else default
```

**禁止**用 `SEV.get(raw, default)` —— 字符串 `"2"` 会落到 default 造成失真。

## 模块级 helper（routers/zentao.py）

```python
def _map_zentao_bug_fields(b):
    """返回 {severity, priority, status, title}，import-bugs 与 sync-from-zentao 共用。"""
    return {
        "severity": _map_level(b.get("severity"), SEV, SEV_CODES, "major"),
        "priority": _map_level(b.get("pri"), PRI, PRI_CODES, "mid"),
        "status":   ST.get(b.get("status"), "open"),
        "title":    (b.get("title") or "").strip(),
    }
```

## 主要接口（routers/zentao.py）

| 路由 | 方法 | 功能 |
|---|---|---|
| `/api/zentao/config` | GET/PUT | 禅道配置（base_url/username/password/enabled） |
| `/api/zentao/test-connection` | POST | 测通并记录 last_sync_at |
| `/api/zentao/products` | GET | 产品列表（检索 bug 时选定产品） |
| `/api/zentao/bugs`?keyword=&product_id=&limit=&status= | GET | 检索 bug；status 默认 `all`，可传 `active`/`resolved`/`closed` |
| `/api/zentao/bugs/{bug_id}` | GET | 单 bug 详情 |
| `/api/zentao/import-bugs` | POST | 批量导入到 Defect |

## 缺陷同步（sync-from-zentao）

放在 **`defects.py`**（不是 zentao.py —— 因为操作的是 Defect 表，前端习惯调 `/api/defects/...`）：

```python
@router.post("/sync-from-zentao")
def sync_from_zentao(body: dict = None, ...):
    """body: { project_id?: int, defect_ids?: [int] }
    只同步本地 zentao_bug_id 非空的缺陷，逐条拉禅道覆盖 severity/priority/status/title。
    禅道 404 的归入 not_found（不删本地，保护已闭环历史数据）。"""
    cfg = ...  # ZenTaoConfig 单例
    client = ZenTaoClient(cfg.base_url, cfg.username, cfg.password)
    q = db.query(Defect).filter(Defect.zentao_bug_id.isnot(None))
    if body.get("project_id"): q = q.filter(Defect.project_id == body["project_id"])
    if body.get("defect_ids"): q = q.filter(Defect.id.in_(body["defect_ids"]))
    for d in q.all():
        try:
            bug = client.get_bug(int(d.zentao_bug_id))
        except ZenTaoError as e:
            if "404" in str(e): not_found.append(d.zentao_bug_id)
            else: errors.append({"zentao_bug_id": d.zentao_bug_id, "msg": str(e)})
            continue
        fields = _map_zentao_bug_fields(bug)
        # 仅 changed 才计入 updated
        ...
    cfg.last_sync_at = datetime.now(timezone.utc); db.commit()
    return {"scanned": ..., "synced": ..., "updated": ..., "not_found": ..., "errors": [...]}
```

## 性能提示

顺序拉禅道单 bug GET：~0.5s/bug。100 条约 50 秒。前端 axios 默认 timeout 5s 不够，**必须传 timeout=180000**。后续可改 asyncio.gather 并发。

## 集成测试模板

每次新加禅道相关功能，写一个 `verify_xxx.py`：
1. login 拿 token
2. 测 connection
3. 检索/导入/同步测试数据
4. 验证 DB 落库正确
5. 完成后 `mv verify_xxx.py .offline_tmp/`