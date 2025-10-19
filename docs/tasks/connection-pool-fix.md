# 连接池复用问题修复方案

## 问题描述

### 错误现象
频繁出现 `Cannot write to closing transport` 错误，导致：
- 请求成功率仅 28-33%
- 平均响应时间长达 3 秒
- 频繁触发 session 重置

### 根本原因
aiohttp 连接池复用机制与服务端超时配置不匹配：
1. 客户端设置 `force_close=False` 复用连接
2. 服务端可能在客户端 keepalive_timeout (60s) 之前关闭连接
3. 客户端尝试使用已关闭的连接时报错

## 解决方案（渐进式）

### 方案 1：禁用连接复用（最稳定，性能略降）

**修改**: `fastcc/proxy/server.py:716-727`

```python
# 当前配置（有问题）
connector=TCPConnector(
    limit=100,
    limit_per_host=20,
    force_close=False,  # ❌ 复用连接导致问题
    keepalive_timeout=60,
)

# 修复方案 1：禁用连接复用
connector=TCPConnector(
    limit=100,
    limit_per_host=10,     # 减少连接数
    force_close=True,      # ✅ 每次关闭连接
    keepalive_timeout=30,  # 减少保持时间
)
```

**优点**：
- ✅ 彻底解决连接复用问题
- ✅ 稳定性最高

**缺点**：
- ⚠️ 每次请求建立新连接（性能损失 10-20%）
- ⚠️ DNS 查询和 SSL 握手开销增加

### 方案 2：优化连接池参数（平衡性能与稳定性）

```python
connector=TCPConnector(
    limit=50,              # ✅ 减少总连接数
    limit_per_host=5,      # ✅ 大幅减少单主机连接（减少复用几率）
    ttl_dns_cache=300,
    force_close=False,     # 允许复用（但严格控制）
    keepalive_timeout=15,  # ✅ 大幅减少保持时间（15秒）
    enable_cleanup_closed=True
)
```

**优点**：
- ✅ 保留连接复用的性能优势
- ✅ 减少错误发生频率（但不能完全消除）

**缺点**：
- ⚠️ 仍可能偶尔出现连接关闭错误
- ⚠️ 需要调优参数

### 方案 3：混合策略（智能降级）

根据 endpoint 健康状态动态调整：

```python
def _create_client_session(self, endpoint=None):
    """根据 endpoint 健康状态创建 session"""

    # 如果 endpoint 不稳定，禁用连接复用
    if endpoint and endpoint.health_status.get('success_rate', 100) < 80:
        force_close = True
        keepalive = 0
        logger.info(f"Endpoint {endpoint.id} 不稳定，禁用连接复用")
    else:
        force_close = False
        keepalive = 30

    return ClientSession(
        timeout=ClientTimeout(total=300),
        connector=TCPConnector(
            limit=50,
            limit_per_host=5,
            force_close=force_close,  # 动态调整
            keepalive_timeout=keepalive,  # 动态调整
            enable_cleanup_closed=True
        )
    )
```

**优点**：
- ✅ 对稳定 endpoint 保持高性能
- ✅ 对不稳定 endpoint 自动降级

**缺点**：
- ⚠️ 实现复杂度增加
- ⚠️ 需要维护 endpoint 级别的 session

## 推荐方案

### 短期（立即修复）
**采用方案 1**：禁用连接复用

理由：
- 彻底解决问题，用户体验优先
- 性能损失可接受（10-20%）
- 实现简单，风险最低

### 中期（优化性能）
**采用方案 2**：优化连接池参数

在方案 1 稳定运行后，逐步优化：
1. 减少 keepalive_timeout 至 15 秒
2. 严格限制 limit_per_host（5 个连接）
3. 监控错误率变化

### 长期（智能优化）
**采用方案 3**：根据健康状态动态调整

条件：
- 需要完整的监控体系
- 需要充分的测试数据

## 实施计划

### 第一步：立即修复（方案 1）

```bash
# 修改代码
vim fastcc/proxy/server.py

# 重启服务
uvx --from . qcc proxy stop
uvx --from . qcc proxy start --cluster test

# 监控日志
tail -f ~/.fastcc/proxy.log | grep -i "cannot write"
```

### 第二步：监控效果

观察指标：
- ✅ "Cannot write to closing transport" 错误数量（应该为 0）
- ✅ 请求成功率（应该 > 95%）
- ✅ 平均响应时间（可能略微增加）

### 第三步：性能对比

使用压测工具对比：
```bash
# 方案 1（禁用复用）
# 预期：稳定性高，性能略降

# 方案 2（优化参数）
# 预期：稳定性中等，性能较好
```

## 参考资料

- [aiohttp Issue #4587](https://github.com/aio-libs/aiohttp/issues/4587)
- [Stack Overflow: Cannot write to closing transport](https://stackoverflow.com/questions/54462271)
- [aiohttp 最佳实践](https://docs.aiohttp.org/en/stable/client_advanced.html)

## 修复时间

- **发现时间**: 2025-10-19 10:47
- **分析完成**: 2025-10-19 10:50
- **建议方案**: 方案 1（短期）+ 方案 2（中期）
