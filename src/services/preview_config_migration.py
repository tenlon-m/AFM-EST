#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预览配置迁移器模块
处理预览配置文件版本迁移和向后兼容
"""

from typing import Dict, Any
from models.preview_config import PreviewConfigFile, HandlerConfig, DefaultPreviewConfig
from core.logger import logger


class PreviewConfigMigration:
    """预览配置迁移器"""
    
    CURRENT_VERSION = "1.0"
    
    @staticmethod
    def migrate(config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        配置迁移入口
        
        Args:
            config_data: 原始配置数据
            
        Returns:
            Dict[str, Any]: 迁移后的配置数据
        """
        if not config_data:
            # 配置为空，返回默认配置
            logger.info("预览配置为空，使用默认配置")
            return DefaultPreviewConfig.get_default_config().to_dict()
        
        # 获取版本号
        version = config_data.get("version", "0.0")
        
        # 根据版本号选择迁移策略
        if version == "0.0":
            logger.info("检测到无版本号预览配置，执行迁移: 0.0 -> 1.0")
            return PreviewConfigMigration._migrate_0_0_to_1_0(config_data)
        elif version == "1.0":
            logger.info("预览配置版本已是最新: 1.0")
            return PreviewConfigMigration._ensure_complete_1_0(config_data)
        else:
            logger.warning(f"未知预览配置版本: {version}，尝试迁移到最新版本")
            return PreviewConfigMigration._ensure_complete_1_0(config_data)
    
    @staticmethod
    def _migrate_0_0_to_1_0(config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从无版本号迁移到1.0
        
        Args:
            config_data: 原始配置数据
            
        Returns:
            Dict[str, Any]: 迁移后的配置数据
        """
        migrated_data = {
            "version": "1.0",
            "handlers": []
        }
        
        # 检查是否有handlers字段
        if "handlers" in config_data:
            # 已有handlers，补全缺失字段
            for handler_data in config_data["handlers"]:
                migrated_handler = {
                    "name": handler_data.get("name", "UnknownHandler"),
                    "enabled": handler_data.get("enabled", True),
                    "priority": handler_data.get("priority", 50),
                    "extensions": handler_data.get("extensions", [])
                }
                migrated_data["handlers"].append(migrated_handler)
        else:
            # 没有handlers，使用默认配置
            default_config = DefaultPreviewConfig.get_default_config()
            migrated_data["handlers"] = [h.to_dict() for h in default_config.handlers]
        
        logger.info(f"预览配置迁移完成: 0.0 -> 1.0，处理器数量: {len(migrated_data['handlers'])}")
        return migrated_data
    
    @staticmethod
    def _ensure_complete_1_0(config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        确保1.0版本配置完整
        
        Args:
            config_data: 配置数据
            
        Returns:
            Dict[str, Any]: 完整的配置数据
        """
        # 确保version字段存在
        if "version" not in config_data:
            config_data["version"] = "1.0"
        
        # 确保handlers字段存在
        if "handlers" not in config_data:
            default_config = DefaultPreviewConfig.get_default_config()
            config_data["handlers"] = [h.to_dict() for h in default_config.handlers]
            logger.info("预览配置缺少handlers字段，已补全默认配置")
            return config_data
        
        # 获取默认处理器名称列表
        default_handlers = {h.name: h for h in DefaultPreviewConfig.get_default_handlers()}
        
        # 补全缺失的处理器
        existing_handler_names = {h.get("name") for h in config_data["handlers"]}
        missing_handlers = []
        
        for handler_name, default_handler in default_handlers.items():
            if handler_name not in existing_handler_names:
                missing_handlers.append(default_handler.to_dict())
                logger.info(f"补全缺失的预览处理器: {handler_name}")
        
        if missing_handlers:
            config_data["handlers"].extend(missing_handlers)
        
        # 补全每个处理器的缺失字段
        for handler_data in config_data["handlers"]:
            handler_name = handler_data.get("name", "UnknownHandler")
            
            # 如果是默认处理器，补全缺失字段
            if handler_name in default_handlers:
                default_handler = default_handlers[handler_name]
                
                if "enabled" not in handler_data:
                    handler_data["enabled"] = default_handler.enabled
                
                if "priority" not in handler_data:
                    handler_data["priority"] = default_handler.priority
                
                if "extensions" not in handler_data:
                    handler_data["extensions"] = default_handler.extensions.copy()
        
        logger.info(f"预览配置完整性检查完成，处理器数量: {len(config_data['handlers'])}")
        return config_data
    
    @staticmethod
    def get_migration_info(config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取迁移信息
        
        Args:
            config_data: 配置数据
            
        Returns:
            Dict[str, Any]: 迁移信息
        """
        if not config_data:
            return {
                "needs_migration": True,
                "from_version": "none",
                "to_version": PreviewConfigMigration.CURRENT_VERSION,
                "reason": "配置为空"
            }
        
        version = config_data.get("version", "0.0")
        
        if version != PreviewConfigMigration.CURRENT_VERSION:
            return {
                "needs_migration": True,
                "from_version": version,
                "to_version": PreviewConfigMigration.CURRENT_VERSION,
                "reason": "版本不匹配"
            }
        
        # 检查是否需要补全
        default_handlers = {h.name for h in DefaultPreviewConfig.get_default_handlers()}
        existing_handlers = {h.get("name") for h in config_data.get("handlers", [])}
        missing_handlers = default_handlers - existing_handlers
        
        if missing_handlers:
            return {
                "needs_migration": True,
                "from_version": version,
                "to_version": PreviewConfigMigration.CURRENT_VERSION,
                "reason": f"缺少处理器: {', '.join(missing_handlers)}"
            }
        
        return {
            "needs_migration": False,
            "from_version": version,
            "to_version": PreviewConfigMigration.CURRENT_VERSION,
            "reason": "配置已是最新"
        }