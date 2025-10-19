"""
QCC Web API 主应用
FastAPI 应用,提供 REST API 和 WebSocket 支持
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path

from .routers import configs, endpoints, priority, health, proxy, queue, dashboard, claude_config, system
from .routers.health import set_health_dependencies
from fastcc.core.config import ConfigManager
from fastcc.proxy.health_monitor import HealthMonitor

# 创建 FastAPI 应用
app = FastAPI(
    title="QCC Web API",
    description="Quick Claude Config Web Interface API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 应用启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化依赖"""
    # 初始化配置管理器
    config_manager = ConfigManager()

    # 初始化健康监控器（可选，默认不启用）
    health_monitor = None
    # health_monitor = HealthMonitor()  # 如果需要启用健康监控，取消注释

    # 设置健康监控依赖
    set_health_dependencies(config_manager, health_monitor)

    # 设置系统配置管理器
    from .routers import system as system_router
    system_router.set_config_manager(config_manager)

# 注册 API 路由
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(configs.router, prefix="/api/configs", tags=["Configs"])
app.include_router(endpoints.router, prefix="/api/endpoints", tags=["Endpoints"])
app.include_router(priority.router, prefix="/api/priority", tags=["Priority"])
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(proxy.router, prefix="/api/proxy", tags=["Proxy"])
app.include_router(queue.router, prefix="/api/queue", tags=["Queue"])
app.include_router(claude_config.router, prefix="/api/claude-config", tags=["Claude Config"])
app.include_router(system.router, prefix="/api/system", tags=["System"])

# 静态文件服务 (前端构建文件)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

    @app.get("/")
    async def serve_spa():
        """服务前端 SPA 应用"""
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "QCC Web API is running. Frontend not built yet."}

    # 使用 exception handler 处理 404，返回 SPA 页面
    from fastapi import Request, status
    from fastapi.responses import JSONResponse
    from fastapi.exceptions import HTTPException

    @app.exception_handler(404)
    async def custom_404_handler(request: Request, exc: HTTPException):
        """处理 404 错误：API 返回 JSON，前端路由返回 SPA"""
        # API 路径返回 JSON 错误
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=404,
                content={"detail": "Not found"}
            )

        # 前端路由返回 index.html
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return JSONResponse(
            status_code=404,
            content={"error": "Not found"}
        )
else:
    @app.get("/")
    async def root():
        return {
            "message": "QCC Web API",
            "version": "1.0.0",
            "docs": "/api/docs"
        }


@app.get("/api/health-check")
async def health_check():
    """健康检查端点"""
    return {"status": "ok", "service": "qcc-web-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)
