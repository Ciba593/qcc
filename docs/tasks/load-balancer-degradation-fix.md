# 负载均衡器降级策略修复

## 问题描述

### 用户报告
用户遇到 502 错误：`{"error":"All 0 endpoints failed"}`

### 问题现象
- 代理返回 "All 0 endpoints failed"
- 日志显示没有尝试任何 endpoint
- 虽然有可用节点（degraded 状态），但未被使用

## 根本原因分析

### 架构矛盾

系统中存在两个组件的降级策略不一致：

| 组件 | 降级策略 | 行为 |
|------|---------|------|
| `ProxyServer._get_active_endpoints()` | ✅ 完整降级链<br>healthy → degraded → unhealthy → circuit_open | 在极端情况下会返回 degraded/unhealthy 节点 |
| `LoadBalancer.select_endpoint()` | ❌ 无降级逻辑<br>只接受 `is_healthy() == True` | 拒绝所有非 healthy 节点，返回 None |

### 失败流程

```
用户请求
  ↓
ProxyServer._get_active_endpoints()
  ├─ 排除失败队列中的节点（491d512f，认证失败）
  ├─ 排除断路器打开的节点（111f4745）
  ├─ 没有 healthy/degraded 节点
  ├─ 触发极端降级策略
  └─ ✅ 返回 [111f4745] (断路器打开的节点)
  ↓
LoadBalancer.select_endpoint([111f4745])
  ├─ 检查 111f4745.is_healthy() → False
  ├─ healthy_endpoints = []
  └─ ❌ 返回 None (拒绝非健康节点)
  ↓
ProxyServer.handle_request()
  ├─ endpoint = None
  └─ ❌ 错误: "All 0 endpoints failed"
```

### 日志证据

```log
2025-10-19 10:39:50,828 - 集群 'test': 所有节点都不可用，强制尝试 1 个断路器打开的 endpoint
2025-10-19 10:39:50,828 - 集群 'test': 总 2 个 endpoint, 健康 0 个, 降级 0 个, 失败队列 1 个
2025-10-19 10:39:50,829 - 可用 endpoints 数量: 1
2025-10-19 10:39:50,829 - LoadBalancer.select_endpoint 调用: 策略=priority_failover, 输入 endpoints=1
2025-10-19 10:39:50,829 - 健康 endpoints: 0/1
2025-10-19 10:39:50,829 - 没有健康的 endpoints
2025-10-19 10:39:50,829 - 负载均衡器选择: None  # ❌ 这里拒绝了 degraded 节点
2025-10-19 10:39:50,829 - [req-8] 没有更多可用的 endpoint（已排除 0 个）
2025-10-19 10:39:50,829 - [req-8] ✗ 尝试了 0 个 endpoint，共 0 次，全部失败
```

## 解决方案

### 修改内容

修改 `fastcc/proxy/load_balancer.py` 的 `select_endpoint()` 方法，增加降级逻辑：

**降级策略（与 `_get_active_endpoints()` 保持一致）**：
1. **优先**：选择 `healthy` 状态的 endpoint
2. **降级**：如果没有 healthy，选择 `degraded` 状态的 endpoint
3. **极端降级**：如果也没有 degraded，选择任何可用的 endpoint（包括 unhealthy）

### 代码变更

```python
# 修改前（只接受 healthy）
healthy_endpoints = [ep for ep in endpoints if ep.is_healthy()]
if not healthy_endpoints:
    return None  # ❌ 直接拒绝

# 修改后（支持降级）
healthy_endpoints = []
degraded_endpoints = []

for ep in endpoints:
    status = ep.health_status.get('status', 'unknown')
    if ep.is_healthy():
        healthy_endpoints.append(ep)
    elif status == 'degraded':
        degraded_endpoints.append(ep)

# 降级策略：healthy > degraded > any
if healthy_endpoints:
    selected_endpoints = healthy_endpoints
elif degraded_endpoints:
    selected_endpoints = degraded_endpoints  # ✅ 降级使用
    logger.warning(f"降级使用 {len(degraded_endpoints)} 个 degraded endpoint")
elif endpoints:
    selected_endpoints = endpoints  # ✅ 极端降级
    logger.error(f"极端降级使用所有 endpoint")
else:
    return None
```

### 预期效果

修复后的行为：

```
用户请求
  ↓
ProxyServer._get_active_endpoints()
  └─ ✅ 返回 [111f4745] (degraded 节点)
  ↓
LoadBalancer.select_endpoint([111f4745])
  ├─ healthy_endpoints = []
  ├─ degraded_endpoints = [111f4745]
  ├─ ✅ 降级使用 degraded endpoint
  └─ ✅ 返回 111f4745
  ↓
ProxyServer.handle_request()
  ├─ ✅ 尝试使用 111f4745
  └─ ✅ 成功或失败（但至少尝试了）
```

## 测试建议

### 场景 1：正常情况
- **配置**：2 个 healthy endpoint
- **预期**：选择 healthy endpoint
- **验证**：日志显示 "类型: healthy"

### 场景 2：降级情况
- **配置**：1 个 degraded endpoint，1 个 unhealthy endpoint
- **预期**：选择 degraded endpoint
- **验证**：日志显示 "降级使用 1 个 degraded endpoint"

### 场景 3：极端降级
- **配置**：所有 endpoint 都是 unhealthy
- **预期**：选择 unhealthy endpoint（作为最后手段）
- **验证**：日志显示 "极端降级使用所有 endpoint"

### 场景 4：失败队列隔离
- **配置**：1 个在失败队列，1 个 degraded
- **预期**：使用 degraded endpoint，不使用失败队列中的
- **验证**：日志显示 degraded endpoint 被选中

## 影响范围

### 受影响的组件
- ✅ `LoadBalancer.select_endpoint()`: 核心修改
- ✅ 所有负载均衡策略（weighted, round_robin, random, least_connections, priority_failover）

### 向后兼容性
- ✅ 完全兼容：降级策略是可选的，只在极端情况下触发
- ✅ 不影响正常流程：当有 healthy endpoint 时，行为与之前完全一致

### 性能影响
- ✅ 最小化：只增加了状态分类逻辑（O(n)，n 为 endpoint 数量）
- ✅ 无额外 I/O：纯内存操作

## 配置建议

### 最佳实践
1. **配置多个 endpoint**：确保至少有 2-3 个可用节点
2. **监控健康状态**：通过 `/__qcc__/stats` 监控节点健康
3. **及时修复失败节点**：失败队列会自动验证和恢复

### 配置示例

```bash
# 查看当前状态
uvx qcc proxy status

# 查看统计信息（包括 endpoint 健康状态）
curl http://127.0.0.1:7860/__qcc__/stats

# 如果发现 degraded 节点，检查原因并修复
uvx qcc config list
```

## 相关文档

- [故障队列隔离修复](./failure-queue-isolation-fix.md)
- [代理改进完成记录](./proxy-improvements-completed.md)

## 修复时间

- **发现时间**: 2025-10-19 10:42
- **修复时间**: 2025-10-19 10:45
- **修复人员**: Claude Code
