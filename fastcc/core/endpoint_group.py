"""EndpointGroup - 高可用代理组模型

EndpointGroup 是一个配置组织单元，用于将多个配置打包成主节点和副节点。
负载均衡和故障切换由现有的 LoadBalancer 和 PriorityManager 处理。

设计理念：
- EndpointGroup 选择 n 个主节点配置 + m 个副节点配置
- 主节点：优先使用的配置列表
- 副节点：主节点全部故障时使用的配置列表
- 实际的负载均衡和故障切换由外部组件管理
"""

import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional


class EndpointGroup:
    """高可用代理组

    一个 EndpointGroup 包含：
    - 基本信息（名称、描述）
    - 主节点配置列表（从已有 config 中选择 n 个）
    - 副节点配置列表（从已有 config 中选择 m 个）
    - 负载均衡和故障切换由外部的 LoadBalancer 和 PriorityManager 处理
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        primary_configs: Optional[List[str]] = None,
        secondary_configs: Optional[List[str]] = None,
        enabled: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """初始化 EndpointGroup

        Args:
            name: 代理组名称（唯一标识）
            description: 描述信息
            primary_configs: 主节点配置名称列表
            secondary_configs: 副节点配置名称列表
            enabled: 是否启用
            metadata: 额外的元数据
        """
        self.id = self._generate_id(name)
        self.name = name
        self.description = description
        self.primary_configs = primary_configs or []
        self.secondary_configs = secondary_configs or []
        self.enabled = enabled
        self.metadata = metadata or {}

        # 时间戳
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

    @staticmethod
    def _generate_id(name: str) -> str:
        """基于名称生成稳定的 ID

        Args:
            name: 代理组名称

        Returns:
            8 字符的稳定 ID
        """
        hash_value = hashlib.sha256(name.encode('utf-8')).hexdigest()
        return hash_value[:8]

    def add_primary_config(self, config_name: str) -> bool:
        """添加主节点配置

        Args:
            config_name: 配置名称

        Returns:
            是否添加成功
        """
        if config_name not in self.primary_configs:
            self.primary_configs.append(config_name)
            self.updated_at = datetime.now().isoformat()
            return True
        return False

    def remove_primary_config(self, config_name: str) -> bool:
        """移除主节点配置

        Args:
            config_name: 配置名称

        Returns:
            是否移除成功
        """
        if config_name in self.primary_configs:
            self.primary_configs.remove(config_name)
            self.updated_at = datetime.now().isoformat()
            return True
        return False

    def add_secondary_config(self, config_name: str) -> bool:
        """添加副节点配置

        Args:
            config_name: 配置名称

        Returns:
            是否添加成功
        """
        if config_name not in self.secondary_configs:
            self.secondary_configs.append(config_name)
            self.updated_at = datetime.now().isoformat()
            return True
        return False

    def remove_secondary_config(self, config_name: str) -> bool:
        """移除副节点配置

        Args:
            config_name: 配置名称

        Returns:
            是否移除成功
        """
        if config_name in self.secondary_configs:
            self.secondary_configs.remove(config_name)
            self.updated_at = datetime.now().isoformat()
            return True
        return False

    def get_all_configs(self) -> List[str]:
        """获取所有配置（主节点 + 副节点）

        Returns:
            所有配置名称列表
        """
        return self.primary_configs + self.secondary_configs

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）

        Returns:
            包含所有信息的字典
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'primary_configs': self.primary_configs,
            'secondary_configs': self.secondary_configs,
            'enabled': self.enabled,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EndpointGroup':
        """从字典创建 EndpointGroup（用于反序列化）

        Args:
            data: 包含配置信息的字典

        Returns:
            EndpointGroup 实例
        """
        group = cls(
            name=data['name'],
            description=data.get('description', ''),
            primary_configs=data.get('primary_configs', []),
            secondary_configs=data.get('secondary_configs', []),
            enabled=data.get('enabled', True),
            metadata=data.get('metadata', {})
        )

        # 恢复时间戳
        group.id = data.get('id', group.id)
        group.created_at = data.get('created_at', group.created_at)
        group.updated_at = data.get('updated_at', group.updated_at)

        return group

    def display_info(self) -> str:
        """生成显示信息

        Returns:
            格式化的信息字符串
        """
        enabled_icon = '✓' if self.enabled else '✗'

        info = [
            f"名称: {self.name}",
            f"ID: {self.id}",
            f"主节点: {len(self.primary_configs)}个",
            f"副节点: {len(self.secondary_configs)}个",
            f"启用: {enabled_icon}"
        ]

        return " | ".join(info)

    def __repr__(self) -> str:
        """字符串表示"""
        return f"EndpointGroup({self.name}, primary={len(self.primary_configs)}, secondary={len(self.secondary_configs)})"

    def __eq__(self, other) -> bool:
        """相等性比较（基于名称）"""
        if not isinstance(other, EndpointGroup):
            return False
        return self.name == other.name

    def __hash__(self) -> int:
        """哈希值（用于去重）"""
        return hash(self.name)
