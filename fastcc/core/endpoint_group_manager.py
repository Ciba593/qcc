"""EndpointGroup 管理器

管理所有 EndpointGroup 的 CRUD 操作和持久化存储。
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .endpoint_group import EndpointGroup
from .config import ConfigManager


class EndpointGroupManager:
    """EndpointGroup 管理器

    负责管理所有高可用代理组的生命周期：
    - 创建、读取、更新、删除 EndpointGroup
    - 持久化存储到本地缓存
    - 支持云端同步（通过 ConfigManager）
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """初始化 EndpointGroupManager

        Args:
            config_manager: ConfigManager 实例（用于验证配置是否存在）
        """
        self.config_manager = config_manager or ConfigManager()
        self.groups: Dict[str, EndpointGroup] = {}

        # 加载本地缓存
        self._load_local_cache()

    def _get_cache_file(self) -> Path:
        """获取缓存文件路径

        Returns:
            缓存文件路径
        """
        cache_dir = Path.home() / ".fastcc"
        cache_dir.mkdir(exist_ok=True)
        return cache_dir / "endpoint_groups.json"

    def _load_local_cache(self):
        """从本地缓存加载 EndpointGroup"""
        cache_file = self._get_cache_file()

        if not cache_file.exists():
            return

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 加载 groups
            groups_data = data.get('groups', {})
            for name, group_data in groups_data.items():
                self.groups[name] = EndpointGroup.from_dict(group_data)

            print(f"[i] 已加载 {len(self.groups)} 个 EndpointGroup")

        except (json.JSONDecodeError, IOError) as e:
            print(f"[!] 加载 EndpointGroup 缓存失败: {e}")

    def _save_local_cache(self):
        """保存 EndpointGroup 到本地缓存"""
        cache_file = self._get_cache_file()

        data = {
            'version': '1.0',
            'last_updated': datetime.now().isoformat(),
            'groups': {
                name: group.to_dict()
                for name, group in self.groups.items()
            }
        }

        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # 设置文件权限
            cache_file.chmod(0o600)

        except IOError as e:
            print(f"[X] 保存 EndpointGroup 缓存失败: {e}")

    def sync_to_cloud(self) -> bool:
        """同步 EndpointGroup 到云端

        将 EndpointGroup 数据整合到 ConfigManager 的存储中

        Returns:
            是否同步成功
        """
        if not self.config_manager.storage_backend:
            # 本地存储模式，无需云端同步
            return True

        try:
            # 将 EndpointGroup 数据添加到 ConfigManager 的缓存中
            # 这样会在 ConfigManager.sync_to_cloud() 时一起同步
            endpoint_groups_data = {
                name: group.to_dict()
                for name, group in self.groups.items()
            }

            # 保存到本地缓存
            self._save_local_cache()

            # 通过 ConfigManager 同步到云端
            # 我们需要将 endpoint_groups 数据加入到 ConfigManager 的同步中
            return self.config_manager.sync_to_cloud()

        except Exception as e:
            print(f"[X] 同步 EndpointGroup 到云端失败: {e}")
            return False

    def sync_from_cloud(self) -> bool:
        """从云端同步 EndpointGroup

        从 ConfigManager 的云端存储中加载 EndpointGroup 数据

        Returns:
            是否同步成功
        """
        if not self.config_manager.storage_backend:
            # 本地存储模式，直接返回
            return True

        try:
            # 先同步 ConfigManager
            self.config_manager.sync_from_cloud()

            # 从本地缓存加载（ConfigManager 已经从云端更新了本地缓存）
            self._load_local_cache()

            return True

        except Exception as e:
            print(f"[X] 从云端同步 EndpointGroup 失败: {e}")
            return False

    def create_group(
        self,
        name: str,
        description: str = "",
        primary_configs: Optional[List[str]] = None,
        secondary_configs: Optional[List[str]] = None,
        **kwargs
    ) -> Optional[EndpointGroup]:
        """创建新的 EndpointGroup

        Args:
            name: 代理组名称
            description: 描述
            primary_configs: 主节点配置列表
            secondary_configs: 副节点配置列表
            **kwargs: 其他参数

        Returns:
            创建的 EndpointGroup，如果失败则返回 None
        """
        # 检查是否已存在
        if name in self.groups:
            print(f"[X] EndpointGroup '{name}' 已存在")
            return None

        # 验证配置是否存在
        all_configs = (primary_configs or []) + (secondary_configs or [])
        for config_name in all_configs:
            if not self.config_manager.has_profile(config_name):
                print(f"[X] 配置 '{config_name}' 不存在")
                return None

        # 创建 EndpointGroup
        group = EndpointGroup(
            name=name,
            description=description,
            primary_configs=primary_configs,
            secondary_configs=secondary_configs,
            **kwargs
        )

        self.groups[name] = group

        # 保存到缓存
        self._save_local_cache()

        # 同步到云端
        if self.config_manager.settings.get('auto_sync', True):
            self.sync_to_cloud()

        print(f"[OK] 已创建 EndpointGroup: {name}")
        return group

    def get_group(self, name: str) -> Optional[EndpointGroup]:
        """获取指定的 EndpointGroup

        Args:
            name: 代理组名称

        Returns:
            EndpointGroup 实例，如果不存在则返回 None
        """
        return self.groups.get(name)

    def list_groups(self) -> List[EndpointGroup]:
        """列出所有 EndpointGroup

        Returns:
            所有 EndpointGroup 的列表
        """
        return list(self.groups.values())

    def update_group(
        self,
        name: str,
        description: Optional[str] = None,
        primary_configs: Optional[List[str]] = None,
        secondary_configs: Optional[List[str]] = None,
        **kwargs
    ) -> bool:
        """更新 EndpointGroup

        Args:
            name: 代理组名称
            description: 新的描述
            primary_configs: 新的主节点配置列表
            secondary_configs: 新的副节点配置列表
            **kwargs: 其他要更新的属性

        Returns:
            是否更新成功
        """
        group = self.get_group(name)
        if not group:
            print(f"[X] EndpointGroup '{name}' 不存在")
            return False

        # 更新属性
        if description is not None:
            group.description = description

        if primary_configs is not None:
            # 验证配置是否存在
            for config_name in primary_configs:
                if not self.config_manager.has_profile(config_name):
                    print(f"[X] 配置 '{config_name}' 不存在")
                    return False
            group.primary_configs = primary_configs

        if secondary_configs is not None:
            # 验证配置是否存在
            for config_name in secondary_configs:
                if not self.config_manager.has_profile(config_name):
                    print(f"[X] 配置 '{config_name}' 不存在")
                    return False
            group.secondary_configs = secondary_configs

        # 更新其他属性
        for key, value in kwargs.items():
            if hasattr(group, key):
                setattr(group, key, value)

        # 更新时间戳
        group.updated_at = datetime.now().isoformat()

        # 保存到缓存
        self._save_local_cache()

        # 同步到云端
        if self.config_manager.settings.get('auto_sync', True):
            self.sync_to_cloud()

        print(f"[OK] 已更新 EndpointGroup: {name}")
        return True

    def delete_group(self, name: str) -> bool:
        """删除 EndpointGroup

        Args:
            name: 代理组名称

        Returns:
            是否删除成功
        """
        if name not in self.groups:
            print(f"[X] EndpointGroup '{name}' 不存在")
            return False

        del self.groups[name]

        # 保存到缓存
        self._save_local_cache()

        # 同步到云端
        if self.config_manager.settings.get('auto_sync', True):
            self.sync_to_cloud()

        print(f"[OK] 已删除 EndpointGroup: {name}")
        return True

    def add_primary_config(self, group_name: str, config_name: str) -> bool:
        """为 EndpointGroup 添加主节点配置

        Args:
            group_name: 代理组名称
            config_name: 配置名称

        Returns:
            是否添加成功
        """
        group = self.get_group(group_name)
        if not group:
            print(f"[X] EndpointGroup '{group_name}' 不存在")
            return False

        # 验证配置是否存在
        if not self.config_manager.has_profile(config_name):
            print(f"[X] 配置 '{config_name}' 不存在")
            return False

        # 添加配置
        if group.add_primary_config(config_name):
            self._save_local_cache()
            # 同步到云端
            if self.config_manager.settings.get('auto_sync', True):
                self.sync_to_cloud()
            print(f"[OK] 已为 '{group_name}' 添加主节点: {config_name}")
            return True
        else:
            print(f"[i] 配置 '{config_name}' 已在主节点列表中")
            return False

    def remove_primary_config(self, group_name: str, config_name: str) -> bool:
        """从 EndpointGroup 移除主节点配置

        Args:
            group_name: 代理组名称
            config_name: 配置名称

        Returns:
            是否移除成功
        """
        group = self.get_group(group_name)
        if not group:
            print(f"[X] EndpointGroup '{group_name}' 不存在")
            return False

        if group.remove_primary_config(config_name):
            self._save_local_cache()
            # 同步到云端
            if self.config_manager.settings.get('auto_sync', True):
                self.sync_to_cloud()
            print(f"[OK] 已从 '{group_name}' 移除主节点: {config_name}")
            return True
        else:
            print(f"[i] 配置 '{config_name}' 不在主节点列表中")
            return False

    def add_secondary_config(self, group_name: str, config_name: str) -> bool:
        """为 EndpointGroup 添加副节点配置

        Args:
            group_name: 代理组名称
            config_name: 配置名称

        Returns:
            是否添加成功
        """
        group = self.get_group(group_name)
        if not group:
            print(f"[X] EndpointGroup '{group_name}' 不存在")
            return False

        # 验证配置是否存在
        if not self.config_manager.has_profile(config_name):
            print(f"[X] 配置 '{config_name}' 不存在")
            return False

        # 添加配置
        if group.add_secondary_config(config_name):
            self._save_local_cache()
            # 同步到云端
            if self.config_manager.settings.get('auto_sync', True):
                self.sync_to_cloud()
            print(f"[OK] 已为 '{group_name}' 添加副节点: {config_name}")
            return True
        else:
            print(f"[i] 配置 '{config_name}' 已在副节点列表中")
            return False

    def remove_secondary_config(self, group_name: str, config_name: str) -> bool:
        """从 EndpointGroup 移除副节点配置

        Args:
            group_name: 代理组名称
            config_name: 配置名称

        Returns:
            是否移除成功
        """
        group = self.get_group(group_name)
        if not group:
            print(f"[X] EndpointGroup '{group_name}' 不存在")
            return False

        if group.remove_secondary_config(config_name):
            self._save_local_cache()
            # 同步到云端
            if self.config_manager.settings.get('auto_sync', True):
                self.sync_to_cloud()
            print(f"[OK] 已从 '{group_name}' 移除副节点: {config_name}")
            return True
        else:
            print(f"[i] 配置 '{config_name}' 不在副节点列表中")
            return False

    def has_group(self, name: str) -> bool:
        """检查 EndpointGroup 是否存在

        Args:
            name: 代理组名称

        Returns:
            是否存在
        """
        return name in self.groups
