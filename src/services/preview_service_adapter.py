#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预览服务适配器
将配置动态应用到预览服务
"""

from typing import Dict, Optional, List
from services.preview_config_manager import preview_config_manager
from core.logger import logger


class PreviewServiceAdapter:
    """
    预览服务适配器
    负责将配置管理器与预览服务连接
    """
    
    def __init__(self, preview_service):
        """
        初始化适配器
        
        Args:
            preview_service: 预览服务实例
        """
        self._preview_service = preview_service
        self._handler_map: Dict[str, any] = {}
        
        # 初始化处理器映射
        self._build_handler_map()
        
        # 注册配置变更监听器
        preview_config_manager.add_config_listener(self._on_config_changed)
    
    def _build_handler_map(self) -> None:
        """构建处理器映射表"""
        self._handler_map.clear()
        
        # 获取配置中的处理器列表
        handlers = preview_config_manager.get_handlers()
        
        # 按优先级排序（优先级越小越优先）
        sorted_handlers = sorted(handlers, key=lambda h: h.priority)
        
        # 构建映射表
        for handler_config in sorted_handlers:
            if not handler_config.enabled:
                continue
            
            handler_name = handler_config.name
            
            # 在预览服务中查找对应的处理器实例
            for handler in self._preview_service.handlers:
                if handler.__class__.__name__ == handler_name:
                    # 设置处理器的扩展名列表
                    if hasattr(handler, 'set_extensions'):
                        handler.set_extensions(handler_config.extensions)
                    
                    # 记录映射关系
                    for ext in handler_config.extensions:
                        ext_lower = ext.lower()
                        if ext_lower not in self._handler_map:
                            self._handler_map[ext_lower] = handler
                    
                    break
        
        logger.info(f"预览处理器映射表构建完成，扩展名数量: {len(self._handler_map)}")
    
    def _on_config_changed(self, config) -> None:
        """
        配置变更回调
        
        Args:
            config: 新的配置
        """
        logger.info("检测到预览配置变更，重新加载处理器映射")
        self._build_handler_map()
    
    def get_handler_for_extension(self, extension: str) -> Optional[any]:
        """
        根据扩展名获取处理器
        
        Args:
            extension: 文件扩展名
            
        Returns:
            处理器实例，不存在则返回None
        """
        ext_lower = extension.lower()
        return self._handler_map.get(ext_lower)
    
    def reload_handlers(self) -> None:
        """重新加载处理器映射"""
        self._build_handler_map()
        logger.info("预览处理器映射已重新加载")
    
    def get_handler_map(self) -> Dict[str, any]:
        """获取处理器映射表"""
        return self._handler_map.copy()
    
    def get_supported_extensions(self) -> List[str]:
        """获取所有支持的扩展名"""
        return list(self._handler_map.keys())
    
    def is_extension_supported(self, extension: str) -> bool:
        """
        检查扩展名是否支持
        
        Args:
            extension: 文件扩展名
            
        Returns:
            bool: 是否支持
        """
        return extension.lower() in self._handler_map