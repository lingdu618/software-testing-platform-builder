# Field Mapping Conventions

## 严重程度 / 优先级 / 状态 — **全局唯一字典**

位置：`frontend/src/constants.js`

```js
// === 严重程度（对齐禅道 1-4）===
export const SEV_LABELS = {
  fatal: '致命', serious: '严重', major: '一般', minor: '轻微'
}
export const SEV_TYPES = {  // el-tag type
  fatal: 'danger', serious: 'warning', major: 'primary', minor: 'info'
}
// 排序：致命最前
export const SEV_RANK = { fatal: 0, serious: 1, major: 2, minor: 3 }
export const SEVERITY_OPTIONS = [
  { value: 'fatal', label: '致命' },
  { value: 'serious', label: '严重' },
  { value: 'major', label: '一般' },
  { value: 'minor', label: '轻微' },
]

// === 优先级 ===
export const PRI_LABELS = { urgent:'紧急', high:'高', mid:'中', low:'低' }
export const PRI_TYPES  = { urgent:'danger', high:'warning', mid:'primary', low:'info' }
export const PRIORITY_OPTIONS = [
  { value: 'urgent', label: '紧急' },
  { value: 'high', label: '高' },
  { value: 'mid', label: '中' },
  { value: 'low', label: '低' },
]

// === 缺陷状态 ===
export const DEFECT_STATUS_LABELS = { open:'未关闭', resolved:'已解决', closed:'已关闭' }
export const DEFECT_STATUS_TYPES  = { open:'danger', resolved:'warning', closed:'success' }
export const DEFECT_STATUS_OPTIONS = [
  { value: 'open', label: '未关闭' },
  { value: 'resolved', label: '已解决' },
  { value: 'closed', label: '已关闭' },
]
// 排序：未关闭最前
export const STATUS_RANK = { open: 0, resolved: 1, closed: 2 }

// helper
export function sevLabel(s) { return SEV_LABELS[s] || s || '-' }
export function sevType(s) { return SEV_TYPES[s] || 'info' }
// ... priLabel/priType/defectStatusLabel/defectStatusType 同理
```

## 严禁

- ❌ 在视图里再写一遍 `{fatal:'致命', serious:'严重', ...}` —— 改全局时容易漏
- ❌ 在组件 props 里硬编码 `'致命' / '严重'` 字面量
- ❌ 用 `SEV.get(raw, 'major')` 处理禅道返回（字符串 `"2"` 会落到 default 失真）

## 禅道等级 → 平台编码（后端）

位置：`backend/app/routers/zentao.py`

```python
SEV = {1: "fatal", 2: "serious", 3: "major", 4: "minor"}
PRI = {1: "urgent", 2: "high", 3: "mid", 4: "low"}
ST  = {"active": "open", "resolved": "resolved", "closed": "closed"}
SEV_CODES = {"fatal", "serious", "major", "minor", "suggestion"}
PRI_CODES = {"urgent", "high", "mid", "low"}

def _level(raw):
    """兼容 int / "2" / " 2 " / 越界等级，归一为 1-4 整数。"""
    if raw is None or raw == "" or isinstance(raw, bool):
        return None
    try: n = int(str(raw).strip())
    except (TypeError, ValueError): return None
    return min(4, max(1, n))   # 越界向最近有效等级收敛

def _map_level(raw, table, code_set, default):
    lv = _level(raw)
    if lv is not None: return table[lv]
    # 兼容已是平台内部编码的入参（例如再次导入）
    s = str(raw).strip().lower()
    return s if s in code_set else default
```

## 全局改名规范

平台 brand 调整时（如"蓝牙专项综合测试管理平台"→"软件专项测试平台"）：

| 改 | 不改 |
|---|---|
| 主标题/页面 H1/菜单 meta.title/按钮文字/卡片头 | API 路径（`/api/bluetooth/...`） |
| 报告标题（gen_report.py） | 数据库表名/列名/路由文件 |
| README.md 标题/简介/功能表 | SQLAlchemy 关系名（如 `bluetooth_tests`） |
| 启动脚本提示文本 | Vue 组件名/变量名 |
| Login 副标题、metrics 卡片文字 | |

```bash
# 全局搜索需要改的字符串
cd frontend/src
grep -rn "蓝牙专项综合测试管理平台" .   # 应该 0 结果
grep -rn "蓝牙专项" .                    # 应该 0 结果（"蓝牙兼容专项测试"除外）
```

## 字段命名约定（数据库）

- 表名用复数：`projects` / `devices` / `test_plans` / `test_results` / `bluetooth_tests` / `defects`
- 列名用 snake_case：`project_id` / `firmware_version` / `created_at`
- 时间字段统一 `created_at` / `updated_at` / `uploaded_at`
- 外键用 `_id` 后缀：`project_id` / `device_id` / `linked_result_id`
- 布尔用 `is_*` / `enabled` / `*_success`
- JSON 字段命名 `summary` / `extra` / `metadata`

## 国际化（如果未来要 i18n）

当前所有中文文案**硬编码**在视图/常量里。要做 i18n 时：
1. 把所有中文文案提到 `frontend/src/i18n/zh.js` / `en.js`
2. 在 `constants.js` 的 `LABELS` 字典改成 `i18n.t()`
3. 后端 message 改成 `code + i18n_key` 结构，前端按 key 翻译