# 健康监控功能实现文档

## 概述

为 QCC Web UI 实现了完整的健康监控前后端功能，允许用户通过 Web 界面实时查看和管理所有 endpoint 的健康状态。

## 实现日期

2025-10-18

## 功能特性

### 1. 后端 API 实现

#### 健康状态 API (`GET /api/health/status`)

**功能**：
- 获取所有 endpoint 的健康状态统计和详细信息
- 实时反映每个 endpoint 的健康状况

**响应数据**：
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
    "endpoints": [
      {
        "endpoint_id": "36fb0ed6",
        "base_url": "https://api.anthropic.com",
        "status": "healthy",
        "enabled": true,
        "last_check": "2025-10-18T10:30:00",
        "consecutive_failures": 0,
        "success_rate": 98.5,
        "avg_response_time": 150.5,
        "total_requests": 100,
        "failed_requests": 2
      }
    ]
  }
}
```

#### 健康测试 API (`POST /api/health/test`)

**功能**：
- 执行健康检查测试（支持测试单个或所有 endpoint）
- 如果健康监控器已启用，使用对话测试方式进行深度检查

**请求参数**：
- `endpoint_id` (可选): 指定要测试的 endpoint ID

**响应示例**：
```json
{
  "success": true,
  "data": [
    {
      "endpoint_id": "36fb0ed6",
      "base_url": "https://api.anthropic.com",
      "status": "healthy",
      "response_time": 145.2,
      "last_check": "2025-10-18T10:35:00"
    }
  ],
  "message": "成功测试 8 个 endpoint"
}
```

#### 性能指标 API (`GET /api/health/metrics`)

**功能**：
- 获取 endpoint 的性能指标数据
- 支持查询单个或所有 endpoint 的指标

**请求参数**：
- `endpoint_id` (可选): 指定 endpoint ID

**响应示例**：
```json
{
  "success": true,
  "data": [
    {
      "endpoint_id": "36fb0ed6",
      "total_checks": 50,
      "success_count": 48,
      "failure_count": 2,
      "avg_response_time": 152.3,
      "min_response_time": 120.5,
      "max_response_time": 250.8
    }
  ]
}
```

### 2. 前端实现

#### 健康监控页面 (`/health`)

**组件位置**: `qcc-web/src/pages/Health.tsx`

**主要功能**：

1. **健康状态概览**
   - 显示健康、降级、不健康、未知状态的统计数字
   - 实时更新（每 10 秒刷新）
   - 使用不同颜色和图标区分状态

2. **Endpoint 详情表格**
   - 显示所有 endpoint 的详细健康信息
   - 包含：状态、ID、URL、成功率、响应时间、请求统计等
   - 支持单个 endpoint 测试
   - 成功率进度条可视化

3. **批量测试功能**
   - 一键测试所有 endpoint
   - 实时显示测试进度
   - 测试结果自动更新

**UI 特性**：
- 响应式设计，适配不同屏幕尺寸
- 状态图标和颜色编码（绿色=健康，黄色=降级，红色=不健康）
- 成功率进度条可视化
- 最后检查时间显示
- 连续失败次数警告标签

#### Dashboard 集成

**组件位置**: `qcc-web/src/pages/Dashboard.tsx`

**新增功能**：

1. **Endpoint 健康状况卡片**
   - 总体健康率统计（带进度条）
   - 各状态分类统计
   - "查看详情"按钮跳转到健康监控页面

2. **实时数据刷新**
   - 使用 React Query 自动刷新健康数据
   - 与其他 Dashboard 数据协同更新

#### 导航菜单

**位置**: `qcc-web/src/layouts/MainLayout.tsx`

**更新**：
- 添加"健康监控"菜单项（心形图标）
- 路由: `/health`

### 3. 依赖注入系统

**实现位置**: `fastcc/web/routers/health.py`

**设计模式**：
- 使用全局变量存储依赖实例
- 通过 `set_health_dependencies()` 函数初始化
- FastAPI Depends 机制注入到路由函数

**初始化**：
```python
# fastcc/web/app.py
@app.on_event("startup")
async def startup_event():
    config_manager = ConfigManager()
    health_monitor = HealthMonitor()  # 可选
    set_health_dependencies(config_manager, health_monitor)
```

## 技术架构

### 后端技术栈

- **框架**: FastAPI
- **异步处理**: asyncio
- **依赖注入**: FastAPI Depends
- **数据模型**: Pydantic

### 前端技术栈

- **框架**: React 18 + TypeScript
- **UI 库**: Ant Design 5
- **状态管理**: React Query (TanStack Query)
- **路由**: React Router v6
- **HTTP 客户端**: Axios

### 核心组件

1. **ConfigManager**: 配置管理
2. **Endpoint**: Endpoint 模型（包含健康状态）
3. **HealthMonitor**: 健康监控器（可选启用）
4. **Health Router**: FastAPI 健康监控路由

## 数据流

```
前端 Health 页面
    ↓ (HTTP GET)
