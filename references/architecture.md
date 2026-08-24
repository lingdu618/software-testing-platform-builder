# Architecture & Database Schema

## Core entities

```
Project (1) ──< (N) Device
Project (1) ──< (N) TestPlan ──< (N) TestResult (含 summary JSON + extra.固件版本)
Project (1) ──< (N) BluetoothTest (含 firmware_version 字段)
Project (1) ──< (N) Defect (含 zentao_bug_id / zentao_url)

User (1) ──< (N) TestResult / Defect (created_by)
ZenTaoConfig (单例表) — base_url / username / password / enabled / last_sync_at
```

## Key model definitions

```python
# backend/app/models.py
class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), unique=True, nullable=False)
    description = Column(String(500))
    # 关联 — **必须带 cascade**，否则删除会因 NOT NULL project_id 崩
    devices = relationship("Device", back_populates="project", cascade="all, delete-orphan")
    plans = relationship("TestPlan", back_populates="project", cascade="all, delete-orphan")
    bluetooth_tests = relationship("BluetoothTest", back_populates="project",
                                   cascade="all, delete-orphan")
    defects = relationship("Defect", back_populates="project",
                           cascade="all, delete-orphan")
```

`BluetoothTest.firmware_version = Column(String(64), nullable=True)` —— **必须独立字段**，不要塞到 summary JSON 里（要参与 SQL filter / 聚合）。

`Defect` 增加禅道字段：
```python
zentao_bug_id = Column(String(32), index=True)
zentao_url = Column(String(500))
```

`ZenTaoConfig` 单例表（默认 1 行）：
```python
class ZenTaoConfig(Base):
    base_url = Column(String(200))
    username = Column(String(120))
    password = Column(String(200))
    enabled = Column(Boolean, default=False)
    last_sync_at = Column(DateTime)
```

## Startup migration (in main.py)

```python
# 启动时幂等加列（已有库不会重置）
with engine.connect() as conn:
    for stmt in [
        "ALTER TABLE bluetooth_tests ADD COLUMN firmware_version VARCHAR(64)",
        # ... 其它字段
    ]:
        try: conn.execute(text(stmt)); conn.commit()
        except Exception: pass
```

种子项目：只在 projects 表为空时创建，避免覆盖用户数据。

## Router file layout (约定)

```
routers/
├── auth.py        # /api/auth/login, /api/auth/me
├── projects.py    # /api/projects (CRUD)
├── devices.py     # /api/devices
├── plans.py       # /api/plans
├── results.py     # /api/results + /api/results/{id}/version-analysis
├── defects.py     # /api/defects (CRUD) + /api/defects/sync-from-zentao
├── bluetooth.py   # /api/bluetooth + /api/bluetooth/upload + /api/bluetooth/matrix + /api/bluetooth/bulk
├── dashboard.py   # /api/dashboard?project_id=
└── zentao.py      # /api/zentao/config + /api/zentao/products + /api/zentao/bugs + /api/zentao/import-bugs
```

## FastAPI route ordering pitfall

**`/bulk` 必须在 `/{id}` 之前**，否则 `/bulk` 会被 `/api/bluetooth/{bid}` 捕获：

```python
@router.post("/bulk")          # 先注册
def bulk_delete(...): ...

@router.get("/{bid}")           # 后注册（路径参数）
def get_one(bid: int, ...): ...
```

## 静态文件托管（前后端一体化）

```python
# main.py 最后一行
app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="static")
```

前端用 `createWebHashHistory()` 让路由 fallback 到 `index.html`。

## Schema versioning

新加字段一律：
1. `models.py` 加 `Column(..., nullable=True)` 默认值
2. `main.py` 启动时跑幂等 `ALTER TABLE ... ADD COLUMN ...`（try/except 兜底）
3. `schemas.py` 的对应 Pydantic 类加 `Optional[新字段] = None`
4. **不要** 通过 `Base.metadata.create_all()` 给已有表加列（SQLite ALTER TABLE 不被 SQLAlchemy 覆盖）