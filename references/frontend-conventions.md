# Frontend Conventions

## Tech stack

- **Vue 3** Composition API (`<script setup>`)
- **Element Plus**（按需全量注册到 main.js）
- **ECharts** 用于仪表盘/趋势/矩阵
- **axios** (通过 `frontend/src/api/index.js` 统一实例)
- **vue-router** `createWebHashHistory`（便于后端 StaticFiles 托管）
- **Vite 5** 构建

## 全局字典（**必读**）

`frontend/src/constants.js` 定义**严重程度/优先级/状态**的双语映射。**任何涉及这三类字段展示/下拉的页面都必须复用**，禁止在视图里再写一遍映射。

```js
// 核心 helper
sevLabel(s)        // 'fatal' → '致命'
sevType(s)         // 返回 el-tag 的 type
priLabel(p), priType(p)
defectStatusLabel(s), defectStatusType(s)

// 选项列表（直接 v-for 用于 el-select）
SEVERITY_OPTIONS = [{value:'fatal',label:'致命'}, ...]
PRIORITY_OPTIONS, DEFECT_STATUS_OPTIONS

// 排序用
SEV_RANK = { fatal:0, serious:1, major:2, minor:3 }
STATUS_RANK = { open:0, resolved:1, closed:2 }
```

新增字段时**先改 constants.js，再改视图**。

## 路由

```js
// router/index.js
{ path: '/xxx', component: () => import('@/views/Xxx.vue'), meta: { title: 'xxx' } }
```

## Layout.vue 侧边栏图标

**坑**：Element Plus 图标需要显式 import（不在 Vue 全局里）。`@element-plus/icons-vue` 的图标名**不是全的**，例如 `Bug` 不存在，要用 `WarnTriangleFilled`。

```js
import { DataLine, Files, Cpu, List, Upload, Connection,
         WarnTriangleFilled, Link, Search, Document, DataAnalysis } from '@element-plus/icons-vue'
```

如果 `<Xxx />` 没在 import 列表里，Vue 会**静默**渲染为空字符串（控制台无报错），表现就是"图标不见了"。

## API 调用

```js
// frontend/src/api/index.js
import axios from 'axios'
const api = axios.create({ baseURL: '/api' })
api.interceptors.request.use(cfg => {
  cfg.headers.Authorization = `Bearer ${localStorage.getItem('token')}`
  return cfg
})
export default api
```

## 项目选择器约定

所有需要"按项目过滤"的页面，**顶部**都加项目选择器：
```html
<el-select v-model="projFilter" placeholder="项目" clearable @change="load">
  <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
</el-select>
```

`load()` 内部：
```js
const params = {}
if (projFilter.value != null) params.project_id = projFilter.value
const { data } = await api.get('/xxx', { params })
```

## ECharts 使用

```js
import * as echarts from 'echarts'
// init + setOption
// 切换数据前先 dispose 旧实例（避免 resize 报错）
if (chart) { chart.dispose(); chart = null }
chart = echarts.init(ref.value)
chart.setOption({...})
```

## 表单 / 对话框约定

- 编辑用 `<el-dialog v-model="visible">`，内部 `<el-form :model="form">`
- "新增/编辑"模式靠 `form.id` 是否存在判断
- 保存后必须 reload 列表

## 上传 / 批量导入

```html
<el-upload :auto-upload="false" :show-file-list="false" :on-change="onUpload"
           accept=".csv,.json,.xlsx,.xls">
  <el-button>批量导入</el-button>
</el-upload>
```

```js
async function onUpload(f) {
  const fd = new FormData(); fd.append('file', f.raw)
  await api.post('/xxx/upload?project_id=<目标项目id>', fd)
  ElMessage.success('导入成功'); load()
}
```

**关键**：上传目标项目 ID 一定要从 `projFilter`（顶部项目选择器）取，**不要**用 `form.value.project_id`（那个是"新增对话框"用的，会被默认成第一个项目造成误导）。

## 中文显示文案原则

- 技术标识符（路由、API 路径、变量名）保持英文
- 用户可见的中文文案集中改（全局改名时用 Grep 找全所有引用）