后端 /api/health/status
    ↓
ConfigManager → 获取所有 endpoint
    ↓
收集健康状态数据
    ↓
返回统计和详情
    ↓ (JSON)
前端渲染展示
```

## 文件清单

### 后端文件

1. `fastcc/web/routers/health.py` - 健康监控 API 路由（重写）
2. `fastcc/web/app.py` - 添加启动事件和依赖初始化
3. `fastcc/web/models.py` - 已有 HealthStatusModel 定义
4. `fastcc/core/endpoint.py` - Endpoint 模型（已有健康状态）
5. `fastcc/proxy/health_monitor.py` - 健康监控器（已有）

### 前端文件

1. `qcc-web/src/pages/Health.tsx` - 健康监控页面（新建）
2. `qcc-web/src/pages/Dashboard.tsx` - Dashboard 集成（更新）
3. `qcc-web/src/App.tsx` - 路由配置（更新）
4. `qcc-web/src/layouts/MainLayout.tsx` - 导航菜单（已有健康监控）
5. `qcc-web/src/api/client.ts` - API 客户端（已有健康监控 API）

### 测试文件

1. `test_health_api.py` - 健康监控功能测试脚本

## 测试结果

### 后端测试

✅ ConfigManager 初始化成功
✅ Endpoint 健康状态更新正常
✅ 健康状态统计计算正确
✅ HealthMonitor 创建成功

**测试输出**：
```
============================================================
测试健康监控 API
============================================================

1. 初始化配置管理器...
   ✓ 配置管理器已初始化

2. 创建测试 endpoints...
   ✓ Endpoint: 36fb0ed6 - https://api.anthropic.com
   ✓ Endpoint: e172c7bf - https://api.openai-proxy.com

3. 模拟更新 endpoint 健康状态...
   ✓ 健康状态已更新

4. 检查 endpoint 健康状态...
   Endpoint 36fb0ed6:
     - 状态: healthy
     - 平均响应时间: 150.50ms
     - 成功率: 100.00%
     - 是否健康: True

   Endpoint e172c7bf:
     - 状态: degraded
     - 平均响应时间: 300.20ms
     - 成功率: 100.00%
     - 是否健康: False

5. 统计健康状况...
   健康: 1
   降级: 1
   不健康: 0
   未知: 0
   总计: 2

6. 测试健康监控器...
   ✓ 健康监控器已创建
   - 检查间隔: 60秒
   - 动态权重调整: False

============================================================
✅ 测试完成
============================================================
```

## 使用说明

### 启动 Web UI

```bash
# 方式 1: 使用 CLI
uvx --from . qcc web start

# 方式 2: 直接运行
python3 -m fastcc.cli web start
```

### 访问健康监控

1. 打开浏览器访问: `http://127.0.0.1:8080`
2. 点击左侧菜单的"健康监控"
3. 查看所有 endpoint 的健康状态
4. 点击"测试所有 Endpoint"执行健康检查

### API 访问

```bash
# 获取健康状态
curl http://127.0.0.1:8080/api/health/status

# 执行健康测试
curl -X POST http://127.0.0.1:8080/api/health/test

# 获取性能指标
curl http://127.0.0.1:8080/api/health/metrics
```

## 未来改进

1. **历史记录功能**
   - 实现健康检查历史记录存储
   - 提供历史趋势图表

2. **性能图表**
   - 响应时间趋势图
   - 成功率变化曲线
   - 实时监控图表

3. **告警功能**
   - 健康状态变化通知
   - 邮件/WebSocket 告警

4. **高级筛选**
   - 按状态筛选 endpoint
   - 按响应时间排序
   - 搜索功能

## 相关文档

- [Endpoint 模型文档](../../../fastcc/core/endpoint.py)
- [健康监控器文档](../../../fastcc/proxy/health_monitor.py)
- [Web API 文档](../../../fastcc/web/app.py)
- [前端架构文档](../../../qcc-web/README.md)

## 贡献者

- Claude (AI Assistant)
- 实现日期: 2025-10-18

## 版本历史

### v1.0.0 (2025-10-18)
- ✅ 实现健康状态 API
- ✅ 实现健康测试 API
- ✅ 实现性能指标 API
- ✅ 创建健康监控页面
- ✅ Dashboard 集成
- ✅ 完成测试验证
