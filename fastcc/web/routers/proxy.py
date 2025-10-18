"""
代理服务 API 路由
对应 CLI: proxy start/stop/status/use/logs
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..models import ApiResponse, ProxyStatusModel
import os
import psutil
from datetime import datetime

router = APIRouter()


class StartProxyRequest(BaseModel):
    host: str = "127.0.0.1"
    port: int = 7860
    cluster: str  # 必需参数,指定要使用的 EndpointGroup


@router.get("/status")
async def get_proxy_status():
    """获取代理状态 - 对应 CLI: qcc proxy status"""
    try:
        pid_file = os.path.expanduser("~/.fastcc/proxy.pid")

        if not os.path.exists(pid_file):
            return ApiResponse(
                success=True,
                data={
                    "running": False,
                    "pid": None,
                    "host": None,
                    "port": None,
                    "uptime": None
                }
            )

        with open(pid_file, 'r') as f:
            content = f.read().strip()

            # 尝试解析 JSON 格式 (新格式)
            try:
                import json
                pid_data = json.loads(content)
                pid = pid_data['pid']
                host = pid_data.get('host', '127.0.0.1')
                port = pid_data.get('port', 7860)
                config = None
            except (json.JSONDecodeError, KeyError):
                # 回退到旧格式
                if ':' in content:
                    pid_str, config = content.split(':', 1)
                    pid = int(pid_str)
                else:
                    pid = int(content)
                    config = None
                host = "127.0.0.1"
                port = 7860

        # 检查进程是否存在
        if psutil.pid_exists(pid):
            try:
                process = psutil.Process(pid)
                create_time = process.create_time()
                uptime = int(datetime.now().timestamp() - create_time)

                return ApiResponse(
                    success=True,
                    data={
                        "running": True,
                        "pid": pid,
                        "host": host,
                        "port": port,
                        "uptime": uptime,
                        "config": config
                    }
                )
            except:
                pass

        # 进程不存在,清理 PID 文件
        os.remove(pid_file)
        return ApiResponse(
            success=True,
            data={
                "running": False,
                "pid": None,
                "host": None,
                "port": None,
                "uptime": None
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_proxy(request: StartProxyRequest):
    """启动代理服务 - 对应 CLI: qcc proxy start"""
    try:
        import subprocess
        import sys
        from pathlib import Path

        # 检查是否已经在运行
        pid_file = os.path.expanduser("~/.fastcc/proxy.pid")
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                content = f.read().strip()
                if ':' in content:
                    pid_str = content.split(':', 1)[0]
                else:
                    pid_str = content
                pid = int(pid_str)

            if psutil.pid_exists(pid):
                return ApiResponse(
                    success=False,
                    message="代理服务已在运行"
                )

        # 构建启动命令
        cmd = [
            sys.executable, "-m", "fastcc.cli",
            "proxy", "start",
            "--host", request.host,
            "--port", str(request.port),
            "--cluster", request.cluster
        ]

        # 确保日志目录存在
        log_dir = Path.home() / ".fastcc"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "proxy_web.log"

        # 在后台启动代理服务
        with open(log_file, 'w') as f:
            process = subprocess.Popen(
                cmd,
                stdout=f,
                stderr=subprocess.STDOUT,
                start_new_session=True  # 使进程在后台独立运行
            )

        # 等待一小段时间确保启动成功
        import asyncio
        await asyncio.sleep(1)

        # 验证是否启动成功
        if os.path.exists(pid_file):
            return ApiResponse(
                success=True,
                message=f"代理服务已启动 (PID: {process.pid})",
                data={
                    "pid": process.pid,
                    "host": request.host,
                    "port": request.port,
                    "cluster": request.cluster
                }
            )
        else:
            return ApiResponse(
                success=False,
                message="代理服务启动失败，请查看日志文件"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_proxy():
    """停止代理服务 - 对应 CLI: qcc proxy stop"""
    try:
        import json
        pid_file = os.path.expanduser("~/.fastcc/proxy.pid")

        if not os.path.exists(pid_file):
            return ApiResponse(
                success=False,
                message="代理服务未运行"
            )

        with open(pid_file, 'r') as f:
            content = f.read().strip()

            # 尝试解析 JSON 格式 (新格式)
            try:
                pid_data = json.loads(content)
                pid = pid_data['pid']
            except (json.JSONDecodeError, KeyError):
                # 回退到旧格式
                pid = int(content.split(':')[0]) if ':' in content else int(content)

        if psutil.pid_exists(pid):
            process = psutil.Process(pid)
            process.terminate()
            process.wait(timeout=5)

        os.remove(pid_file)

        return ApiResponse(
            success=True,
            message="代理服务已停止"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs")
async def get_proxy_logs(
    lines: int = 100,
    level: str = "ALL",
    grep: str = ""
):
    """获取代理日志 - 对应 CLI: qcc proxy logs

    Args:
        lines: 返回最后 N 行（默认 100）
        level: 过滤日志级别（DEBUG, INFO, WARNING, ERROR, ALL，默认 ALL）
        grep: 搜索关键词（默认空）

    Returns:
        日志内容
    """
    try:
        import os
        from pathlib import Path

        log_file = Path.home() / '.fastcc' / 'proxy.log'

        if not log_file.exists():
            return ApiResponse(
                success=True,
                data={
                    'logs': [],
                    'total_lines': 0,
                    'displayed_lines': 0,
                    'log_file': str(log_file),
                    'message': '日志文件不存在'
                }
            )

        # 读取日志文件
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            all_lines = f.readlines()

        # 过滤日志
        filtered_lines = []
        for line in all_lines:
            if not line.strip():
                continue

            # 级别过滤
            if level != 'ALL':
                if f" - {level} - " not in line:
                    continue

            # 关键词过滤
            if grep and grep.lower() not in line.lower():
                continue

            filtered_lines.append(line.rstrip())

        # 返回最后 N 行
        display_lines = filtered_lines[-lines:] if len(filtered_lines) > lines else filtered_lines

        return ApiResponse(
            success=True,
            data={
                'logs': display_lines,
                'total_lines': len(filtered_lines),
                'displayed_lines': len(display_lines),
                'log_file': str(log_file),
                'filters': {
                    'lines': lines,
                    'level': level,
                    'grep': grep
                }
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取日志失败: {str(e)}")
