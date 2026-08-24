# Bluetooth Test Matrix Import

## 业务场景

导入"测试项 × 设备型号"矩阵（如用户提供的兼容测试模板）。每个非空单元格记一条 `BluetoothTest`，方便按固件版本/测试项/机型查看。

## Excel 结构

```
sheet 名（如 launcher_V3 / V8 / V1版本） → firmware_version
第 1 行：表头（测试项 | 预期结果 | 设备1 | 设备2 | ...）
后续行：每个测试项一行，每列是一个设备型号在该测试项下的结果
```

### 单元格判定

| 单元格内容 | result |
|---|---|
| `PASS` / `pass` / `通过` | `pass` |
| `FAIL` / `fail` / `不通过` / 其它 | `fail` |
| 空 | 跳过（不生成记录） |

## 导入流程（routers/bluetooth.py）

```python
@router.post("/upload", response_model=dict)
async def upload_bt(project_id: int, file: UploadFile = File(...), ...):
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj: raise HTTPException(404, "项目不存在")
    raw = await file.read()
    fname = file.filename or "bt.csv"
    
    mode = "flat"  # 或 "matrix"
    if fname.endswith((".xlsx", ".xls")):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        for ws in wb.worksheets:
            ws_rows = [...]
            if len(ws_rows) < 2: continue
            hdr = [str(c).strip() for c in ws_rows[0]]
            # 判断模式：是否有"测试项"列
            if _is_bt_matrix_header(hdr):
                mode = "matrix"
                _convert_matrix_to_bt(ws_rows, project_id, db, sheet_title=ws.title)
            else:
                _convert_flat_to_bt(ws_rows, project_id, db)
    elif fname.endswith(".csv"):
        rows = list(csv.reader(io.StringIO(raw.decode("utf-8"))))
        ...
    elif fname.endswith(".json"):
        bugs = json.loads(raw)
        ...
    
    db.commit()
    return {"imported": imported, "mode": mode}
```

## 矩阵转换核心

```python
def _is_bt_matrix_header(header):
    cells = [str(h).strip().lower() for h in header if h]
    has_name = any(k in cells for k in ("测试项", "用例", "测试名称"))
    return has_name and len(cells) >= 3

def _convert_matrix_to_bt(raw_rows, project_id, db):
    """每个非空单元格生成一条 BluetoothTest。"""
    hdr = [str(c).strip() for c in raw_rows[0]]
    # 找"测试项"列
    name_col = next(i for i, h in enumerate(hdr) if h in _NAME_HEADERS)
    # 后续列都是设备
    device_cols = [(i, h) for i, h in enumerate(hdr) if i > name_col and h]
    
    # sheet 名作为 firmware_version
    fw_version = _norm_version_name(sheet_title)
    
    for row in raw_rows[1:]:
        item_name = (row[name_col] or "").strip()
        if not item_name: continue
        for ci, dev_name in device_cols:
            cell = row[ci] if ci < len(row) else None
            if cell is None or str(cell).strip() == "": continue
            result = "pass" if str(cell).strip().upper() in ("PASS", "通过", "P") else "fail"
            dev_id = _get_or_create_device(db, project_id, dev_name)
            db.add(BluetoothTest(
                project_id=project_id,
                firmware_version=fw_version,
                test_type="multi_device_compat",   # 矩阵导入统一为多设备兼容
                device_id=dev_id,
                scenario=item_name,
                result=result,
                notes=f"矩阵导入: {item_name} × {dev_name}",
            ))

def _get_or_create_device(db, project_id, name):
    dev = db.query(Device).filter_by(project_id=project_id, name=name).first()
    if not dev:
        dev = Device(project_id=project_id, name=name, device_type="参考机")
        db.add(dev); db.flush()
    return dev.id
```

## 扁平模式（CSV/JSON/单 sheet Excel）

走"一行一条记录"模式，列名用别名映射：

