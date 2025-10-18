# Web UI 停止时自动清理功能

## 📋 功能概述

当停止 Web UI 时（无论是 `uvx qcc web stop` 还是 `Ctrl+C`），自动执行清理操作：
1. ✅ 停止 Web UI 服务（前后端进程）
2. ✅ 停止代理服务（如果在运行）
3. ✅ 还原 Claude Code 配置（如果已应用）

**支持的停止方式：**
- ✅ 命令停止：`uvx qcc web stop`
- ✅ 快捷键停止：`Ctrl+C`
- ✅ 进程终止：自动清理

## 🎯 使用方法

### 默认行为（推荐）

```bash
# 停止 Web UI 并自动清理
uvx qcc web stop
```

**执行流程：**
1. 停止 Web UI 前后端进程
2. 检测并停止代理服务
3. 检测并还原 Claude Code 配置

**输出示例：**
```
==================================================
🚀 QCC Web UI
==================================================
正在停止 Web UI (PID: 12345, 127.0.0.1:8080)...
✅ Web UI 已停止

ℹ️ 检测到代理服务正在运行，正在停止...
✅ 代理服务已停止

ℹ️ 检测到已应用代理配置，正在还原...
✅ Claude Code 配置已还原
```

### 保持代理运行

```bash
# 停止 Web UI 但保持代理服务运行
uvx qcc web stop --keep-proxy
```

适用场景：
- 继续使用代理服务
- 只是暂时关闭 Web UI

### 保持配置不还原

```bash
# 停止 Web UI 但保持 Claude Code 配置
uvx qcc web stop --keep-config
```

适用场景：
- 继续使用代理配置
- 稍后会重新启动

### 保持所有

```bash
# 只停止 Web UI，不做任何清理
uvx qcc web stop --keep-proxy --keep-config
```

## 🔧 技术实现

### 通用清理函数

所有停止方式都调用统一的清理函数：

```python
def cleanup_on_stop(keep_proxy=False, keep_config=False):
    """Web UI 停止时的清理函数"""
    # 1. 停止代理服务
    if not keep_proxy:
        ProxyServer.stop_running_server()

    # 2. 还原 Claude Code 配置
    if not keep_config:
        claude_config_manager.restore_config()
```

### Ctrl+C 处理

```python
except KeyboardInterrupt:
    print_status("服务已停止", "info")
    # 自动执行清理
    cleanup_on_stop()
```

### 命令停止

```python
@web.command()
def stop(keep_proxy, keep_config):
    # 停止 Web UI
    stop_running_web_server()
    # 执行清理
    cleanup_on_stop(keep_proxy, keep_config)
```

### 停止代理服务

```python
from .proxy.server import ProxyServer

proxy_info = ProxyServer.get_running_server()
if proxy_info:
    ProxyServer.stop_running_server()
```

**检测逻辑：**
- 读取代理服务 PID 文件
- 检查进程是否存在
- 发送 SIGTERM 信号停止

### 还原 Claude Code 配置

```python
from .web.routers.claude_config import claude_config_manager

if claude_config_manager.is_proxy_applied():
    claude_config_manager.restore_config()
```

**还原流程：**
1. 检查是否存在备份配置
2. 从备份还原 `~/.claude/settings.json`
3. 删除备份文件和代理信息文件

## 📊 清理状态表

| 操作 | 默认 | --keep-proxy | --keep-config | 两者都保持 |
|-----|------|-------------|--------------|-----------|
| 停止 Web UI | ✅ | ✅ | ✅ | ✅ |
| 停止代理 | ✅ | ❌ | ✅ | ❌ |
| 还原配置 | ✅ | ✅ | ❌ | ❌ |

## 🔍 检测逻辑详解

### 1. 代理服务检测

**检测文件：** `~/.qcc/proxy.pid`

**检测步骤：**
```python
# 1. 读取 PID 文件
if pid_file.exists():
    with open(pid_file) as f:
        data = json.load(f)
        pid = data['pid']

# 2. 检查进程是否存在
os.kill(pid, 0)  # 信号 0 只检查进程

# 3. 返回代理信息
return {
    'pid': pid,
    'host': host,
    'port': port
}
```

### 2. 配置应用检测

**检测文件：**
- `~/.claude/settings.json.qcc_backup` - 备份配置
- `~/.claude/qcc_proxy_info.json` - 代理信息

**检测逻辑：**
```python
def is_proxy_applied():
    return (
        backup_file.exists() and
        proxy_info_file.exists()
    )
```

## 🎯 使用场景

### 场景 1: 日常使用结束

```bash
# 用完就关闭，完全清理
uvx qcc web stop
```

**结果：**
- ✅ Web UI 停止
- ✅ 代理停止
- ✅ 配置还原
- ✅ 系统恢复原状

### 场景 2: 临时关闭 Web UI

