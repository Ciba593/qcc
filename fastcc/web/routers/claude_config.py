"""
Claude Code 配置管理 API
自动应用和还原 Claude Code 配置
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
import shutil
from datetime import datetime
from ..models import ApiResponse

router = APIRouter()


class ClaudeConfigManager:
    """Claude Code 配置管理器"""

    def __init__(self):
        self.claude_dir = Path.home() / ".claude"
        self.settings_file = self.claude_dir / "settings.json"
        self.backup_file = self.claude_dir / "settings.json.qcc_backup"
        self.proxy_info_file = self.claude_dir / "qcc_proxy_info.json"

    def get_current_config(self) -> dict:
        """获取当前 Claude Code 配置"""
        if not self.settings_file.exists():
            return {}

        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"读取配置失败: {str(e)}")

    def backup_config(self) -> bool:
        """备份当前配置"""
        if not self.settings_file.exists():
            # 如果配置文件不存在，创建一个空配置
            self.claude_dir.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=2)

        try:
            shutil.copy2(self.settings_file, self.backup_file)
            return True
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"备份配置失败: {str(e)}")

    def has_backup(self) -> bool:
        """检查是否有备份"""
        return self.backup_file.exists()

    def apply_proxy_config(self, proxy_url: str, api_key: str) -> dict:
        """应用代理配置到 Claude Code

        Args:
            proxy_url: 代理服务器 URL
            api_key: API 密钥

        Returns:
            应用后的配置
        """
        # 先备份
        self.backup_config()

        # 读取当前配置
        config = self.get_current_config()

        # 保存原始配置信息
        proxy_info = {
            "applied_at": datetime.now().isoformat(),
            "proxy_url": proxy_url,
            "original_base_url": config.get("env", {}).get("ANTHROPIC_BASE_URL"),
            "original_api_key": config.get("env", {}).get("ANTHROPIC_API_KEY"),
        }

        # 更新配置使用代理
        if "env" not in config:
            config["env"] = {}

        config["env"]["ANTHROPIC_BASE_URL"] = proxy_url
        config["env"]["ANTHROPIC_API_KEY"] = api_key
        config["env"]["ANTHROPIC_AUTH_TOKEN"] = api_key

        # 保存新配置
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)

            # 保存代理信息
            with open(self.proxy_info_file, 'w', encoding='utf-8') as f:
                json.dump(proxy_info, f, indent=2, ensure_ascii=False)

            return config
        except Exception as e:
            # 如果失败，恢复备份
            if self.backup_file.exists():
                shutil.copy2(self.backup_file, self.settings_file)
            raise HTTPException(status_code=500, detail=f"应用配置失败: {str(e)}")

    def restore_config(self) -> dict:
        """还原配置"""
        if not self.has_backup():
            raise HTTPException(status_code=404, detail="没有找到备份配置")

        try:
            # 恢复配置
            shutil.copy2(self.backup_file, self.settings_file)

            # 读取恢复后的配置
            config = self.get_current_config()

            # 删除备份和代理信息
            self.backup_file.unlink(missing_ok=True)
            self.proxy_info_file.unlink(missing_ok=True)

            return config
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"还原配置失败: {str(e)}")

    def get_proxy_info(self) -> dict:
        """获取代理应用信息"""
        if not self.proxy_info_file.exists():
            return None

        try:
            with open(self.proxy_info_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None

    def is_proxy_applied(self) -> bool:
        """检查是否已应用代理"""
        return self.proxy_info_file.exists() and self.backup_file.exists()


# 全局实例
claude_config_manager = ClaudeConfigManager()


@router.get("/status")
async def get_claude_config_status():
    """获取 Claude Code 配置状态

    Returns:
        当前配置状态信息
    """
    try:
        current_config = claude_config_manager.get_current_config()
        proxy_info = claude_config_manager.get_proxy_info()
        is_proxy_applied = claude_config_manager.is_proxy_applied()

        return ApiResponse(
            success=True,
            data={
                "is_proxy_applied": is_proxy_applied,
                "has_backup": claude_config_manager.has_backup(),
                "current_base_url": current_config.get("env", {}).get("ANTHROPIC_BASE_URL"),
                "proxy_info": proxy_info,
                "config_file": str(claude_config_manager.settings_file),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/apply")
async def apply_proxy_to_claude(proxy_url: str = None, api_key: str = None):
    """应用代理配置到 Claude Code

    Args:
        proxy_url: 代理服务器 URL，默认为 http://127.0.0.1:7860
        api_key: API 密钥，如果不提供则使用当前配置中的密钥

    Returns:
        应用结果
    """
    try:
        # 获取当前配置
        current_config = claude_config_manager.get_current_config()

        # 使用默认代理 URL
        if not proxy_url:
            proxy_url = "http://127.0.0.1:7860"

        # 如果没有提供 API 密钥，使用当前配置中的
        if not api_key:
            api_key = current_config.get("env", {}).get("ANTHROPIC_API_KEY")
            if not api_key:
                # 尝试从 apiKeyHelper 获取
                api_key_helper = current_config.get("apiKeyHelper")
                if api_key_helper:
                    import subprocess
                    try:
                        result = subprocess.run(
                            api_key_helper,
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        api_key = result.stdout.strip().strip("'\"")
                    except:
                        pass

            if not api_key:
                raise HTTPException(
                    status_code=400,
                    detail="无法获取 API 密钥，请在当前 Claude Code 配置中设置或手动提供"
                )

        # 检查是否已经应用过
        if claude_config_manager.is_proxy_applied():
            raise HTTPException(
                status_code=400,
                detail="代理配置已应用，请先还原再重新应用"
            )

        # 应用配置
        new_config = claude_config_manager.apply_proxy_config(proxy_url, api_key)

        return ApiResponse(
            success=True,
            message=f"成功应用代理配置到 Claude Code: {proxy_url}",
            data={
                "proxy_url": proxy_url,
                "config_file": str(claude_config_manager.settings_file),
                "backup_file": str(claude_config_manager.backup_file),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"应用代理配置失败: {str(e)}\n\n{traceback.format_exc()}"
        )


@router.post("/restore")
async def restore_claude_config():
    """还原 Claude Code 配置

    Returns:
        还原结果
    """
    try:
        if not claude_config_manager.is_proxy_applied():
            raise HTTPException(
                status_code=400,
                detail="没有应用过代理配置，无需还原"
            )

        # 还原配置
        restored_config = claude_config_manager.restore_config()

        return ApiResponse(
            success=True,
            message="成功还原 Claude Code 配置",
            data={
                "restored_base_url": restored_config.get("env", {}).get("ANTHROPIC_BASE_URL"),
                "config_file": str(claude_config_manager.settings_file),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"还原配置失败: {str(e)}\n\n{traceback.format_exc()}"
        )
