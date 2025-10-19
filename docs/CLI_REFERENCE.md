# QCC CLI 命令参考

本文档列出所有实际可用的 QCC CLI 命令（基于当前实现）。

## 📌 命令格式说明

- **本地开发测试**: `uvx --from . qcc <command>`
- **远程安装使用**: `uvx qcc <command>`

以下示例使用远程安装格式，本地开发时请替换为 `uvx --from . qcc`。

---

## 🎯 核心命令

### 智能启动
```bash
uvx qcc                    # 智能启动 - 快速选择配置并启动 Claude Code
```

### 初始化
```bash
uvx qcc init               # 初始化配置，选择存储后端
```

### 配置管理
```bash
uvx qcc add <name>         # 添加新配置档案
uvx qcc list               # 列出所有配置
uvx qcc use <name>         # 使用指定配置
uvx qcc default <name>     # 设置默认配置
uvx qcc remove <name>      # 删除配置
```

### 同步与状态
```bash
uvx qcc sync               # 手动同步配置到云端
uvx qcc status             # 查看系统状态
```

### 厂商配置
```bash
uvx qcc fc                 # 厂商快速配置向导
```

### 配置设置
```bash
uvx qcc config             # 配置管理（交互式菜单）
                          # 1. 更改同步方式
                          # 2. 查看当前配置
```

### 卸载
```bash
uvx qcc uninstall          # 卸载本地配置
```

---

## 🎮 Web UI 管理命令 (v0.5.0+)

### web start - 启动 Web UI
```bash
uvx qcc web start [options]

选项:
  --host TEXT      监听地址 (默认: 127.0.0.1)
  --port INTEGER   监听端口 (默认: 8080)
  --dev            开发模式（前后端热重载）
  --no-browser     不自动打开浏览器

v0.6.1 修复:
  - 修复自定义端口时前端 API 地址不匹配问题
  - 前端现在动态使用当前页面地址，支持任意端口

示例:
  uvx qcc web start                    # 生产模式，默认端口 8080
  uvx qcc web start --port 9000        # 自定义端口（已修复）
  uvx qcc web start --dev              # 开发模式（仅限本地）
  uvx qcc web start --no-browser       # 不自动打开浏览器
```

### web status - 查看 Web UI 状态
```bash
uvx qcc web status                     # 显示 Web UI 运行状态
```

### web stop - 停止 Web UI
```bash
uvx qcc web stop [options]

选项:
  --keep-proxy     保持代理服务器运行
  --keep-config    保持配置不还原

示例:
  uvx qcc web stop                     # 完全清理（停止代理 + 还原配置）
  uvx qcc web stop --keep-proxy        # 保持代理运行
  uvx qcc web stop --keep-config       # 保持配置不还原
```

---

## 🌐 代理服务命令 (v0.4.0+)

### proxy start - 启动代理服务器
```bash
uvx qcc proxy start [options]

选项:
  --host TEXT      监听地址 (默认: 127.0.0.1)
  --port INTEGER   监听端口 (默认: 7860)
  --cluster TEXT   集群配置名称

v0.6.0 新增特性:
  - httpx 客户端：性能提升 33%，连接复用率 70%
  - 断路器模式：自动隔离故障节点，节点切换速度提升 80%
  - 会话亲和性：同一对话绑定同一节点，会话一致性 95%
  - 智能错误分类：误判率降低 80%（从 15% 降至 3%）
  - 负载均衡降级：多层降级策略确保高可用

示例:
  uvx qcc proxy start
  uvx qcc proxy start --port 8080
  uvx qcc proxy start --cluster production
```

### proxy status - 查看代理状态
```bash
uvx qcc proxy status      # 显示代理服务器运行状态
```

### proxy stop - 停止代理服务器
```bash
uvx qcc proxy stop        # 停止运行中的代理服务器
```

### proxy logs - 查看代理日志
```bash
uvx qcc proxy logs [options]

选项:
  --lines INTEGER  显示最后 N 行 (默认: 50)
  --follow, -f     实时跟踪日志

示例:
  uvx qcc proxy logs
  uvx qcc proxy logs --lines 100
  uvx qcc proxy logs -f
```

