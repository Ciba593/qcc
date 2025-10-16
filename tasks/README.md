# QCC v0.4.0 开发任务文档

## 📚 文档索引

本目录包含 QCC v0.4.0 版本的所有开发计划和技术实现文档。

### 核心文档

1. **[claude-code-proxy-development-plan.md](./claude-code-proxy-development-plan.md)** - 主开发计划
   - 项目整体架构和规划
   - 6 大核心功能详细设计
   - 开发里程碑和时间线
   - 使用示例和最佳实践

2. **[endpoint-reuse-implementation.md](./endpoint-reuse-implementation.md)** - Endpoint 配置复用
   - 从现有配置快速复用 API Key
   - 三种 endpoint 添加方式
   - 数据模型和 CLI 命令实现
   - 完整的使用流程和测试用例

3. **[auto-failover-mechanism.md](./auto-failover-mechanism.md)** - 自动故障转移机制
   - 智能配置优先级管理
   - 自动故障检测和切换
   - 故障恢复和历史追踪
   - 实时监控和告警通知

4. **[intelligent-health-check.md](./intelligent-health-check.md)** - 智能健康检测 🆕
   - 真实对话测试取代 ping
   - 多维度性能评估
   - 动态权重自动调整
   - 性能指标统计分析

---

## 🎯 核心功能概览

### 1. Claude Code 代理服务 🚀
提供本地代理服务器，拦截和转发 Claude Code 的 API 请求。

**关键特性:**
- 本地 HTTP/HTTPS 代理服务器
- 流式响应支持 (SSE)
- 请求/响应日志记录
- 透明代理模式

**CLI 命令:**
```bash
qcc proxy start              # 启动代理服务
qcc proxy stop               # 停止代理服务
qcc proxy status             # 查看代理状态
qcc proxy logs               # 查看代理日志
```

---

### 2. 多 API Key 配置管理 🔑
为每个配置档案添加多个 API Key 和 Base URL，实现负载均衡。

**关键特性:**
- 每个配置支持多个 endpoint
- **从现有配置复用** (新增) ⭐
- 支持权重和优先级设置
- Endpoint 启用/禁用管理

**三种添加方式:**
1. 从现有配置复用（推荐）
2. 手动输入新配置
3. 从厂商快速配置

**CLI 命令:**
```bash
qcc endpoint add <config-name>           # 添加 endpoint (交互式)
qcc endpoint add <config-name> -f work   # 从 work 配置复用
qcc endpoint list <config-name>          # 查看 endpoint 列表
qcc endpoint remove <config-name> <id>   # 删除 endpoint
```

**使用示例:**
```bash
# 从现有配置快速复用
qcc endpoint add production
# 选择: 1 (从现有配置复用)
# 选择配置: work
# 权重: 100, 优先级: 1
# ✅ Endpoint 添加成功！
```

---

### 3. 主次配置策略 ⭐
配置三级优先级体系：Primary（主） → Secondary（次） → Fallback（兜底）

**关键特性:**
- 三级优先级管理
- 配置组管理
- **自动故障转移** (新增) 🔄
- **自动恢复** (新增) ✅
- 智能切换策略

**故障转移流程:**
```
Primary 配置失败
  ↓ 自动检测
  ↓ 达到故障阈值（如 3 次）
  ↓ 触发故障转移
Secondary 配置接管
  ↓ 继续提供服务
  ↓ 监控 Primary 恢复
Primary 恢复健康
  ↓ 自动切回（可选）
```

**CLI 命令:**
```bash
qcc priority set production primary      # 设置为主配置
qcc priority set backup secondary        # 设置为次配置
qcc priority set emergency fallback      # 设置为兜底配置
qcc priority list                        # 查看优先级配置
qcc priority switch backup               # 手动切换配置
qcc priority history                     # 查看切换历史

# 配置故障转移策略
qcc priority policy --auto-failover --auto-recovery \
  --failure-threshold 3 --cooldown 300
```

**使用示例:**
```bash
# 配置三级故障转移
qcc priority set production primary
qcc priority set backup secondary
qcc priority set emergency fallback

qcc priority policy --auto-failover --auto-recovery

qcc proxy start
# ✓ 代理服务器已启动
# ✓ 故障转移监控已启动

# 当 production 失败时:
# 🔄 故障转移: production → backup
# 原因: 连续 3 次健康检查失败
# ✓ 故障转移完成，当前使用配置: backup
```