```bash
# 保持代理和配置，稍后继续使用
uvx qcc web stop --keep-proxy --keep-config
```

**结果：**
- ✅ Web UI 停止
- ❌ 代理继续运行
- ❌ 配置保持应用

### 场景 3: 只关闭 Web UI，保持代理

```bash
# 通过命令行继续使用代理
uvx qcc web stop --keep-proxy
```

**结果：**
- ✅ Web UI 停止
- ❌ 代理继续运行
- ✅ 配置还原（代理仍可用）

### 场景 4: 测试不同配置

```bash
# 保持配置以便测试
uvx qcc web stop --keep-config
```

**结果：**
- ✅ Web UI 停止
- ✅ 代理停止
- ❌ 配置保持（可以手动测试）

## ⚠️ 注意事项

### 1. 配置还原失败

如果还原失败，手动还原：

```bash
# 检查备份是否存在
ls ~/.claude/settings.json.qcc_backup

# 手动还原
cp ~/.claude/settings.json.qcc_backup ~/.claude/settings.json

# 清理
rm ~/.claude/settings.json.qcc_backup
rm ~/.claude/qcc_proxy_info.json
```

### 2. 代理停止失败

如果代理未停止，手动停止：

```bash
# 查找代理进程
ps aux | grep proxy

# 停止进程
kill -9 <PID>

# 清理 PID 文件
rm ~/.qcc/proxy.pid
```

### 3. 进程残留

如果有进程残留：

```bash
# 清理所有相关进程
pkill -f uvicorn
pkill -f vite

# 清理 PID 文件
rm -f ~/.qcc/web.pid
rm -f ~/.qcc/proxy.pid
```

## 🔄 完整清理流程

### 自动清理（推荐）

```bash
# 一条命令完成所有清理
uvx qcc web stop
```

### 手动清理

```bash
# 1. 停止 Web UI
uvx qcc web stop --keep-proxy --keep-config

# 2. 停止代理
uvx qcc proxy stop

# 3. 还原配置（通过 Web UI 或 API）
curl -X POST http://127.0.0.1:8080/api/claude-config/restore

# 或手动还原
cp ~/.claude/settings.json.qcc_backup ~/.claude/settings.json
```

## 📝 日志输出

### 成功清理示例

```
==================================================
🚀 QCC Web UI
==================================================
正在停止 Web UI (PID: 21990, 127.0.0.1:8080)...
✅ Web UI 已停止

ℹ️ 检测到代理服务正在运行，正在停止...
✅ 代理服务已停止

ℹ️ 检测到已应用代理配置，正在还原...
✅ Claude Code 配置已还原
```

### 无需清理示例

```
==================================================
🚀 QCC Web UI
==================================================
正在停止 Web UI (PID: 21990, 127.0.0.1:8080)...
✅ Web UI 已停止

ℹ️ 代理服务未运行，无需停止

ℹ️ 未应用代理配置，无需还原
```

### 保持代理和配置示例

```
==================================================
🚀 QCC Web UI
==================================================
正在停止 Web UI (PID: 21990, 127.0.0.1:8080)...
✅ Web UI 已停止

💡 提示: 代理服务仍在运行，使用 'uvx qcc proxy stop' 停止
💡 提示: Claude Code 配置未还原，请手动还原或在 Web UI 中还原
```

## 🎓 最佳实践

### 推荐做法

1. **日常使用**：使用默认清理
   ```bash
   uvx qcc web stop
   ```

2. **开发调试**：保持配置
   ```bash
   uvx qcc web stop --keep-config
   ```

3. **长期代理**：保持代理
   ```bash
   uvx qcc web stop --keep-proxy
   ```

### 不推荐做法

❌ **手动清理所有**：容易遗漏
```bash
# 不推荐：手动逐个停止
uvx qcc web stop --keep-proxy --keep-config
uvx qcc proxy stop
# 手动还原配置...
```

✅ **使用自动清理**：一键完成
```bash
# 推荐：自动完成所有清理
uvx qcc web stop
```

## 🆕 更新说明

**版本**: v0.5.0-web-ui
**更新日期**: 2025-10-18

**新增功能：**
- ✅ 停止时自动停止代理服务
- ✅ 停止时自动还原 Claude Code 配置
- ✅ 添加 `--keep-proxy` 选项
- ✅ 添加 `--keep-config` 选项
- ✅ 友好的清理状态提示

**向后兼容：**
- ✅ 完全兼容旧版本
- ✅ 默认行为更智能
- ✅ 可选择性保持某些服务

## 📚 相关文档

- [Web UI 快速开始](./web-ui/快速开始.md)
- [Web UI 一键启动](./web-ui-one-command-start.md)
- [代理服务管理](../proxy/)
- [Claude Code 配置](./claude-config.md)

---

**一键停止，自动清理，省心省力！** ✨