---

## 🏥 健康检测命令 (v0.4.0)

### health test - 执行对话测试
```bash
uvx qcc health test [endpoint_id] [options]

选项:
  --verbose, -v    显示详细信息

示例:
  uvx qcc health test                  # 测试所有 endpoint
  uvx qcc health test endpoint-1       # 测试指定 endpoint
  uvx qcc health test -v               # 显示详细信息
```

### health metrics - 查看性能指标
```bash
uvx qcc health metrics [endpoint_id]

示例:
  uvx qcc health metrics               # 所有 endpoint 的指标
  uvx qcc health metrics endpoint-1    # 指定 endpoint 的详细指标
```

### health check - 立即执行健康检查
```bash
uvx qcc health check      # 触发健康检查（需要代理服务器运行）
```

### health status - 查看健康状态
```bash
uvx qcc health status     # 查看所有 endpoint 的健康状态
```

### health history - 查看历史记录
```bash
uvx qcc health history <endpoint_id> [options]

选项:
  --limit INTEGER  显示最近 N 条记录 (默认: 10)

示例:
  uvx qcc health history endpoint-1
  uvx qcc health history endpoint-1 --limit 20
```

### health config - 配置健康检测参数
```bash
uvx qcc health config [options]

选项:
  --interval INTEGER                 检查间隔（秒）
  --enable-weight-adjustment         启用权重调整
  --disable-weight-adjustment        禁用权重调整
  --min-checks INTEGER               最小检查次数

示例:
  uvx qcc health config --interval 60
  uvx qcc health config --enable-weight-adjustment
```

---

## 📊 Endpoint 管理命令 (v0.4.0)

### endpoint add - 创建 Endpoint 集群配置
```bash
uvx qcc endpoint add <cluster_name> [options]

选项:
  --host TEXT         代理服务器监听地址 (默认: 127.0.0.1)
  --port INTEGER      代理服务器监听端口 (默认: 7860)
  --auto-start        创建后立即启动代理服务器和 Claude Code
  --no-auto-start     不自动启动（默认）

示例:
  uvx qcc endpoint add production                # 创建集群（默认不启动）
  uvx qcc endpoint add production --auto-start   # 创建并立即启动
```

### endpoint list - 列出 endpoints
```bash
uvx qcc endpoint list <config_name>

示例:
  uvx qcc endpoint list production
```

### endpoint remove - 删除 endpoint
```bash
uvx qcc endpoint remove <config_name> <endpoint_id>

示例:
  uvx qcc endpoint remove production endpoint-1
```

---

## ⚡ 优先级管理命令 (v0.4.0)

### priority set - 设置优先级
```bash
uvx qcc priority set <profile_name> <level>

级别选项:
  primary     主配置
  secondary   次配置
  fallback    兜底配置

示例:
  uvx qcc priority set production primary
  uvx qcc priority set backup secondary
  uvx qcc priority set emergency fallback
```

### priority list - 查看优先级配置
```bash
uvx qcc priority list     # 显示所有配置的优先级
```

### priority switch - 手动切换配置
```bash
uvx qcc priority switch <profile_name>

示例:
  uvx qcc priority switch backup
```

### priority history - 查看切换历史
```bash
uvx qcc priority history [options]

选项:
  --limit INTEGER  显示最近 N 条记录 (默认: 10)

示例:
  uvx qcc priority history
  uvx qcc priority history --limit 20
```

### priority policy - 配置故障转移策略
```bash
uvx qcc priority policy [options]

选项:
  --auto-failover            启用自动故障转移
  --no-auto-failover         禁用自动故障转移
  --auto-recovery            启用自动恢复
  --no-auto-recovery         禁用自动恢复
  --failure-threshold INT    故障阈值
  --cooldown INT             冷却期（秒）
  --recovery-checks INT      恢复检查次数

示例:
  uvx qcc priority policy --auto-failover --auto-recovery
  uvx qcc priority policy --failure-threshold 3 --cooldown 300
```

