# CarSoul Guardian — Frontend

基于 **React 18 + TypeScript + Vite + TailwindCSS + Ant Design** 的前端工程。

## 目录结构

```
frontend/
├── public/                 # 静态资源
├── src/
│   ├── pages/              # 页面：Dashboard / AgentChat / VehicleArchive
│   ├── components/         # 可复用展示组件
│   ├── layouts/            # 布局（含侧边导航 MainLayout）
│   ├── hooks/              # 自定义 Hook（useAgent / useApi）
│   ├── services/           # API 调用与类型
│   ├── stores/             # Zustand 状态（agent / user）
│   ├── utils/              # 工具（axios 请求封装）
│   ├── assets/             # 图片/字体
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── vite.config.ts          # 含 /api 代理到后端
├── tailwind.config.js
└── package.json
```

## 页面

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | Dashboard | 车辆健康指数、AI 守护状态、最近提醒、车辆概览 |
| `/agent` | AI 守护 | 类 ChatGPT 对话界面，调用 `/api/agent/chat` |
| `/vehicle` | 车辆档案 | 车辆列表 + 添加表单，调用 `/api/vehicle` |

## 本地启动

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

> 开发模式下 Vite 会把 `/api` 与 `/health` 代理到 `http://localhost:8000`，无需额外配置跨域。

## 代码规范

- ESLint + Prettier 已配置（`npm run lint` / `npm run format`）
- Tailwind 关闭 preflight 以兼容 Ant Design
