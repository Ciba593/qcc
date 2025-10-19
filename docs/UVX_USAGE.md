# QCC uvx 使用指南

QCC 已完全支持通过 `uvx` 运行，用户无需安装即可使用！

## ✅ 发布状态

- **PyPI**: https://pypi.org/project/qcc/
- **最新版本**: v0.6.1
- **uvx 支持**: ✅ 已配置

## 🚀 快速开始

### 方式 1: 从 PyPI 运行（推荐）

```bash
# 启动 Web UI
uvx qcc web start

# 启动代理服务器
uvx qcc proxy start

# 查看所有命令
uvx qcc --help
```

### 方式 2: 指定版本

```bash
# 使用特定版本
uvx qcc@0.6.1 web start

# 使用最新版本
uvx qcc@latest web start
```

### 方式 3: 从 GitHub 运行

```bash
# 从 main 分支
uvx --from git+https://github.com/yxhpy/qcc.git qcc web start

# 从特定 tag
uvx --from git+https://github.com/yxhpy/qcc.git@v0.6.1 qcc web start
```

### 方式 4: 本地开发

```bash
# 克隆仓库
git clone https://github.com/yxhpy/qcc.git
cd qcc

# 从本地运行
uvx --from . qcc web start --dev
```

## 📚 常用命令

### Web UI 管理

```bash
# 启动 Web UI（生产模式）
uvx qcc web start

# 启动 Web UI（开发模式，仅限本地开发）
uvx --from . qcc web start --dev

# 查看 Web UI 状态
uvx qcc web status

# 停止 Web UI
uvx qcc web stop
```

### 代理服务器

```bash
# 启动代理服务器
uvx qcc proxy start

# 使用指定配置
uvx qcc proxy start --cluster prod

# 停止代理服务器
uvx qcc proxy stop

# 查看代理状态
uvx qcc proxy status
```

### 配置管理

```bash
# 初始化配置
uvx qcc init

# 添加新配置
uvx qcc add myconfig

# 列出所有配置
uvx qcc list

# 使用指定配置
uvx qcc use myconfig

# 显示当前配置
uvx qcc show
```

### Endpoint 管理

```bash
# 列出所有 endpoints
uvx qcc endpoint list

# 添加 endpoint
uvx qcc endpoint add

# 测试 endpoint
uvx qcc endpoint test <endpoint-id>
```

## 🔧 高级用法

### 使用环境变量

```bash
# 设置配置文件路径
export QCC_CONFIG_PATH=/path/to/config.json
uvx qcc web start

# 设置日志级别
export QCC_LOG_LEVEL=debug
uvx qcc proxy start
```

### 指定端口

```bash
# Web UI 使用自定义端口
uvx qcc web start --port 9000

# 代理服务器使用自定义端口
uvx qcc proxy start --port 7890
```

### 不打开浏览器

```bash
# 启动 Web UI 但不自动打开浏览器
uvx qcc web start --no-browser
```

## 💡 使用场景

### 场景 1: 快速体验

```bash
# 一键启动，无需安装
uvx qcc web start

# 在浏览器访问 http://127.0.0.1:8080
```

### 场景 2: 临时使用不同版本

```bash
# 测试新版本
uvx qcc@0.6.1 web start

# 回退到旧版本
uvx qcc@0.5.2 web start
```

### 场景 3: CI/CD 环境

```bash
# 在 CI 中运行测试
uvx qcc proxy start --cluster test
uvx qcc endpoint test all
uvx qcc proxy stop
```

### 场景 4: 开发和调试

```bash
# 克隆并本地开发
git clone https://github.com/yxhpy/qcc.git
cd qcc
uvx --from . qcc web start --dev
```

## 🔍 故障排除

### 问题 1: 命令未找到

```bash
# 确保 uvx 已安装
pip install uv

# 或使用 pipx 安装 uv
pipx install uv
```

### 问题 2: 版本不匹配

```bash
# 清除 uvx 缓存
rm -rf ~/.cache/uv

# 强制重新下载
uvx -n qcc@0.6.1 web start
```

### 问题 3: 网络问题

```bash
# 使用国内镜像
export UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
uvx qcc web start
```

## 📦 与 pip 安装的对比

| 特性 | uvx | pip install |
|------|-----|-------------|
| 无需安装 | ✅ | ❌ |
| 隔离环境 | ✅ | ❌ |
| 多版本共存 | ✅ | ❌ |
| 一键运行 | ✅ | ❌ |
| 系统污染 | ❌ | ✅ |
| 适用场景 | 快速体验、临时使用 | 长期使用、集成 |

## 🎯 推荐使用方式

### 新用户（推荐 uvx）

```bash
# 快速体验 Web UI
uvx qcc web start
```

### 经常使用（推荐 pip）

```bash
# 安装到系统
pip install qcc

# 直接使用
qcc web start
```

### 开发者（推荐本地）

```bash
# 克隆仓库
git clone https://github.com/yxhpy/qcc.git
cd qcc

# 开发模式
uvx --from . qcc web start --dev
```

## 📖 更多信息

- **完整文档**: [README.md](../README.md)
- **发布说明**: [docs/releases/](./releases/)
- **问题反馈**: https://github.com/yxhpy/qcc/issues

## ✨ 快速命令参考

```bash
# Web UI
uvx qcc web start              # 启动 Web UI
uvx qcc web status             # 查看状态
uvx qcc web stop               # 停止服务

# 代理服务器
uvx qcc proxy start            # 启动代理
uvx qcc proxy status           # 查看状态
uvx qcc proxy stop             # 停止代理

# 配置管理
uvx qcc init                   # 初始化
uvx qcc list                   # 列出配置
uvx qcc use <name>             # 切换配置

# Endpoint 管理
uvx qcc endpoint list          # 列出 endpoints
uvx qcc endpoint add           # 添加 endpoint
uvx qcc endpoint test <id>     # 测试 endpoint
```

---

**最后更新**: 2025-10-19
**版本**: v0.6.1
