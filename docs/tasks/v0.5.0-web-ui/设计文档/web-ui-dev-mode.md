# Web UI 一键启动功能测试文档

## 功能概述

实现 uvx 一键启动 Web UI，支持：
- **生产模式**：构建前端并通过后端单一端口提供服务
- **开发模式**：前后端同时启动，支持热重载

## 技术实现

### 1. Vite 配置 (`qcc-web/vite.config.ts`)

```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '127.0.0.1',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
    },
    open: true, // 自动打开浏览器
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
```

### 2. CLI 命令 (`fastcc/cli.py`)

#### 生产模式
```bash
uvx qcc web start
```

流程：
1. 检查前端是否已构建 (`qcc-web/dist`)
2. 如果未构建，自动安装依赖并构建
3. 启动后端 FastAPI 服务（单一端口 8080）
4. 自动打开浏览器

#### 开发模式
```bash
uvx qcc web start --dev
```

流程：
1. 检查并安装前端依赖
2. 启动前端 Vite 开发服务器（端口 5173）
3. 启动后端 FastAPI 服务（端口 8080，热重载）
4. Vite 自动打开浏览器到前端地址
5. API 请求自动代理到后端

### 3. 进程管理

#### PID 文件结构
```json
{
  "pid": 12345,              // 后端进程 ID
  "vite_pid": 12346,         // 前端进程 ID（仅开发模式）
  "host": "127.0.0.1",
  "port": 8080,
  "dev_mode": true,          // 是否开发模式
  "start_time": "2025-10-18T10:00:00"
}
```

#### 停止服务
```bash
uvx qcc web stop
```

自动停止：
- 开发模式：先停止前端进程，再停止后端进程
- 生产模式：停止后端进程

#### 查看状态
```bash
uvx qcc web status
```

显示信息：
- 运行模式（开发/生产）
- 前后端进程 ID
- 访问地址
- 运行时长

## 测试用例

### 测试 1: 生产模式启动（首次）

**操作：**
```bash
uvx --from . qcc web start
```

**预期结果：**
- ✅ 自动安装前端依赖
- ✅ 自动构建前端（生成 `qcc-web/dist`）
- ✅ 启动后端服务
- ✅ 自动打开浏览器到 http://127.0.0.1:8080
- ✅ 可以访问前端页面和 API

**验证命令：**
```bash
# 检查构建输出
ls -la qcc-web/dist

# 检查服务状态
uvx --from . qcc web status

# 访问 API
curl http://127.0.0.1:8080/api/dashboard/summary
```

### 测试 2: 生产模式启动（已构建）

**前置条件：** 已执行过测试 1

**操作：**
```bash
uvx --from . qcc web stop
uvx --from . qcc web start
```

**预期结果：**
- ✅ 跳过构建步骤
- ✅ 直接启动后端服务
- ✅ 启动速度更快

### 测试 3: 开发模式启动

**操作：**
```bash
uvx --from . qcc web start --dev
```

**预期结果：**
- ✅ 自动安装前端依赖（如果需要）
- ✅ 启动前端 Vite 服务器（5173 端口）
- ✅ 启动后端服务（8080 端口，热重载）
- ✅ 显示两个地址：
  - 前端开发: http://127.0.0.1:5173
  - 后端 API: http://127.0.0.1:8080
- ✅ 浏览器自动打开到前端地址

**验证命令：**
```bash
# 检查服务状态
uvx --from . qcc web status

# 应该显示：
# - 运行模式: 开发模式 (热重载)
# - 后端进程 ID: XXX
# - 前端进程 ID: XXX
# - 前端地址: http://127.0.0.1:5173
# - 后端 API: http://127.0.0.1:8080
```

### 测试 4: 前端热重载

**前置条件：** 开发模式运行中

**操作：**
1. 修改前端代码（如 `qcc-web/src/pages/Dashboard.tsx`）
2. 保存文件

**预期结果：**
- ✅ Vite 自动检测变化
- ✅ 浏览器自动刷新，显示更改
- ✅ 无需手动重启

### 测试 5: 后端热重载

**前置条件：** 开发模式运行中

**操作：**
1. 修改后端代码（如 `fastcc/web/routers/dashboard.py`）
2. 保存文件

**预期结果：**
- ✅ Uvicorn 自动检测变化
- ✅ 后端服务自动重启
- ✅ API 请求立即使用新代码
- ✅ 前端保持运行

### 测试 6: API 代理（开发模式）

**前置条件：** 开发模式运行中

**操作：**
```bash
# 通过前端代理访问 API
curl http://127.0.0.1:5173/api/dashboard/summary

# 直接访问后端 API
curl http://127.0.0.1:8080/api/dashboard/summary
```

**预期结果：**
- ✅ 两个请求都能成功
- ✅ 返回相同的数据
- ✅ 浏览器开发工具中看到 API 请求到 `/api/*`

### 测试 7: 停止服务（开发模式）

**前置条件：** 开发模式运行中

**操作：**
```bash
uvx --from . qcc web stop
```