---

### 4. 后台健康检测机制 🏥
定时检查所有 endpoint 的健康状态，自动发现和标记失败。

**关键特性:**
- 定时健康检测（可配置间隔）
- 多层次检测（连接、API、性能）
- 健康度评分系统
- 健康状态持久化

**健康状态模型:**
```json
{
  "status": "healthy",
  "last_check": "2025-10-16T12:00:00Z",
  "consecutive_failures": 0,
  "success_rate": 99.5,
  "avg_response_time": 250
}
```

**CLI 命令:**
```bash
qcc health check                    # 立即执行健康检查
qcc health status                   # 查看所有 endpoint 健康状态
qcc health history <endpoint-id>    # 查看历史健康记录
qcc health config                   # 配置健康检测参数
```

---

### 5. 故障转移队列 📋
失败请求自动入队，支持多种重试策略。

**关键特性:**
- 失败请求自动入队
- 多种重试策略（指数退避、固定间隔、立即重试）
- 队列持久化
- 优先级队列

**重试策略:**
- **指数退避**: 5s → 10s → 20s → ... (最大 300s)
- **固定间隔**: 每次重试间隔固定
- **立即重试**: 失败后立即重试

**CLI 命令:**
```bash
qcc queue status                     # 查看队列状态
qcc queue list                       # 列出队列中的请求
qcc queue retry <request-id>         # 手动重试某个请求
qcc queue retry-all                  # 重试所有失败请求
qcc queue clear                      # 清空队列
```

---

### 6. 终端配置管理 ⚙️
所有功能都可通过终端命令配置和管理。

**配置项分类:**
- `proxy.*` - 代理配置
- `health.*` - 健康检测配置
- `queue.*` - 队列配置
- `loadbalancer.*` - 负载均衡配置

**CLI 命令:**
```bash
qcc config get <key>                 # 获取配置项
qcc config set <key> <value>         # 设置配置项
qcc config list                      # 列出所有配置
qcc config reset [key]               # 重置配置
qcc config export <file>             # 导出配置
qcc config import <file>             # 导入配置
```

---

## 🏗️ 技术架构

### 系统架构图

```
┌──────────────────────────────────────────────┐
│           Claude Code Client                 │
└──────────────────┬───────────────────────────┘
                   │
                   ↓
┌──────────────────────────────────────────────┐
│          QCC Proxy Server                    │
│  ┌────────────────────────────────────┐     │
│  │    Request Router                  │     │
│  └────────────┬───────────────────────┘     │
│               │                              │
│  ┌────────────┴───────────────────────┐     │
│  │    Failover Manager (新增)         │     │
│  │    - 自动故障转移                   │     │
│  │    - 自动恢复                      │     │
│  │    - 切换策略管理                  │     │
│  └────────────┬───────────────────────┘     │
│               │                              │
│  ┌────────────┴───────────────────────┐     │
│  │    Priority Manager (新增)         │     │
│  │    - 优先级管理                    │     │
│  │    - 配置组管理                    │     │
│  └────────────┬───────────────────────┘     │
│               │                              │
│  ┌────────────┴───────────────────────┐     │
│  │    Load Balancer                   │     │
│  └────────────┬───────────────────────┘     │
│               │                              │
│  ┌────────────┴───────────────────────┐     │
│  │    Health Monitor                  │     │
│  └────────────────────────────────────┘     │
└──────────────────┬───────────────────────────┘
                   │
   ┌───────────────┼───────────────┐
   ↓               ↓               ↓
┌─────────┐  ┌──────────┐  ┌──────────┐
│ Primary │  │Secondary │  │ Fallback │
│ Config  │  │  Config  │  │  Config  │
└─────────┘  └──────────┘  └──────────┘
```

### 核心模块

```
fastcc/
├── proxy/                     # 🆕 代理服务模块
│   ├── server.py              # 代理服务器
│   ├── load_balancer.py       # 负载均衡器
│   ├── health_monitor.py      # 健康监控器
│   ├── failure_queue.py       # 失败队列
│   └── failover_manager.py    # 🆕 故障转移管理器
├── core/
│   ├── config.py              # 配置管理 (扩展)
│   ├── endpoint.py            # 🆕 Endpoint 模型
│   └── priority_manager.py    # 🆕 优先级管理器
└── utils/
    ├── logger.py              # 🆕 日志工具
    └── validator.py           # 🆕 验证工具
```

