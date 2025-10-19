# 失败队列节点隔离修复

## 问题描述

**问题现象**：配置了一个故意失败的主节点，虽然该节点被正确切换到了重试队列，但随着对话的进行，这个异常节点仍然会被标识为"使用中"，导致代理不受控制地切换到错误的节点。

**根本原因**：
1. **断路器超时机制**：断路器在 60 秒后自动尝试恢复（half-open 状态），导致失败队列中的 endpoint 重新进入可用列表
2. **健康状态与失败队列不同步**：endpoint 可能同时在失败队列中，但因断路器超时而被认为是"可用"的
3. **端点选择未过滤失败队列**：`_get_active_endpoints()` 和 `_select_endpoint()` 方法只检查 `enabled` 和 `is_healthy()`，未检查是否在失败队列中

## 解决方案

实现三队列架构的简化版本：**确保失败队列中的 endpoint 永远不会被正常代理使用**，只有经过验证恢复后才能重新使用。

### 架构设计

```
所有 Endpoint
├─ 主节点队列 (primary)    ← 优先使用
├─ 副节点队列 (secondary)   ← 其次使用
└─ 重试队列 (failure_queue) ← 永不使用（仅用于验证恢复）
```

**关键原则**：
- 同一节点只能存在于一个队列中
- 正常代理**永不使用**重试队列中的节点
- 只有失败队列验证器确认节点恢复后，才从重试队列移除并重新加入主/副队列

## 实施细节

### 修改 1: `_select_endpoint()` 方法

**文件**: `fastcc/proxy/server.py:397-437`

**修改内容**：
- 在选择 endpoint 时，优先排除失败队列中的节点
- 添加日志输出，明确标识重试队列中的节点被排除

```python
# ⚠️ 关键修复：排除失败队列中的 endpoint（永远不使用重试队列中的节点）
if self.failure_queue:
    failure_count = 0
    for ep in endpoints[:]:  # 使用切片创建副本进行迭代
        if ep.id in self.failure_queue.failed_endpoints:
            exclude_ids.add(ep.id)
            failure_count += 1
            logger.debug(f"跳过失败队列中的 endpoint: {ep.id}")
    if failure_count > 0:
        logger.info(f"失败队列过滤: 排除了 {failure_count} 个 endpoint（重试队列中的节点不用于正常代理）")
```

### 修改 2: `_get_active_endpoints()` 方法

**文件**: `fastcc/proxy/server.py:498-562`

**修改内容**：
- 在获取活跃端点时，直接过滤掉失败队列中的节点
- 添加失败队列计数统计，便于监控
- 增强日志输出，显示节点是否在失败队列中

```python
# 只返回启用且健康的 endpoint，同时排除失败队列中的节点
endpoints = [
    ep for ep in profile.endpoints
    if ep.enabled and ep.is_healthy() and (
        not self.failure_queue or ep.id not in self.failure_queue.failed_endpoints
    )
]
failed_count = sum(1 for ep in profile.endpoints if self.failure_queue and ep.id in self.failure_queue.failed_endpoints)
logger.info(f"配置 '{profile.name}': 总 {total_count} 个 endpoint, 健康 {len(endpoints)} 个, 失败队列 {failed_count} 个")
```

## 测试计划

### 测试场景 1: 故意失败的主节点

**步骤**：
1. 配置一个故意失败的主节点（例如错误的 API Key 或 URL）
2. 启动代理服务器
3. 发送请求，观察节点是否被加入失败队列
4. 持续发送请求，验证失败节点**永不被使用**
5. 检查日志，确认失败队列过滤生效

**预期结果**：
- 失败节点被加入失败队列
- 后续请求永不使用失败队列中的节点
- 失败队列验证器定期验证失败节点
- 日志中显示"失败队列过滤: 排除了 N 个 endpoint"

### 测试场景 2: 节点恢复

**步骤**：
1. 配置一个暂时失败的节点（例如临时网络问题）
2. 节点被加入失败队列
3. 修复节点问题（例如恢复网络）
4. 等待失败队列验证器验证（60秒周期）
5. 确认节点从失败队列移除后可以重新使用

**预期结果**：
- 失败队列验证器检测到节点恢复
- 节点从失败队列移除
- 断路器状态被重置
- 节点重新加入主/副队列，可被正常使用

### 测试场景 3: 多节点负载均衡

**步骤**：
1. 配置多个节点（例如 3 个主节点 + 2 个副节点）
2. 使其中 1 个主节点失败
3. 发送大量请求，观察负载分配
4. 验证失败节点**永不被使用**
5. 验证其他健康节点正常分担负载

**预期结果**：
- 失败节点被隔离在失败队列中
- 剩余健康节点均衡分担负载
- 无错误请求被路由到失败节点
- 系统整体可用性不受影响

## 监控和日志

### 关键日志标识

1. **失败队列过滤**：
```
INFO - 失败队列过滤: 排除了 1 个 endpoint（重试队列中的节点不用于正常代理）
```

2. **端点状态**：
```
INFO - 配置 'default': 总 3 个 endpoint, 健康 2 个, 失败队列 1 个
DEBUG - Endpoint ep-xxx: enabled=True, healthy=True, status=healthy, in_failure_queue=False
DEBUG - Endpoint ep-yyy: enabled=True, healthy=False, status=unhealthy, in_failure_queue=True
```

3. **节点恢复**：
```
INFO - ✅ Endpoint ep-yyy 已恢复健康 (123ms, 评分: 100)
DEBUG - 重置断路器状态: ep-yyy
```

### 统计 API

通过 `GET /__qcc__/stats` 可以查看：
```json
{
  "failed_endpoints": ["ep-yyy"],
  "failure_queue_size": 1,
  "endpoint_verify_counts": {
    "ep-yyy": 5
  }
}
```

## 影响范围

**修改文件**：
- `fastcc/proxy/server.py` (2 个方法修改)

**影响模块**：
- 端点选择逻辑
- 负载均衡器
- 失败队列处理器

**兼容性**：
- 向后兼容，不影响现有配置
- 不需要修改配置文件
- 自动生效，无需用户干预

## 验证结果

✅ 修复已完成
✅ 代码已自动热重载
✅ 所有修改已应用

## 下一步

1. 启动代理服务器进行实际测试
2. 配置故意失败的节点验证修复效果
3. 观察日志输出，确认失败队列隔离生效
4. 如有问题，请检查日志并反馈

---

**创建时间**: 2025-10-19
**修复状态**: 已完成
**测试状态**: 待验证
