"""
Web 工具函数
"""

from typing import Any, List, Dict, Union


def to_dict(obj: Any) -> Union[Dict, Any]:
    """
    将对象转换为字典
    如果对象有 to_dict 方法，则调用它
    否则返回原对象
    """
    if obj is None:
        return None
    if hasattr(obj, 'to_dict'):
        return obj.to_dict()
    return obj


def to_dict_list(obj_list: List[Any]) -> List[Dict]:
    """
    将对象列表转换为字典列表
    """
    return [to_dict(obj) for obj in obj_list]
