# QCC v0.5.0 - Web UI 管理界面

## 📚 版本概览

**状态**: 🚧 开发中
**目标发布**: v0.5.0
**核心特性**: Web 管理界面，提供可视化配置和监控功能

---

## 🎯 核心功能

### 1. **Web UI 管理界面**
- 直观的 Web 界面管理 QCC 代理服务
- 实时监控和配置管理
- 前后端分离架构

### 2. **一键启动**
- `qcc web start` - 快速启动 Web UI
- 开发模式支持热重载
- 自动端口管理

### 3. **完整的生命周期管理**
- 启动、停止、重启命令
- 状态查询和健康检查
- 优雅的进程清理

---

## 📂 文档导航

### 设计文档

| 文档 | 说明 |
|------|------|
| [web-ui-one-command-start.md](./设计文档/web-ui-one-command-start.md) | 一键启动功能设计 |
| [web-ui-dev-mode.md](./设计文档/web-ui-dev-mode.md) | 开发模式实现 |
| [web-ui-stop-cleanup.md](./设计文档/web-ui-stop-cleanup.md) | 停止和清理机制 |
| [CTRL_C_CLEANUP_FIX.md](./设计文档/CTRL_C_CLEANUP_FIX.md) | Ctrl+C 清理修复 |
| [FINAL_VERIFICATION.md](./设计文档/FINAL_VERIFICATION.md) | 最终验证报告 |
| [IMPLEMENTATION_SUMMARY.md](./设计文档/IMPLEMENTATION_SUMMARY.md) | 实现总结 |
| [README_UPDATE_SUMMARY.md](./设计文档/README_UPDATE_SUMMARY.md) | 文档更新总结 |

### 用户指南

| 文档 | 说明 |
|------|------|
| [快速开始.md](./用户指南/快速开始.md) | 快速入门指南 |
| [README.md](./用户指南/README.md) | Web UI 使用说明 |
| [WEB_START_QUICK_REFERENCE.md](./用户指南/WEB_START_QUICK_REFERENCE.md) | 快速参考 |

---

## 🚀 快速开始

### 启动 Web UI

```bash
# 生产模式
uvx qcc web start

# 开发模式（热重载）
uvx qcc web start --dev

# 指定端口
uvx qcc web start --port 8080
```

### 查看状态

```bash
uvx qcc web status
```

### 停止服务

```bash
uvx qcc web stop
```

---

## 🏗️ 技术架构

### 前端
- **框架**: Vue 3 + TypeScript
- **构建**: Vite
- **UI**: Element Plus
- **开发服务器**: http://127.0.0.1:5173

### 后端
- **框架**: FastAPI
- **服务器**: Uvicorn
- **API**: http://127.0.0.1:8080
- **文档**: http://127.0.0.1:8080/api/docs

---

## 📊 功能特性

### ✅ 已实现

- [x] 一键启动/停止
- [x] 开发模式热重载
- [x] 状态查询
- [x] 优雅关闭
- [x] 进程管理
- [x] 端口检测

### 🚧 开发中

- [ ] 配置可视化编辑
- [ ] 实时监控面板
- [ ] 日志查看
- [ ] 性能分析

### 📅 计划中

- [ ] 用户认证
- [ ] 多用户支持
- [ ] 配置导入/导出
- [ ] API 统计分析

---

## 🔗 相关链接

- **主仓库**: https://github.com/yxhpy/qcc
- **问题反馈**: https://github.com/yxhpy/qcc/issues
- **发布说明**: [docs/releases/](../../releases/)

---

**最后更新**: 2025-10-18
**维护者**: QCC Development Team