---

## 📅 开发计划

**预计完成时间**: 3-4 周 (基于复杂度评估)

### Phase 1: 基础架构 (5-7 天)
- [ ] 代理服务器基础框架
- [ ] Endpoint 数据模型
- [ ] 基本请求拦截和转发
- [ ] 配置管理扩展
- [ ] **异步运行时管理器** (新增)
- [ ] **并发控制器** (新增)

### Phase 2: 负载均衡与健康检测 (5-7 天)
- [ ] 负载均衡器实现
- [ ] **分级健康检测** (快速/轻量/深度)
- [ ] **Endpoint 配置复用功能** (新增)
- [ ] 多种负载均衡策略
- [ ] **动态权重调整** (新增)

### Phase 3: 故障转移机制 (7-10 天)
- [ ] **Priority Manager 实现** (新增)
- [ ] **Failover Manager 实现** (新增)
- [ ] **自动故障转移逻辑** (新增)
- [ ] **自动恢复机制** (新增)
- [ ] 失败队列实现
- [ ] 重试策略实现
- [ ] **配置校验和回滚** (新增)

### Phase 4: 完善和优化 (5-7 天)
- [ ] 终端配置命令完善
- [ ] 性能优化和压力测试
- [ ] 监控和统计
- [ ] **部署和故障排查文档** (新增)
- [ ] **uvx 集成测试** (必需)
- [ ] 全面测试 (覆盖率 > 80%)

---

## 🚀 快速开始

### 完整使用流程

```bash
# 1. 初始化
qcc init

# 2. 创建配置
qcc add production --description "生产环境"
qcc add backup --description "备用环境"

# 3. 为生产配置添加多个 endpoint (从现有配置复用)
qcc endpoint add production -f work      # 从 work 配置复用
qcc endpoint add production -f personal  # 从 personal 配置复用

# 4. 设置优先级
qcc priority set production primary
qcc priority set backup secondary

# 5. 配置故障转移策略
qcc priority policy --auto-failover --auto-recovery

# 6. 启动代理服务
qcc proxy start
# ✓ 代理服务器已启动: http://127.0.0.1:7860
# ✓ 故障转移监控已启动

# 7. 查看状态
qcc priority list
qcc health status
qcc queue status

# 8. 配置 Claude Code 使用代理
export ANTHROPIC_BASE_URL=http://127.0.0.1:7860
export ANTHROPIC_API_KEY=proxy-managed

# 9. 启动 Claude Code
claude
```

---

## 📊 核心优势

### 1. 高可用性 🛡️
- 三级配置优先级
- 自动故障检测和转移
- 失败请求自动重试
- 多 endpoint 负载均衡

### 2. 易用性 ⭐
- **从现有配置快速复用**
- 交互式命令行界面
- 清晰的状态显示
- 详细的日志和历史记录

### 3. 灵活性 🔧
- 多种负载均衡策略
- 可配置的切换策略
- 手动和自动切换
- 支持自定义通知

### 4. 可靠性 💪
- 健康状态持久化
- 队列持久化
- 故障历史追踪
- 频率限制保护

---

## 🧪 测试策略

### 单元测试
- Endpoint 模型测试
- Priority Manager 测试
- Failover Manager 测试
- Health Monitor 测试

### 集成测试
- 端到端故障转移测试
- 多 endpoint 负载均衡测试
- 自动恢复测试
- 配置复用测试

### 性能测试
- 并发请求测试
- 响应时间测试
- 长时间运行稳定性测试

---

## 📈 性能指标

- **代理延迟**: < 50ms
- **并发请求**: > 100
- **故障检测**: < 60s
- **故障转移时间**: < 5s
- **测试覆盖率**: > 80%

---

## 📞 相关资源

- **主仓库**: https://github.com/lghguge520/qcc
- **文档**: ./claude-code-proxy-development-plan.md
- **Issues**: https://github.com/lghguge520/qcc/issues

---

## 📝 更新日志

### 2025-10-16
- ✅ 创建主开发计划文档
- ✅ 添加 Endpoint 配置复用功能设计
- ✅ 添加自动故障转移机制设计
- ✅ 完善使用示例和测试用例

---

**文档版本**: v1.0
**创建日期**: 2025-10-16
**维护者**: QCC Development Team
