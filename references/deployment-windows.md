# Deployment on Windows Sandbox

## 启动脚本

### 后端（start.bat）

```bat
@echo off
cd /d %~dp0
set PY=C:\Users\admin\.workbuddy\binaries\python\envs\btplat\Scripts\python.exe
cd backend
"%PY%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
```

### 局域网启动（start-lan.bat）

同上，但加 `--host 0.0.0.0`（已含）。前端用 `http://<本机IP>:8000/` 访问。

### 前端开发模式

```bash
cd frontend
C:\Users\admin\.workbuddy\binaries\node\versions\22.22.2\npm.cmd run dev
# 默认 http://localhost:5173，代理 /api → http://127.0.0.1:8000
```

## 关键坑：genie-safe-delete EPERM

Windows 沙箱里的 `safe-delete` 守卫会拦截 `rm`/`unlink`/`Remove-Item`/`shutil.rmtree`：

```
[safe-delete][SAFE_DELETE_FAIL_CLOSED] {"reason": "windows-sandbox-recycle-bin-unavailable"}
```

**根因**：Vite/Rollup 重建时会试图 `unlink` 旧 dist 里已存在的同名/同 hash 文件 → 被拦截 → `EPERM: open dist/assets/xxx.js`。

**修复（唯一可靠方案）**：构建前把旧 dist **改名** 到一个不存在的位置：

```bash
TS=$(date +%s)
[ -d dist ] && mv dist ../.offline_tmp/old_dist_${TS}
npm run build
```

mv 是 rename，不被 safe-delete 拦截。`npm run build` 看到 dist 不存在就创建全新目录，不会触发 unlink。

注意：
- `mv dist dist_bak`（如果 dist_bak 已存在）会失败 → 必须 `mv dist ../.offline_tmp/old_dist_<ts>`（fresh path）
- 千万别用 `rm -rf dist_bak`（被拦截）—— 让它留在 `frontend/dist_bak/` 或 `frontend/dist/`

### vite.config.js 加固

```js
export default defineConfig({
  build: {
    outDir: 'dist',
    emptyOutDir: false,   // ← 关键，禁用 Vite 自己 rm dist
    chunkSizeWarningLimit: 2000,
  }
})
```

## 重启后端

```bash
# 1. 通过 Win32_Process 找 uvicorn 进程
$proc = Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -like "*uvicorn app.main:app*" -and $_.ProcessId -ne $PID
}
$proc | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

# 2. 后台启动新 uvicorn
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

或者直接通过 WorkBuddy Bash 工具的 `run_in_background: true`：
```bash
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## .offline_tmp 目录约定

```bash
ls -la .offline_tmp/
├── old_dist_<ts>/         # 历史构建产物（safe-delete 不能 rm，移到这里堆着）
├── test_upload_done.csv   # 测试用的临时文件
├── verify_xxx_done.py     # 验证脚本（完成后 mv 过来不删）
└── diag_xxx_done.py
```

**原则**：
- 任何被 safe-delete 拦的 rm 操作 → 改为 mv 到 `.offline_tmp/<类型>_<ts>`
- 临时 CSV/Excel 测试文件 → `mv test_xxx.* .offline_tmp/test_xxx_done.*`
- 验证脚本 → `mv verify_xxx.py .offline_tmp/verify_xxx_done.py`

## 离线 HTML 生成

设计文档导出单文件离线 HTML（双击浏览器可看，内联 Mermaid + Marked）：

```python
# .offline_tmp/build_html.py
# 读取 .md，注入：
#   <script src="mermaid.min.js"></script>
#   <script src="marked.min.js"></script>
# 把 .js 内容 base64 内联到 <script>...</script>
# Mermaid ER 图渲染：mermaid.run() 在 DOMContentLoaded 后
```

### Mermaid ER 图三个坑

1. **属性块不支持中文标识符**：用纯英文属性名（如 `id`, `name`）
2. **属性不能用 `;` 分隔**：必须每行一个属性
   ```mermaid
   erDiagram
       PROJECT ||--o{ DEVICE : has
       PROJECT {
           int id PK
           string name
           string description
       }
   ```
3. **中文实体名/关系标签**：经 jsdom+mermaid 验证可用，但写完后建议本地预览一次

## 升级 SQLite（新增字段）

```python
# main.py 启动时
with engine.connect() as conn:
    for stmt in [
        "ALTER TABLE bluetooth_tests ADD COLUMN firmware_version VARCHAR(64)",
    ]:
        try: conn.execute(text(stmt)); conn.commit()
        except Exception: pass
```

## Token / 路径常量

- venv：`C:\Users\admin\.workbuddy\binaries\python\envs\btplat\Scripts\python.exe`
- Node：`C:\Users\admin\.workbuddy\binaries\node\versions\22.22.2\npm.cmd`
- 项目：`C:\Users\admin\WorkBuddy\<project-name>`
- 后端日志：`backend/uvicorn.log`（可选）