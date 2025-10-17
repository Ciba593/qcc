# QCC Endpoint 集群配置指南

## 概述

`qcc endpoint add` 命令现已升级为**智能集群配置**功能，支持：
- ✨ 创建任意名称的 endpoint 集群
- 🎯 多选主节点和副节点
- 🚀 自动启动代理服务器
- 💻 自动启动 Claude Code
- 🔄 自动负载均衡和故障转移

## 快速开始

### 1. 基础用法

```bash
# 创建一个名为 production 的集群配置
qcc endpoint add production
```

### 2. 交互式流程

```
==================================================
🚀 创建 Endpoint 集群配置: production
==================================================

──────────────────────────────────────────────────
📍 步骤 1/2: 选择主节点（优先级高，优先使用）
──────────────────────────────────────────────────
可用配置:
  1. codecmd - 订阅
  2. deepseek - 无描述
  3. aicodewith - 无描述
  4. ccapi - 无描述
  5. 88code - 无描述

请选择主节点 (多选用逗号分隔，如: 1,2,4): 1,5

──────────────────────────────────────────────────
📍 步骤 2/2: 选择副节点（故障转移，主节点失败时使用）
──────────────────────────────────────────────────
剩余配置:
  2. deepseek - 无描述
  3. aicodewith - 无描述
  4. ccapi - 无描述

请选择副节点 (多选用逗号分隔，或直接回车跳过): 2,3

==================================================

✅ 集群配置创建成功！

集群配置 'production':
  主节点: codecmd, 88code
  副节点: deepseek, aicodewith
  总计: 4 个 endpoint

1. [主节点] ID: abc12345 | URL: https://... | Key: sk-ant... | 权重: 100 | 优先级: 1 | 启用: ✓ | 健康: ? | 来源: codecmd
2. [主节点] ID: def67890 | URL: https://... | Key: 88_1cd... | 权重: 100 | 优先级: 1 | 启用: ✓ | 健康: ? | 来源: 88code
3. [副节点] ID: ghi11121 | URL: https://... | Key: sk-abc... | 权重: 100 | 优先级: 2 | 启用: ✓ | 健康: ? | 来源: deepseek
4. [副节点] ID: jkl31415 | URL: https://... | Key: sk-xyz... | 权重: 100 | 优先级: 2 | 启用: ✓ | 健康: ? | 来源: aicodewith

是否立即启动代理服务器和 Claude Code？ (Y/n):
```

### 3. 自动启动流程

选择 `Y` 后：

```
✅ 应用集群配置: production

✅ Claude Code 配置已更新

✅ 启动代理服务器...
✅ 代理服务器已启动: http://127.0.0.1:7860 (PID: 12345)
   日志文件: /Users/xxx/.qcc/proxy.log

✅ 启动 Claude Code...

==================================================

✅ 集群配置已激活！

📊 集群状态:
   配置: production
   代理: http://127.0.0.1:7860
   Endpoints: 已加载

💡 使用方法:
   1. Claude Code 将通过代理服务器访问所有 endpoints
   2. 代理服务器会自动进行负载均衡和故障转移
   3. 查看代理状态: qcc proxy status
   4. 查看健康状态: qcc health status

🚀 正在启动 Claude Code...
```

## 命令选项

```bash
qcc endpoint add <集群名称> [选项]
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `<集群名称>` | 新集群的名称（必填，不能与现有配置重名） | - |
| `--host` | 代理服务器监听地址 | `127.0.0.1` |
| `--port` | 代理服务器监听端口 | `7860` |
| `--no-auto-start` | 创建配置但不自动启动 | `False` |

### 使用示例

```bash
# 创建集群并自动启动
qcc endpoint add production

# 创建集群但不自动启动
qcc endpoint add production --no-auto-start

# 自定义代理服务器地址和端口
qcc endpoint add production --host 0.0.0.0 --port 8080
```

## 工作原理

### 1. 节点选择

- **主节点**（优先级 1）：优先使用，权重为 100
- **副节点**（优先级 2）：主节点失败时使用，权重为 100

### 2. 负载均衡策略

代理服务器会：
1. 优先使用主节点（priority=1）
2. 主节点内部按权重进行负载均衡
3. 当所有主节点失败时，自动切换到副节点
4. 副节点恢复后，可配置自动切回主节点

### 3. 故障转移

- 连续失败阈值：3 次（可配置）
- 健康检查间隔：60 秒（可配置）
- 自动重试队列：失败的请求会进入队列等待重试

## 管理集群

### 查看集群配置

```bash
# 查看所有配置（包括集群）
qcc list

