# Version Dimension Analysis

## 业务场景

测试数据按固件版本（firmware version）分组展示、对比、回归检测。版本来源通常是 Excel 的 sheet 名（如 `launcher_V3` / `launcher_V5` / `V1版本` / `更新so库+launcher_V8+APP_V8`）。

## 核心排序算法

```python
import re

def _ver_sort_key(name, idx):
    """固件版本排序：基线 sheet* → V 数字升序 → 其他 → 压测最后。"""
    n = name or ""
    m = re.search(r"(?:launcher_V|V)(\d+)(?:版本)", n)
    if m: return (1, int(m.group(1)), idx)
    if re.match(r"^sheet\d*$", n.strip(), re.I): return (0, 0, idx)
    if "压测" in n: return (3, 0, idx)
    return (2, 0, idx)

def _norm_version_name(name):
    """把默认 sheet 名（Sheet1/Sheet2...）重命名为可读版本。"""
    if not name: return name
    m = re.match(r"^sheet(\d+)$", str(name).strip(), re.I)
    if m: return f"V{m.group(1)}版本"
    return name
```

## 数据模型

测试结果 / 蓝牙测试都要有 `firmware_version` 字段（独立列，不要放 JSON 里）：

```python
class BluetoothTest(Base):
    firmware_version = Column(String(64), nullable=True, index=True)
```

Excel 解析时：
- **矩阵模式**（测试项×设备）：sheet 名 → firmware_version
- **扁平模式**（一行一条记录）：读 "固件版本" 列中文/英文别名

```python
COL_ALIASES = {
    "固件版本": "firmware_version",
    "firmware": "firmware_version",
    "firmware_version": "firmware_version",
}
```

## 版本维度分析接口

```python
# routers/results.py
@router.get("/{rid}/version-analysis")
def version_analysis(rid: int, ...):
    """按固件版本（Excel sheet 名）做版本维度分析：
    每个版本的问题清单、通过率、版本×测试项矩阵、跨版本回归/修复检测、自动总结。"""
    obj = db.query(TestResult).filter(TestResult.id == rid).first()
    summary = obj.summary or []

    by_ver = {}
    for row in summary:
        v = _norm_version_name((row.get("extra") or {}).get("固件版本") or "(未命名)")
        by_ver.setdefault(v, []).append(row)

    versions_sorted = sorted(by_ver.keys(), key=lambda v: _ver_sort_key(v, order_index[v]))
    # ... 构建版本×测试项矩阵 + 检测回归/修复
    return {
        "versions": [{"name": v, "stats": ...} for v in versions_sorted],
        "matrix": [["测试项×版本" 二维数据"], ...],
        "regression": [...],   # 首版通过 → 最新版失败
        "fixed": [...],        # 首版失败 → 最新版通过
        "summary": "中文自动总结",
    }
```

## 跨版本健康度检测

```python
# 取每个版本的 pass/fail 集合
def detect_changes(first_ver, latest_v):
    regression, fixed = [], []
    for item, cells in matrix.items():
        first = _agg_status(cells_by_ver[first_ver][item])
        latest = _agg_status(cells_by_ver[latest_v][item])
        if first == "pass" and latest in ("fail", "partial"):
            regression.append(item)
        if first in ("fail", "partial") and latest == "pass":
            fixed.append(item)
    return regression, fixed
```

## 测试报告中的版本趋势

`/api/dashboard` 聚合 `version_trend`：

```python
bt_v_stats = _bt_version_stats(bt)  # 每个固件版本的连接/多设备通过率
test_by_ver = {}                    # 每个固件版本的测试结果通过率
for r in results:
    for row in r.summary or []:
        fw = ((row.get("extra") or {}).get("固件版本")) or "(未指定)"
        test_by_ver.setdefault(fw, {"total":0, "passed":0})
        test_by_ver[fw]["total"] += row.get("total") or 0
        test_by_ver[fw]["passed"] += row.get("passed") or 0

# 合并去压测、按 _ver_sort_key 排序
version_trend = []
for v in sorted(all_versions, key=lambda v: _ver_sort_key(v, 0)):
    if "压测" in v: continue
    bt_entry = next((s for s in bt_v_stats if s["version"] == v), None)
    test_entry = test_by_ver.get(v)
    ...
    version_trend.append({
        "version": v,
        "is_latest": v == bt_latest_version,
        "bt_conn_rate": ..., "bt_multi_rate": ..., "bt_avg": ...,
        "test_pass_rate": ...,
        "avg": ...
    })
```

## 趋势分析文案

```python
# 用 version_trend 做跨版本趋势（替代时间趋势）
vt = [v for v in version_trend if v.get("avg") is not None]
if len(vt) >= 2:
    first_v = vt[0]; cur_v = vt[-1]
    diff = cur_v["avg"] - first_v["avg"]
    if diff > 0:
        text = f"蓝牙跨版本平均通过率从「{first_v['version']}」{first_v['avg']}% 提升至「{cur_v['version']}」{cur_v['avg']}%，整体呈上升（改善）趋势。"
    elif diff < 0:
        text = f"... 呈下滑趋势，需警惕。"
        # 风险也加上
        risks.append(f"蓝牙平均通过率跨版本下滑...")
```

## 前端展示

- **矩阵视图**：`<el-tabs>` 按版本切换，行=测试项，列=设备（✓/✗）
- **趋势图**：折线图，X 轴版本，Y 轴 0-100%，多条线（连接/多设备/测试结果/综合）
- **最新版本标 ★**：用 `:style="row.is_latest ? 'color:#67c23a;font-weight:600' : ''"`