**预期结果：**
- ✅ 前端进程被停止
- ✅ 后端进程被停止
- ✅ PID 文件被清理
- ✅ 端口释放

**验证命令：**
```bash
# 检查进程
uvx --from . qcc web status
# 应该显示: Web UI 未运行

# 检查端口
lsof -i :5173
lsof -i :8080
# 应该无输出
```

### 测试 8: Ctrl+C 停止（开发模式）

**前置条件：** 开发模式运行中

**操作：**
在运行终端按 `Ctrl+C`

**预期结果：**
- ✅ 前端进程被停止
- ✅ 后端进程被停止
- ✅ PID 文件被清理
- ✅ 显示 "服务已停止"

### 测试 9: 端口占用检测

**操作：**
```bash
# 占用后端端口
python3 -m http.server 8080 &

# 尝试启动
uvx --from . qcc web start
```

**预期结果：**
- ✅ 显示错误: "后端端口 8080 已被占用"
- ✅ 不启动服务

### 测试 10: 重复启动检测

**前置条件：** 服务已运行

**操作：**
```bash
uvx --from . qcc web start
```

**预期结果：**
- ✅ 显示警告: "Web UI 已在运行"
- ✅ 显示提示: "如需重启，请先运行: uvx qcc web stop"
- ✅ 不启动新服务

### 测试 11: Windows 兼容性

**环境：** Windows + Git Bash

**操作：**
```bash
# 使用 Git Bash
uvx --from . qcc web start --dev
```

**预期结果：**
- ✅ npm 命令正常执行
- ✅ 前后端都能启动
- ✅ 进程管理正常工作

### 测试 12: 不自动打开浏览器

**操作：**
```bash
uvx --from . qcc web start --no-browser
```

**预期结果：**
- ✅ 服务正常启动
- ✅ 浏览器不自动打开
- ✅ 显示访问地址

## 性能验证

### 启动时间

| 模式 | 首次启动 | 后续启动 |
|------|---------|---------|
| 生产模式（需构建） | ~30-60s | ~2-3s |
| 开发模式 | ~15-30s | ~5-8s |

### 热重载速度

| 类型 | 响应时间 |
|------|---------|
| 前端热重载 | <500ms |
| 后端热重载 | ~2-3s |

## 问题排查

### 问题 1: npm 命令找不到

**症状：** 错误提示 "npm: command not found"

**解决：**
```bash
# 安装 Node.js (macOS)
brew install node

# 安装 Node.js (Ubuntu)
sudo apt install nodejs npm

# Windows: 下载安装包
# https://nodejs.org/
```

### 问题 2: 端口被占用

**症状：** "端口 8080 已被占用"

**解决：**
```bash
# 查找占用进程
lsof -i :8080

# 停止进程
kill -9 <PID>

# 或使用其他端口
uvx qcc web start --port 9000
```

### 问题 3: 前端进程未停止

**症状：** 停止后端但前端仍在运行

**解决：**
```bash
# 查找 Vite 进程
ps aux | grep vite

# 手动停止
kill -9 <PID>

# 清理 PID 文件
rm ~/.qcc/web.pid
```

### 问题 4: 构建失败

**症状：** "构建前端失败"

**解决：**
```bash
# 手动构建
cd qcc-web
npm install
npm run build

# 检查错误日志
```

## 开发建议

### 推荐工作流

**方式 1: 全栈开发（推荐）**
```bash
# 一键启动开发模式
uvx --from . qcc web start --dev

# 同时修改前后端代码
# - 前端: qcc-web/src/
# - 后端: fastcc/web/

# 自动热重载，无需重启
```

**方式 2: 仅前端开发**
```bash
# 启动生产模式后端
uvx --from . qcc web start

# 在另一个终端启动前端开发
cd qcc-web
npm run dev
```

**方式 3: 仅后端开发**
```bash
# 使用已构建的前端
uvx --from . qcc web start --dev

# 只修改后端代码
# 后端自动热重载
```

### 调试技巧

**前端调试：**
- 浏览器开发工具 (F12)
- React DevTools 扩展
- 查看 Vite 控制台输出

**后端调试：**
- 查看 Uvicorn 日志
- 访问 API 文档: http://127.0.0.1:8080/api/docs
- 使用 `print()` 或 Python 调试器

## 总结

✅ **已实现功能：**
1. 一键启动生产模式和开发模式
2. 前端自动构建和依赖安装
3. 前后端热重载
4. 进程管理和 PID 跟踪
5. 自动代理 API 请求
6. 优雅的进程清理
7. Windows/macOS/Linux 兼容
8. 状态监控和错误处理

🎯 **核心优势：**
- **开发体验**: 修改代码立即生效，无需手动重启
- **一键部署**: 生产模式自动构建和优化
- **统一管理**: 单一命令管理前后端服务
- **安全可靠**: 完善的错误处理和进程清理

📝 **注意事项：**
- 开发模式使用两个端口（5173 + 8080）
- 生产模式只使用一个端口（8080）
- 确保 Node.js 和 npm 已安装
- Windows 用户建议使用 Git Bash