# 查看特定集群的 endpoints
qcc endpoint list production
```

### 删除集群

```bash
qcc remove production
```

### 使用集群启动 Claude Code

```bash
# 直接使用集群配置
qcc use production

# 或者通过 endpoint add 再次启动
qcc endpoint add production  # 会提示已存在
```

## 监控和维护

### 查看代理服务器状态

```bash
# 查看服务器运行状态
qcc proxy status

# 查看日志
qcc proxy logs
qcc proxy logs -f  # 实时跟踪

# 停止代理服务器
qcc proxy stop
```

### 查看健康状态

```bash
# 查看所有 endpoint 健康状态
qcc health status

# 查看详细指标
qcc health metrics

# 查看指定 endpoint 的指标
qcc health metrics <endpoint-id>

# 手动执行健康检查
qcc health test
```

### 查看故障转移历史

```bash
# 查看切换历史
qcc priority history

# 查看失败队列
qcc queue status
qcc queue list
```

## 高级配置

### 配置健康检查

```bash
# 设置检查间隔为 30 秒
qcc health config --interval 30

# 启用动态权重调整
qcc health config --enable-weight-adjustment

# 设置最少检查次数
qcc health config --min-checks 5
```

### 配置故障转移策略

```bash
# 启用自动故障转移和恢复
qcc priority policy --auto-failover --auto-recovery

# 设置故障阈值
qcc priority policy --failure-threshold 5

# 设置冷却期（秒）
qcc priority policy --cooldown 300
```

## 最佳实践

### 1. 节点选择建议

- **主节点**：选择稳定、高速的节点（1-3 个）
- **副节点**：选择备用节点，确保高可用（2-4 个）
- **总数控制**：建议总 endpoint 数量在 3-7 个之间

### 2. 权重配置

默认所有节点权重为 100，可根据需要调整：
- 高性能节点：增加权重（如 150-200）
- 备用节点：降低权重（如 50-80）

### 3. 监控建议

- 定期查看 `qcc health status` 确保节点健康
- 查看 `qcc priority history` 了解故障转移情况
- 监控 `~/.qcc/proxy.log` 日志文件

### 4. 故障处理

如果某个 endpoint 持续失败：
```bash
# 1. 查看健康状态
qcc health status

# 2. 查看详细指标
qcc health metrics <endpoint-id>

# 3. 查看历史记录
qcc health history <endpoint-id>

# 4. 必要时删除并重新添加
qcc remove production
qcc endpoint add production  # 重新配置
```

## 故障排查

### 问题：代理服务器启动失败

```bash
# 检查端口是否被占用
lsof -i :7860

# 查看日志
cat ~/.qcc/proxy.log

# 尝试使用其他端口
qcc endpoint add production --port 8080
```

### 问题：Claude Code 连接失败

```bash
# 检查 Claude Code 配置
cat ~/.claude/settings.json

# 确认代理服务器运行
qcc proxy status

# 查看代理日志
qcc proxy logs -f
```

### 问题：所有节点都失败

```bash
# 查看失败队列
qcc queue status
qcc queue list

# 手动重试失败请求
qcc queue retry-all

# 检查各节点健康状态
qcc health test -v
```

## 迁移指南

### 从旧版 endpoint add 迁移

旧版命令（已弃用）：
```bash
qcc endpoint add existing-config  # 为现有配置添加 endpoint
```

新版命令（推荐）：
```bash
qcc endpoint add new-cluster  # 创建新的集群配置
```

如果需要为现有配置添加 endpoint，建议：
1. 创建新的集群配置
2. 选择现有配置作为主/副节点
3. 删除旧配置（可选）

## 总结

`qcc endpoint add` 现在是一个强大的集群管理工具：

✅ **简化操作**：一个命令完成集群创建、启动、配置
✅ **智能选择**：交互式多选主/副节点
✅ **自动化**：自动启动代理和 Claude Code
✅ **高可用**：自动负载均衡和故障转移
✅ **易监控**：完整的健康检查和监控命令

现在就试试创建你的第一个 endpoint 集群吧！🚀