```python
COL_ALIASES = {
    "device_id": "device_id", "设备id": "device_id", "设备编号": "device_id",
    "test_type": "test_type", "类型": "test_type", "测试类型": "test_type",
    "scenario": "scenario", "场景": "scenario",
    "connection_time_ms": "connection_time_ms", "连接耗时": "connection_time_ms",
    "pairing_success": "pairing_success", "配对成功": "pairing_success",
    "reconnect_count": "reconnect_count", "重连次数": "reconnect_count",
    "reconnect_failures": "reconnect_failures", "重连失败": "reconnect_failures",
    "interference_level": "interference_level", "干扰": "interference_level",
    "co_device_count": "co_device_count", "共存设备数": "co_device_count",
    "co_device_failures": "co_device_failures", "共存失败": "co_device_failures",
    "result": "result", "结果": "result",
    "notes": "notes", "备注": "notes", "说明": "notes",
    "operator": "operator", "操作人": "operator", "测试人": "operator",
}

TT_MAP = {
    "连接稳定性": "connection_stability",
    "多设备兼容": "multi_device_compat",
    "兼容性": "multi_device_compat",
}
```

## 矩阵视图接口

```python
@router.get("/matrix")
def get_matrix(project_id: int = None, db: Session = Depends(get_db), ...):
    """返回 {versions:[{firmware_version, items, devices, cells, stats}]}"""
    q = db.query(BluetoothTest).filter(BluetoothTest.test_type == "multi_device_compat")
    if project_id: q = q.filter(BluetoothTest.project_id == project_id)
    
    by_ver = {}
    for b in q.all():
        v = b.firmware_version or "(未指定)"
        by_ver.setdefault(v, {"items": set(), "devices": set(), "cells": {}})
        by_ver[v]["items"].add(b.scenario or "")
        if b.device_id:
            dev = db.query(Device).filter(Device.id == b.device_id).first()
            if dev: by_ver[v]["devices"].add(dev.name)
        key = (b.scenario or "", dev.name if dev else "")
        by_ver[v]["cells"][key] = {"result": b.result, "notes": b.notes}
    
    versions = []
    for v, data in by_ver.items():
        items = sorted(data["items"]); devices = sorted(data["devices"])
        passed = sum(1 for c in data["cells"].values() if c["result"] == "pass")
        failed = sum(1 for c in data["cells"].values() if c["result"] == "fail")
        versions.append({
            "firmware_version": v,
            "items": items, "devices": devices, "cells": data["cells"],
            "stats": {"total": passed+failed, "passed": passed, "failed": failed}
        })
    versions.sort(key=lambda x: _ver_sort_key(x["firmware_version"], 0))
    return {"versions": versions}
```

## 批量删除（注意路由顺序）

```python
@router.delete("/bulk")     # ← 必须先注册
def bulk_delete(project_id: int, firmware_version: str = None,
                test_type: str = None, ...):
    q = db.query(BluetoothTest).filter(BluetoothTest.project_id == project_id)
    if firmware_version: q = q.filter(BluetoothTest.firmware_version == firmware_version)
    if test_type: q = q.filter(BluetoothTest.test_type == test_type)
    deleted = 0
    device_ids_to_check = set()
    for b in q.all():
        if b.device_id: device_ids_to_check.add(b.device_id)
        db.delete(b); deleted += 1
    db.commit()
    # 自动清理无关联的"参考机"
    devices_deleted = 0
    for did in device_ids_to_check:
        remaining = db.query(BluetoothTest).filter(BluetoothTest.device_id == did).count()
        if remaining == 0:
            dev = db.query(Device).filter(Device.id == did).first()
            if dev and dev.device_type == "参考机":
                db.delete(dev); devices_deleted += 1
    db.commit()
    return {"deleted": deleted, "devices_deleted": devices_deleted}

@router.get("/{bid}")       # ← 后注册
def get_one(bid: int, ...): ...
```

## 前端要点

- 顶部项目选择器（**projFilter**）必须正确传入 upload 接口，否则导入到错误项目
- 矩阵视图用 `<el-tabs>` 按版本切换，行=测试项，列=设备，单元格 ✓/✗/—
- "删除该版本"按钮调用 `bulkDelete({project_id, firmware_version, test_type:'multi_device_compat'})`
- "清空本项目数据"按钮调用 `bulkDelete({project_id})`
- 上传前确认对话框：显示「将导入到：[项目名]」让用户二次确认

## 已知坑

1. **openpyxl read_only=True**：大数据 Excel 用 `read_only=True` 但要小心行顺序，必要时用 `data_only=True` 读公式计算结果
2. **sheet 名**：可能是中文 / 含特殊字符；用 `_norm_version_name()` 归一化
3. **空白单元格**：`cell is None or str(cell).strip() == ""` 都要跳过
4. **设备自动创建**：矩阵导入的设备会作为"参考机"自动建表；删除蓝牙数据时连带清理无关联参考机