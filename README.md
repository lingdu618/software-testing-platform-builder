# 软件测试平台搭建助手 (Software Testing Platform Builder)

> 一个用于 **搭建 / 初始化 / 扩展** 轻量级测试管理平台的 WorkBuddy Skill。
> 覆盖 Vue 3 + Element Plus + FastAPI + SQLAlchemy 全栈技术选型，并提供经过真实项目验证的项目结构、模块化功能与 Windows 沙箱下的可复用避坑方案。

## 适用场景（When to use）

- 从零搭建 / 复刻一个测试管理平台
- 给现有平台新增一个专项测试模块（蓝牙、Wi-Fi、压力、性能等）
- 集成禅道（ZenTao）/ 类似 Jira、OpenProject 的缺陷管理
- 按固件 / 版本维度做测试结果趋势分析
- 给测试报告加「分项目 + 智能分析」
- 处理 Windows 沙箱下的文件权限陷阱（safe-delete EPERM、FastAPI 路由顺序坑）

## 技术栈（已验证组合）

| 层 | 选型 | 备注 |
|---|---|---|
| 前端 | Vue 3 + Vite + Element Plus + ECharts | 哈希路由（hash mode），便于后端 StaticFiles 托管 |
| 后端 | FastAPI + SQLAlchemy 2.0 + SQLite + uvicorn | uvicorn `0.0.0.0:8000`；Pydantic v2 |
| 鉴权 | JWT (PyJWT) + bcrypt | 默认账号 `admin/admin123`；token 存 localStorage |
| 数据 | SQLite（单库 `btplat.db`） | 启动时自动建表 + 种子项目 |
| 集成 | httpx（async client）+ 禅道 Open API v1 | 见 `references/zentao-integration.md` |

## 平台能力（模块）

- 项目 / 产品管理（支持分项目隔离）
- 设备 / 型号管理
- 测试计划与多格式结果导入
- 蓝牙 / 专项测试数据（Excel 矩阵导入，sheet 即版本）
- 缺陷管理 + 禅道同步（`/api/defects/sync-from-zentao`）
- 版本维度分析（回归 / 修复 / 反复波动检测）
- 分项目测试报告 + 智能分析（健康度评分、风险、建议）

## 目录结构

```
software-testing-platform-builder/
├── SKILL.md                      # Skill 主入口（purpose / when-to-use / 技术栈 / 结构 / workflow / 坑位）
├── references/                   # 8 个按需加载的模块文档
│   ├── architecture.md           # 数据库 schema、cascade 关系、路由约定
│   ├── frontend-conventions.md   # Vue3 / Element Plus 模式、图标 import、constants.js 字典
│   ├── zentao-integration.md     # 禅道 Open API v1 集成（token / 字段映射 / 坑位）
│   ├── version-analysis.md       # 固件版本排序、版本×测试项矩阵、跨版本回归检测
│   ├── report-analysis.md        # 分项目 dashboard、智能分析、健康度评分
│   ├── bluetooth-matrix-import.md# Excel 测试项×设备矩阵导入、sheet-as-version
│   ├── deployment-windows.md     # safe-delete EPERM 解决方案、构建 / 重启 / 离线 HTML
│   └── field-mapping.md          # 双语严重度 / 优先级 / 状态字典、禅道等级→平台编码
├── scripts/                      # 6 个可复用脚本（带 self-test）
│   ├── start_backend.sh / .bat   # 一键启动 uvicorn（指定 venv 路径）
│   ├── build_frontend_safe.sh    # 前端构建时规避 safe-delete EPERM
│   ├── restart_backend.sh / .ps1 # 找 uvicorn 进程并 kill 重启
│   ├── _ver_sort_key.py          # 固件版本排序键
│   └── _level_mapper.py          # 禅道等级→平台内部编码（兼容 int/"2"/" 2 "）
└── .gitignore
```

## 快速开始（bootstrap 一个新项目）

后端入口（`backend/app/main.py`）：

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="测试管理平台")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
# 注册所有 routers ...
# 最后挂载前端：
app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="static")
```

启动后端：`python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
构建前端：`cd frontend && npm run build`（dev 模式：`npm run dev`，5173 代理 `/api` → `:8000`）

## 安装到 WorkBuddy

```bash
# 将本仓库克隆到用户级 skills 目录
git clone https://github.com/lingdu618/software-testing-platform-builder.git ~/.workbuddy/skills/software-testing-platform-builder
# 重启 WorkBuddy 让 skill 生效
```

> 安装路径：`~/.workbuddy/skills/`（用户级，跨项目可用）。项目级请放在 `<project>/.workbuddy/skills/`。

## 六大必避坑位（Critical pitfalls）

1. **FastAPI 路由顺序**：`POST /bulk` 必须在 `GET /{id}` 之前注册，否则被路径参数捕获 → 404/405。
2. **safe-delete EPERM**：构建前端不要 `rm -rf dist`，用 `mv dist ../.offline_tmp/old_dist_<ts>` → `npm run build`。
3. **禅道 API 三大坑**：base_url 必须是根目录（非 login URL）；登录成功返回 **HTTP 201**（非 200）；等级返回值可能是 int / 字符串 / 带空格，须先归一。
4. **项目级 cascade**：`Project` 删除时 children 关系必须带 `cascade="all, delete-orphan"`，否则 IntegrityError。
5. **图标 import**：Element Plus 图标在 `@element-plus/icons-vue`，`Bug` 等名字不存在（用 `WarnTriangleFilled`），且必须显式 import。
6. **Vue 路由**：用 hash 模式（`createWebHashHistory`）让后端 `StaticFiles(html=True)` 直接托管 `dist/`。

## License

本 skill 按 WorkBuddy skill 规范发布，可用于学习与二次开发。
