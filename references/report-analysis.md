# Test Report Analysis (分项目 + 智能分析)

## 核心接口

`GET /api/dashboard?project_id=<可选>`

- 不传 project_id → 全平台汇总（仪表盘 Dashboard.vue 用）
- 传 project_id → 仅该项目数据（测试报告 Report.vue 用）

## 返回结构

```json
{
  "project_id": 1, "project_name": "3039蓝牙demo",
  "counts": {"projects": 3, "devices": N, "plans": N, "results": N, "defects": N, "bluetooth": N},
  "cases": {"total": N, "passed": N, "failed": N, "skipped": N, "pass_rate": 87.5},
  "defect_status": {"open": N, "resolved": N, "closed": N},
  "defect_severity": {"fatal": N, "serious": N, "major": N, "minor": N},
  "bluetooth": {
    "latest_firmware_version": "V8",
    "connection_total": 20, "connection_pass_rate": 90.0,
    "multi_total": 20, "multi_pass_rate": 90.0,
    "avg_connection_time_ms": 95.5,
    "version_stats": [
      {"version":"V3", "conn_rate":50.0, "multi_rate":40.0, "avg":45.0, "is_latest":false},
      {"version":"V8", "conn_rate":90.0, "multi_rate":90.0, "avg":90.0, "is_latest":true}
    ]
  },
  "trend": [{"name":..., "pass_rate":..., "uploaded_at":...}],   // 时间趋势（最近 10 次结果）
  "version_trend": [...],    // 版本趋势（见 references/version-analysis.md）
  "analysis": {               // 结构化智能分析（关键）
    "health_score": 81, "grade": "良好", "grade_level": "normal",
    "summary": "项目「3039蓝牙demo」综合健康度 81 分（良好）。整体质量良好，可保持。",
    "sections": [
      {"key":"test", "title":"测试执行", "level":"warn", "text":"..."},
      {"key":"defect", "title":"缺陷状况", "level":"bad", "text":"..."},
      {"key":"bluetooth", "title":"蓝牙兼容专项测试", "level":"good",
       "text":"以最新版本「V8」为最终数据...连接稳定性 90.0%...跨版本从 45.0% 提升至 90.0%，整体改善。",
       "version_stats": [...], "latest_version": "V8"},
      {"key":"trend", "title":"版本趋势", "level":"good",
       "text":"蓝牙跨版本平均通过率从「V3」45.0% 提升至「V8」90.0%...",
       "version_trend": [...]}
    ],
    "risks": [...], "suggestions": [...]
  }
}
```

## build_analysis() 模块级函数（routers/dashboard.py）

四个维度 + 综合健康度：

### 1. 测试执行（基于 results）
- pass_rate >= 90% → good；>= 75% → warn；else → bad
- 文案：`"共 N 份测试结果、M 个用例，整体通过率 X%。通过率达标/偏低/一般..."`

### 2. 缺陷状况（基于 defects）
- 未关闭的致命/严重缺陷数 = 0 → good；<= 2 → warn；else → bad
- 健康度 = 100 - min(100, 高严重未关闭占比%)
- 风险：`"存在 N 个未关闭的高严重度缺陷，是当前最主要的质量风险。"`

### 3. 蓝牙兼容（按版本聚合，以最新版本为最终数据）
```python
def _bt_version_stats(bt):
    """按 firmware_version 分组 → 排除压测 → 标 is_latest。"""
    by_ver = {}
    for b in bt:
        v = b.firmware_version or "(未指定)"
        by_ver.setdefault(v, []).append(b)
    versions = sorted(by_ver.keys(), key=lambda v: _ver_sort_key(v, 0))
    main_versions = [v for v in versions if "压测" not in v]
    stats = []
    for v in main_versions:
        bt_v = by_ver[v]
        conn = [b for b in bt_v if b.test_type == "connection_stability"]
        multi = [b for b in bt_v if b.test_type == "multi_device_compat"]
        conn_rate = round(sum(1 for b in conn if b.result == "pass") / len(conn) * 100, 1) if conn else None
        multi_rate = round(sum(1 for b in multi if b.result == "pass") / len(multi) * 100, 1) if multi else None
        rates = [r for r in (conn_rate, multi_rate) if r is not None]
        avg = round(sum(rates) / len(rates), 1) if rates else None
        stats.append({"version": v, "conn_rate": conn_rate, "multi_rate": multi_rate, "avg": avg, "is_latest": False})
    if stats: stats[-1]["is_latest"] = True
    return stats
```

### 4. 版本趋势（基于 version_trend）
```python
vt = [v for v in version_trend if v.get("avg") is not None]
if len(vt) >= 2:
    diff = vt[-1]["avg"] - vt[0]["avg"]
    if diff > 0: lv, txt = "good", f"蓝牙跨版本平均通过率从「{vt[0]['version']}」{vt[0]['avg']}% 提升至..."
    elif diff < 0: lv, txt = "bad", f"...下滑趋势..."
    else: lv, txt = "info", f"...稳定在..."
    risks.append(...) if diff < 0
```

## 综合健康度评分

```python
score_parts = []  # 各维度健康度
score_parts.append(pass_rate)         # 测试
score_parts.append(defect_health)     # 缺陷
if avg: score_parts.append(avg)       # 蓝牙
health = round(sum(score_parts) / len(score_parts)) if score_parts else None

def _grade_label(score):
    if score is None: return ("未知", "info")
    if score >= 85: return ("优秀", "good")
    if score >= 70: return ("良好", "normal")
    if score >= 50: return ("一般", "warn")
    return ("风险", "bad")
```

## 前端 Report.vue 关键结构

```html
<el-card>整体报告分析</el-card>
  - 标题 + 健康度 Tag + 总评 Alert
  - 4 个维度子卡片（带等级色 Tag + 文字结论）
  - 风险项 / 改进建议两栏（el-alert）

<el-card>蓝牙兼容专项测试通过率（最新版本）</el-card>
  - 标题 + 最新版本 Tag + 折线图
  - 「版本通过率趋势」表格（最新版本★高亮）

<el-card>版本趋势分析</el-card>
  - 折线图（连接/多设备/测试结果/综合，4 条线）
  - 详细表格

<el-card>近期测试结果明细 / 缺陷清单</el-card>
```

前端 helper（`constants.js` 扩展）：
```js
const LEVEL_CN = { good:'达标', normal:'正常', warn:'关注', bad:'风险', info:'无数据' }
const LEVEL_TAG = { good:'success', normal:'primary', warn:'warning', bad:'danger', info:'info' }
const LEVEL_ALERT = { good:'success', normal:'success', warn:'warning', bad:'error', info:'info' }
function lvType(l) { return LEVEL_TAG[l] || 'info' }
function lvLabel(l) { return LEVEL_CN[l] || l }
function alertType(l) { return LEVEL_ALERT[l] || 'info' }
```

## 模式选择

- **Dashboard.vue**：不传 project_id → 看全平台汇总
- **Report.vue**：顶部项目选择器（含"全部项目"），切换即按项目重新生成报告
- 后端两个视图都能用同一个 `/api/dashboard`，前端参数决定