---

## 📋 失败队列命令 (v0.4.0)

### queue status - 查看队列状态
```bash
uvx qcc queue status      # 显示队列统计信息和状态
```

### queue list - 列出队列中的请求
```bash
uvx qcc queue list [options]

选项:
  --limit INTEGER  显示最多 N 个请求 (默认: 20)

示例:
  uvx qcc queue list
  uvx qcc queue list --limit 50
```

### queue retry - 重试单个请求
```bash
uvx qcc queue retry <request_id>

示例:
  uvx qcc queue retry req-abc123
```

### queue retry-all - 重试所有失败请求
```bash
uvx qcc queue retry-all   # 重试队列中所有待重试的请求
```

### queue clear - 清空队列
```bash
uvx qcc queue clear       # 清空失败队列
```

---

## 🔄 完整工作流示例

### 1. 基础配置流程
```bash
# 初始化
uvx qcc init

# 添加配置
uvx qcc add production --description "生产环境"
uvx qcc add backup --description "备用环境"

# 设置默认
uvx qcc default production

# 启动
uvx qcc
```

### 2. 创建 Endpoint 集群并启动代理
```bash
# 创建集群配置（交互式添加 endpoints）
uvx qcc endpoint add production

# 查看 endpoints
uvx qcc endpoint list production

# 启动代理服务器
uvx qcc proxy start --cluster production

# 配置 Claude Code
export ANTHROPIC_BASE_URL=http://127.0.0.1:7860
export ANTHROPIC_API_KEY=proxy-managed

# 启动 Claude Code
claude
```

### 3. 配置优先级和故障转移
```bash
# 设置优先级
uvx qcc priority set production primary
uvx qcc priority set backup secondary

# 配置故障转移策略
uvx qcc priority policy --auto-failover --auto-recovery \
  --failure-threshold 3 --cooldown 300

# 启动代理
uvx qcc proxy start
```

### 4. 监控和管理
```bash
# 查看代理状态
uvx qcc proxy status

# 查看健康状态
uvx qcc health status

# 执行健康测试
uvx qcc health test -v

# 查看性能指标
uvx qcc health metrics

# 查看队列状态
uvx qcc queue status

# 查看日志
uvx qcc proxy logs -f
```

---

## 📝 注意事项

1. **配置文件位置**: `~/.fastcc/` 或 `~/.qcc/`
2. **日志文件**: `~/.qcc/proxy.log`
3. **默认代理端口**: 7860
4. **默认 Web UI 端口**: 8080 (v0.5.0+)
5. **健康检查数据**: `~/.qcc/health_metrics.json`
6. **失败队列数据**: `~/.qcc/failure_queue.json`

### v0.6.x 新特性

**v0.6.1** (2025-10-19):
- 修复自定义端口时前端 API 地址不匹配问题
- 前端动态获取 API 地址，支持任意端口

**v0.6.0** (2025-10-19):
- httpx 迁移：性能提升 33%，连接复用率 70%
- 断路器模式：节点切换速度提升 80%
- 会话亲和性：会话一致性提升至 95%
- 错误分类器：误判率降低 80%
- 负载均衡降级：智能多层降级策略
- Windows 平台兼容性修复

---

## 🔗 相关文档

- [README.md](../README.md) - 项目主文档
- [v0.6.1 发布说明](./releases/v0.6.1.md) - 自定义端口修复
- [v0.6.0 发布说明](./releases/v0.6.0.md) - 重大性能优化
- [v0.5.0 发布说明](./releases/v0.5.0.md) - Web UI 管理界面
- [v0.4.0 开发文档](./tasks/v0.4.0-代理服务/) - 代理服务详细技术文档
- [完成报告](./tasks/v0.4.0-代理服务/COMPLETION_REPORT.md) - v0.4.0 完成情况

---

**文档版本**: 2.0
**最后更新**: 2025-10-19
**基于代码版本**: v0.6.1
