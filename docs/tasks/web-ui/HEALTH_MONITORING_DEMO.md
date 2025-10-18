# 健康监控功能演示指南

## 快速开始

### 1. 启动 Web UI

```bash
# 确保在项目根目录
cd /path/to/qcc

# 启动 Web 服务
uvx --from . qcc web start
```

服务启动后，访问 `http://127.0.0.1:8080`

### 2. 访问健康监控页面

**方法 1**: 通过导航菜单
1. 在左侧导航栏点击"健康监控"（心形图标）
2. 进入健康监控页面

**方法 2**: 通过 Dashboard
1. 在 Dashboard 页面查看"Endpoint 健康状况"卡片
2. 点击右上角"查看详情"按钮

### 3. 查看健康状态

健康监控页面显示：

#### 顶部统计卡片
- **健康**: 状态正常的 endpoint 数量（绿色）
- **降级**: 性能下降的 endpoint 数量（黄色）
- **不健康**: 故障的 endpoint 数量（红色）
- **未知**: 未检查的 endpoint 数量（灰色）

#### 详情表格
显示每个 endpoint 的详细信息：
- 状态图标和标签
- Endpoint ID 和 URL
- 成功率（进度条）
- 平均响应时间
- 请求统计（总数和失败数）
- 最后检查时间
- 启用/禁用状态
- 测试按钮

### 4. 执行健康测试

**测试单个 endpoint**:
- 在表格中找到目标 endpoint
- 点击右侧的"测试"按钮
- 等待测试完成，状态自动更新

**测试所有 endpoint**:
- 点击页面右上角的"测试所有 Endpoint"按钮
- 等待批量测试完成
- 所有 endpoint 状态将自动刷新

### 5. 使用 API

#### 获取健康状态

```bash
curl http://127.0.0.1:8080/api/health/status
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "summary": {
      "healthy": 5,
      "degraded": 1,
      "unhealthy": 2,
      "unknown": 0,
      "total": 8
    },
    "endpoints": [...]
  }
}
```

#### 执行健康测试

```bash
# 测试所有 endpoint
curl -X POST http://127.0.0.1:8080/api/health/test

# 测试特定 endpoint
curl -X POST "http://127.0.0.1:8080/api/health/test?endpoint_id=36fb0ed6"
```

#### 获取性能指标

```bash
# 所有 endpoint 的指标
curl http://127.0.0.1:8080/api/health/metrics

# 特定 endpoint 的指标
curl "http://127.0.0.1:8080/api/health/metrics?endpoint_id=36fb0ed6"
```

## 功能特性

### 自动刷新
- 健康状态每 10 秒自动刷新
- Dashboard 健康数据每 10 秒更新
- 无需手动刷新页面

### 状态说明

| 状态 | 图标 | 颜色 | 说明 |
|------|------|------|------|
| 健康 (healthy) | ✓ | 绿色 | Endpoint 正常工作 |
| 降级 (degraded) | ⚠ | 黄色 | 性能下降或受限 |
| 不健康 (unhealthy) | ✗ | 红色 | Endpoint 故障或不可用 |
| 未知 (unknown) | ? | 灰色 | 尚未检查或数据不足 |

### 成功率计算

成功率 = (总请求数 - 失败请求数) / 总请求数 × 100%

- **≥90%**: 绿色进度条（健康）
- **70%-90%**: 蓝色进度条（正常）
- **<70%**: 红色进度条（警告）

### 响应时间显示

- **<1000ms**: 显示为毫秒（如 "150ms"）
- **≥1000ms**: 显示为秒（如 "1.25s"）

## 故障排查

### 健康监控页面显示"暂无 Endpoint 数据"

**原因**: 没有配置任何 endpoint

**解决**:
1. 进入"配置管理"页面
2. 创建或编辑配置，添加 endpoints
3. 返回健康监控页面查看

### 健康状态始终显示"未知"

**原因**: 健康监控器未启用或 endpoint 未被测试

**解决**:
1. 点击"测试所有 Endpoint"按钮执行测试
2. 或等待代理服务器启动后自动更新状态

### API 返回 500 错误

**原因**: 配置管理器未初始化

**解决**:
1. 确保 Web 服务正确启动
2. 检查后端日志查看错误详情
3. 重启 Web 服务

## 最佳实践

### 定期健康检查
建议每 5-10 分钟手动测试一次所有 endpoint，确保服务质量

### 监控成功率
关注成功率低于 90% 的 endpoint，及时排查问题

### 关注响应时间
响应时间过高（>500ms）可能影响用户体验，考虑调整优先级或禁用

### 处理不健康的 Endpoint
1. 检查 endpoint URL 是否正确
2. 验证 API Key 是否有效
3. 确认网络连接正常
4. 必要时禁用或删除问题 endpoint

## API 文档

完整的 API 文档可通过以下方式访问：

- **Swagger UI**: `http://127.0.0.1:8080/api/docs`
- **ReDoc**: `http://127.0.0.1:8080/api/redoc`

## 反馈与支持

如遇到问题或有改进建议，请通过以下方式反馈：
- 项目 Issues: https://github.com/your-org/qcc/issues
- 文档: [健康监控实现文档](./health-monitoring-implementation.md)
