# QCC Web UI

> 现代化的 Web 界面，为 QCC (Quick Claude Config) 提供可视化的配置管理和监控功能

## 📖 文档导航

- **[快速开始](./快速开始.md)** - 安装和启动指南
- **[开发工作流](./开发工作流.md)** - 热重载开发、调试技巧、性能优化
- **[开发计划](./开发计划.md)** - 完整的开发计划和路线图
- **[开发完成报告](./开发完成报告.md)** - Phase 1 完成情况

## 🚀 快速开始

### 零安装运行 (推荐)

```bash
# 使用 uvx 一键启动 (自动安装所有依赖)
uvx -n --from . qcc web start
```

### 传统安装

```bash
# 安装 qcc
pip install -e .

# 启动 Web UI
qcc web start
```

### 访问

- **Web UI**: http://127.0.0.1:8080
- **API 文档**: http://127.0.0.1:8080/api/docs

## ✨ 功能特性

### ✅ 已实现

- **仪表盘** - 系统概览、统计信息
- **配置管理** - 查看、使用、删除配置
- **Endpoint 管理** - 管理 API endpoint
- **代理服务** - 监控代理状态、控制启停

### 🔄 开发中

- 代理启动功能
- 日志查看
- 优先级管理
- 健康监控
- 性能指标
- 失败队列管理

## 🛠️ 技术栈

**前端**:
- React 18 + TypeScript
- Ant Design
- React Router
- TanStack Query
- Axios
- Vite

**后端**:
- FastAPI
- Pydantic
- Uvicorn

## 📊 开发进度

| 模块 | CLI 命令 | 完成度 |
|------|---------|--------|
| 配置管理 | 7 | 100% ✅ |
| Endpoint | 3 | 100% ✅ |
| 代理服务 | 4 | 50% 🔄 |
| 健康监控 | 5 | 0% ⏳ |
| 优先级 | 4 | 0% ⏳ |
| 失败队列 | 4 | 0% ⏳ |

**总体进度**: 44% (12/27 命令已实现)

## 🎯 开发路线图

### Phase 1: 基础设施 ✅
- 前后端项目搭建
- 核心 API 实现
- 基础页面开发

### Phase 2: 核心功能 (进行中)
- Endpoint 管理完善
- 代理服务完整实现
- 配置创建对话框

### Phase 3: 高级功能
- 优先级管理
- 健康监控
- 性能指标

### Phase 4: 优化发布
- WebSocket 实时推送
- 性能优化
- 完整测试

## 📁 项目结构

```
qcc-web/                 # 前端项目
├── src/
│   ├── api/            # API 客户端
│   ├── pages/          # 页面组件
│   ├── layouts/        # 布局组件
│   ├── components/     # 通用组件
│   └── types/          # TypeScript 类型
└── dist/               # 构建产物

fastcc/web/             # 后端模块
├── app.py              # FastAPI 应用
├── models.py           # 数据模型
├── routers/            # API 路由
│   ├── dashboard.py
│   ├── configs.py
│   ├── endpoints.py
│   ├── proxy.py
│   └── ...
└── static/             # 前端静态文件
```

## 🔧 开发指南

### 推荐开发模式: 前后端同时热重载

**终端 1 - 后端热重载**:
```bash
uvx --from . qcc web start --dev --no-browser
# 修改 fastcc/web/ 下的 Python 文件，服务器自动重启
```

**终端 2 - 前端热重载**:
```bash
cd qcc-web && npm run dev
# 修改 src/ 下的文件，浏览器自动刷新（HMR）
```

**访问**: http://localhost:5173 (前端开发服务器，包含热模块替换)

更多开发技巧请查看 **[开发工作流文档](./开发工作流.md)**，包括：
- 不同开发场景的最佳实践
- 前后端调试技巧
- 性能优化建议
- 常见问题解决方案

### 部署流程

```bash
# 1. 构建前端
cd qcc-web && npm run build

# 2. 复制到后端
cp -r dist/* ../fastcc/web/static/

# 3. 启动服务
cd .. && qcc web start
```

## 🐛 已知问题

1. TypeScript 类型部分使用 any (待完善)
2. WebSocket 实时推送未实现
3. 部分页面功能待开发

## 🤝 贡献

欢迎贡献代码！请参考：

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

MIT License

---

**QCC Web UI** - 让配置管理更简单、更直观 ✨
