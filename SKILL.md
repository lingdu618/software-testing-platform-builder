---
name: software-testing-platform-builder
displayName: 软件测试平台搭建助手
description: 当用户要搭建、初始化或扩展一个测试管理平台（项目管理 + 测试计划/结果 + 缺陷管理 + 外部追踪系统集成 + 多维度分析报告）时使用此 skill。覆盖 Vue 3 + Element Plus + FastAPI + SQLAlchemy 全栈技术选型，提供经过生产验证的项目结构、模块化功能（设备/计划/结果/缺陷/蓝牙测试/版本分析/测试报告）、以及 Windows 沙箱下常见坑位的可复用方案（safe-delete EPERM、FastAPI 路由顺序、禅道 Open API v1 接入等）。Use when the user asks to build/init/extend a test management platform with similar features.
agent_created: true
---

# 软件测试平台搭建助手 (Software Testing Platform Builder)

## Purpose

This skill captures a complete blueprint for building a **轻量级测试管理平台** (lightweight test management platform) that covers:
- 项目/产品管理 (project/product management)
- 设备/型号管理 (device/model registry)
- 测试计划与结果 (test plans + multi-format results import)
- 蓝牙/专项测试数据 (Bluetooth & domain-specific test data with matrix layout)
- 缺陷管理与外部追踪系统打通 (defect management with ZenTao/Jira sync)
- 多维度分析与报告 (version dimension analysis + per-project test reports)

The reference platform is `C:\Users\admin\WorkBuddy\2026-08-04-17-10-03` (software testing platform) — see its source for a concrete example.

## When to use

Use this skill when the user asks for any of:
- 搭建 / 初始化 / 复刻一个测试管理平台
- 给现有平台新增一个测试模块（蓝牙、Wi-Fi、压力、性能等）
- 集成 ZenTao (或类似的 Jira/禅道/OpenProject) 缺陷管理
- 按固件/版本维度做测试结果趋势分析
- 给测试报告加"分项目+智能分析"
- 处理 Windows 沙箱下的文件权限陷阱（safe-delete EPERM、路由顺序坑）

## Tech stack (proven combination)

| 层 | 选型 | 备注 |
|---|---|---|
| 前端 | Vue 3 + Vite + Element Plus + ECharts | 哈希路由（hash mode），便于后端 StaticFiles 托管 |
| 后端 | FastAPI + SQLAlchemy 2.0 + SQLite + uvicorn | uvicorn 0.0.0.0:8000；Pydantic v2 |
| 鉴权 | JWT (PyJWT) + bcrypt | 默认账号 admin/admin123；token 存 localStorage |
| 数据 | SQLite (单库 btplat.db) | 启动时自动建表 + 种子项目 |
| 集成 | httpx (async client) + ZenTao Open API v1 | 见 references/zentao-integration.md |

## Project layout (canonical)

```
project/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 入口；启动时建表/迁移/种子
│   │   ├── models.py          # SQLAlchemy ORM（含 cascade 关系）
│   │   ├── schemas.py         # Pydantic 输入/输出
│   │   ├── database.py        # SessionLocal + engine
│   │   ├── auth.py            # JWT + bcrypt + get_current_user
│   │   ├── routers/
│   │   │   ├── auth.py        # /api/auth/login
│   │   │   ├── projects.py    # /api/projects
│   │   │   ├── devices.py
│   │   │   ├── plans.py
│   │   │   ├── results.py     # 含 /api/results/{id}/version-analysis
│   │   │   ├── defects.py     # 含 /api/defects/sync-from-zentao
│   │   │   ├── bluetooth.py   # 蓝牙测试矩阵导入 + 矩阵视图
│   │   │   ├── dashboard.py   # 含 /api/dashboard?project_id= 聚合分析
│   │   │   └── zentao.py      # 禅道集成（配置 + 检索 + 导入 + 字段映射 helper）
│   │   └── services/
│   │       └── zentao.py      # ZenTaoClient（httpx）
│   └── uvicorn.log            # 后端日志（可选）
├── frontend/
│   ├── src/
│   │   ├── api/index.js       # axios 实例 + token 拦截器
│   │   ├── constants.js       # 全局字典（SEV/PRI/STATUS 双语映射）
│   │   ├── main.js            # 路由 + ElementPlus 挂载
│   │   ├── router/index.js    # 哈希路由
│   │   └── views/
│   │       ├── Login.vue
│   │       ├── Layout.vue     # 侧边栏 + 顶栏
│   │       ├── Dashboard.vue
│   │       ├── Projects.vue
│   │       ├── Devices.vue
│   │       ├── Plans.vue
│   │       ├── Results.vue
│   │       ├── Defects.vue    # 含「从禅道刷新」按钮
│   │       ├── Bluetooth.vue  # 兼容矩阵视图 + 批量上传
│   │       ├── Report.vue     # 分项目测试报告 + 智能分析
│   │       ├── VersionAnalysis.vue
│   │       ├── ZentaoBugs.vue
│   │       └── AnalysisReport.vue
│   ├── vite.config.js         # build.emptyOutDir:false 规避 safe-delete
│   └── dist/                  # 后端 StaticFiles(html=True) 直接托管
├── start.bat / start.sh       # 一键启动后端（uvicorn）
├── start-lan.bat              # 局域网启动
└── README.md
```

