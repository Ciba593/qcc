# QCC Web UI

> 现代化的 Web 界面，为 QCC (Quick Claude Config) 提供可视化的配置管理和监控功能

## 📖 文档导航

- **[快速开始](./快速开始.md)** - 安装和启动指南

## 🚀 快速开始

### 一键启动（推荐）

```bash
# 生产模式 - 日常使用
uvx qcc web start

# 开发模式 - 代码开发（前后端热重载）
uvx qcc web start --dev
```

### 本地开发

```bash
# 克隆项目
git clone https://github.com/lghguge520/qcc.git
cd qcc

# 使用 uvx 运行本地版本
uvx --from . qcc web start --dev

# 查看状态
uvx --from . qcc web status

# 停止服务
uvx --from . qcc web stop
```

### 访问

- **Web UI**: http://127.0.0.1:8080
- **API 文档**: http://127.0.0.1:8080/api/docs

## ✨ 功能特性

### ✅ 已实现（v0.5.0）

#### 核心功能
- **仪表盘** - 系统概览、存储方式、代理状态、Endpoint 健康状况
- **配置管理** - 创建、查看、编辑、删除、使用配置
- **Endpoint 管理** - 创建和管理高可用代理组（EndpointGroup）
- **代理服务** - 启动、停止、查看日志、实时监控
- **健康监控** - 实时健康检查、成功率、响应时间统计
- **失败队列** - 查看失败节点、重试管理

#### 高级特性
- **实时状态显示** - Header 显示当前系统配置和激活节点
- **自动刷新** - 健康数据每 5 秒自动更新
- **运行时管理** - 动态添加/移除/移动节点
- **Claude Code 集成** - 一键应用配置到 Claude Code

### 主要改进

1. **配置删除修复** - 修复删除后配置重新出现的问题
2. **存储方式显示** - 正确显示 GitHub/云盘/本地存储类型
3. **健康监控数据** - 从运行时代理获取准确的健康状况
4. **Header 状态栏** - 实时显示系统配置和当前激活节点

## 🛠️ 技术栈

**前端**:
- React 18 + TypeScript
- Ant Design
- React Router
- TanStack Query（数据管理）
- Axios（API 客户端）
- Vite（构建工具）

**后端**:
- FastAPI（Web 框架）
- Pydantic（数据验证）
- Uvicorn（ASGI 服务器）
- aiohttp（异步 HTTP 客户端）

## 📊 功能完成度

| 模块 | 状态 | 说明 |
|------|------|------|
| 配置管理 | ✅ 100% | 完整的 CRUD 操作 |
| Endpoint 管理 | ✅ 100% | EndpointGroup 高可用组 |
| 代理服务 | ✅ 100% | 启动、停止、日志查看 |
| 健康监控 | ✅ 100% | 实时健康检查和统计 |
| 失败队列 | ✅ 100% | 查看和重试管理 |
| 运行时管理 | ✅ 100% | 动态节点管理 |
| Claude Config | ✅ 100% | 配置应用和还原 |

**总体完成度**: 100% ✅

## 📁 项目结构

```
qcc-web/                 # 前端项目
├── src/
│   ├── api/            # API 客户端
│   │   └── client.ts   # API 接口定义
│   ├── pages/          # 页面组件
│   │   ├── Dashboard.tsx
│   │   ├── Configs.tsx
│   │   ├── Endpoints.tsx
│   │   ├── Proxy.tsx
│   │   └── Health.tsx
│   ├── layouts/        # 布局组件
│   │   └── MainLayout.tsx
│   └── types/          # TypeScript 类型
├── dist/               # 构建产物
└── package.json        # 依赖配置

fastcc/web/             # 后端模块
├── app.py              # FastAPI 应用
├── models.py           # 数据模型
├── utils.py            # 工具函数
├── routers/            # API 路由
│   ├── dashboard.py    # 仪表盘 API
│   ├── configs.py      # 配置管理 API
│   ├── endpoints.py    # Endpoint 管理 API
│   ├── proxy.py        # 代理服务 API
│   ├── health.py       # 健康监控 API
│   ├── queue.py        # 失败队列 API
│   ├── priority.py     # 优先级 API
│   └── claude_config.py # Claude Code 配置 API
└── static/             # 前端静态文件
```

## 🔧 开发指南

### 前端开发（热重载）

```bash
# 启动前端开发服务器
cd qcc-web
npm run dev
# 访问 http://localhost:5173
```

### 后端开发（热重载）

```bash
# 启动后端开发服务器（自动重载）
qcc web start --dev --no-browser
# 访问 http://127.0.0.1:8080
```

### 构建部署

```bash
# 1. 构建前端
cd qcc-web
npm run build

# 2. 复制到后端静态目录
cp -r dist/* ../fastcc/web/static/

# 3. 启动生产服务器
cd ..
qcc web start
```

## 🌐 API 接口

完整的 API 文档可通过以下方式访问：
- **Swagger UI**: http://127.0.0.1:8080/api/docs
- **ReDoc**: http://127.0.0.1:8080/api/redoc

主要 API 端点：
- `/api/dashboard/*` - 仪表盘数据
- `/api/configs/*` - 配置管理
- `/api/endpoints/*` - Endpoint 管理
- `/api/proxy/*` - 代理服务控制
- `/api/health/*` - 健康监控
- `/api/queue/*` - 失败队列
- `/api/claude-config/*` - Claude Code 配置

## 🐛 问题反馈

如果遇到问题，请提供：
1. 错误信息或截图
2. 操作步骤
3. 日志文件（`~/.fastcc/web.log`）

## 📄 许可证

MIT License

---

**QCC Web UI v0.5.0** - 让配置管理更简单、更直观 ✨