## Quick start (bootstrap a new project)

1. **后端** `backend/app/main.py`：
   ```python
   from fastapi import FastAPI
   from fastapi.staticfiles import StaticFiles
   from fastapi.middleware.cors import CORSMiddleware
   app = FastAPI(title="测试管理平台")
   app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                      allow_methods=["*"], allow_headers=["*"])
   # 注册所有 routers
   # 最后挂载前端：
   app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="static")
   ```
   启动：`python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
2. **前端**：`cd frontend && npm run build` → `dist/` 自动被后端托管。
   开发模式：`npm run dev`（5173 代理 /api→:8000）。

## What lives in references/

| 文件 | 内容 |
|---|---|
| `references/architecture.md` | 数据库 schema、关系 cascade、路由约定 |
| `references/frontend-conventions.md` | Vue3/Element Plus 模式、图标 import、表格/表单约定、constants.js 字典 |
| `references/zentao-integration.md` | ZenTao Open API v1 集成全套（token、字段映射、坑位） |
| `references/version-analysis.md` | 固件版本排序、版本×测试项矩阵、跨版本回归检测 |
| `references/report-analysis.md` | 分项目 dashboard、智能分析（build_analysis）、健康度评分 |
| `references/bluetooth-matrix-import.md` | Excel 测试项×设备矩阵导入、sheet-as-version、列名别名 |
| `references/deployment-windows.md` | safe-delete EPERM 解决方案、build 流程、后端重启、离线 HTML |
| `references/field-mapping.md` | 双语严重度/优先级/状态字典、禅道等级→平台编码转换 |

## What lives in scripts/

| 文件 | 用途 |
|---|---|
| `scripts/start_backend.sh` / `.bat` | 一键启动 uvicorn（指定 venv 路径） |
| `scripts/build_frontend_safe.sh` | 前端构建时规避 genie-safe-delete EPERM（mv dist→../.offline_tmp/old_dist_<ts> → npm run build） |
| `scripts/restart_backend.sh` / `.ps1` | 通过 Win32_Process 找 uvicorn 进程并 kill 再重启 |
| `scripts/_ver_sort_key.py` | 固件版本排序：基线 sheet* → V 数字升序 → 其他 → 压测最后 |
| `scripts/_level_mapper.py` | 兼容 int/"2"/" 2 " 的禅道等级→平台内部编码映射 |
| `scripts/init_zentao_config.py` | 在 DB 中预创建 ZenTaoConfig 行 |
| `scripts/verify_*.py` 模板 | 任何新接口写一个 verify_*.py 走通真实接口再删（参考模板） |

## Proven workflow for a new feature (template)

1. **后端模型**：在 `models.py` 加表 + 关系（注意 cascade=`all, delete-orphan`）
2. **Pydantic schema**：`schemas.py` 加 Create/Out 类
3. **路由**：新建/扩展 `routers/xxx.py`，先 GET 列表，再 POST 创建，再 GET 详情；详情路由 `/{id}` 永远放最后
4. **字段映射**：新增的 severity/priority/status 一律走 `constants.js` 的 `SEV_LABELS` 等，**禁止**在视图里再写一遍映射
5. **前端页面**：复制一个最简单的 `xxx.vue`，挂到 `router/index.js`，加入侧边栏（在 Layout.vue）
6. **写入验证脚本**：`verify_xxx.py`，走完真实数据 → 移到 `.offline_tmp/`
7. **前端构建**：`scripts/build_frontend_safe.sh`
8. **后端重启**：`scripts/restart_backend.sh`

## Critical pitfalls (must avoid)

1. **FastAPI 路由顺序**：`POST /api/bluetooth/bulk` 必须在 `GET /api/bluetooth/{bid}` 之前注册，否则被路径参数捕获 → 404/405
2. **genie-safe-delete**：构建前端时不要试图 `rm -rf dist`，会被拦截。统一用 `mv dist ../.offline_tmp/old_dist_<ts>` → `npm run build` → 保留旧 dist 在 .offline_tmp
3. **ZenTao API 坑**：
   - base_url 必须是**根目录**（不能填 login URL）
   - token 登录成功返回 **HTTP 201**（不是 200），后端必须把 200/201 都当成功
   - severity/pri 返回值可能是 int / 字符串 / 带空格，必须先归一
4. **项目级 cascade**：`Project` 模型删除时，所有 children 关系（bluetooth_tests、defects 等）**必须**带 `cascade="all, delete-orphan"`，否则 SQLAlchemy 会试图把 `project_id` 置 NULL → IntegrityError
5. **图标 import**：Element Plus 图标在 `@element-plus/icons-vue`，**不是**所有名字都存在（如 `Bug` 不存在，用 `WarnTriangleFilled`）；用前必须显式 import 否则 `<Xxx />` 静默渲染为空字符串
6. **Vue 3 props 路由**：用 hash 模式（createWebHashHistory）让后端 StaticFiles(html=True) 直接托管 dist/

## Related skills (load on demand)

- `excel-xlsx` — 处理 Excel 矩阵导入时加载
- `tencent-docs-routing` — 处理 .docx/.xlsx 文件路由时加载
- `expert-manager` — 给平台做专家包时加载