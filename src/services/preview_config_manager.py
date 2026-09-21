#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预览配置管理器
管理预览处理器配置的核心业务逻辑
"""

import os

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from typing import List, Optional, Callable, Dict, Any
from models.preview_config import (
    HandlerConfig, PreviewConfigFile, 
    ConfigOperationResult, ConfigOperationResponse,
    DefaultPreviewConfig
)
from services.config_validator import ConfigValidator
from services.preview_config_migration import PreviewConfigMigration
from core.logger import logger
from core.config import config_manager


class PreviewConfigManager:
    """
    预览配置管理器（单例模式）
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._config: Optional[PreviewConfigFile] = None
        self._listeners: List[Callable] = []
        self._config_file_path = self._get_config_file_path()
        
        # 加载配置
        self._load_config()
    
    def _get_config_file_path(self) -> str:
        """获取配置文件路径"""
        # 从配置管理器获取配置文件路径
        config_dir = os.path.dirname(config_manager.config_path)
        preview_config_path = os.path.join(config_dir, "preview_config.yaml")
        return preview_config_path
    
    def _load_config(self) -> None:
        """加载配置"""
        try:
            if os.path.exists(self._config_file_path):
                if not HAS_YAML:
                    self._config = DefaultPreviewConfig.get_default_config()
                    logger.warning("yaml模块未安装，使用默认预览配置")
                    return
                
                # 从文件加载
                with open(self._config_file_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f) or {}
                
                # 执行迁移
                migrated_data = PreviewConfigMigration.migrate(config_data)
                
                # 创建配置对象
                self._config = PreviewConfigFile.from_dict(migrated_data)
                
                logger.info(f"预览配置加载成功，处理器数量: {len(self._config.handlers)}")
            else:
                # 使用默认配置
                self._config = DefaultPreviewConfig.get_default_config()
                logger.info("预览配置文件不存在，使用默认配置")
                
                # 保存默认配置到文件
                self._save_config()
        
        except Exception as e:
            logger.error(f"加载预览配置失败: {e}，使用默认配置")
            self._config = DefaultPreviewConfig.get_default_config()
    
    def _save_config(self) -> ConfigOperationResponse:
        """保存配置"""
        if not HAS_YAML:
            return ConfigOperationResponse(
                result=ConfigOperationResult.FILE_ERROR,
                message="yaml模块未安装，无法保存配置"
            )
        
        try:
            # 验证配置
            result = ConfigValidator.validate_config_file(self._config)
            if not result.is_success:
                return result
            
            # 转换为字典
            config_data = self._config.to_dict()
            
            # 写入文件
            with open(self._config_file_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(config_data, f, allow_unicode=True, default_flow_style=False)
            
            logger.info(f"预览配置保存成功: {self._config_file_path}")
            
            # 通知监听器
            self._notify_config_changed()
            
            return ConfigOperationResponse(
                result=ConfigOperationResult.SUCCESS,
                message="配置保存成功"
            )
        
        except Exception as e:
            logger.error(f"保存预览配置失败: {e}")
            return ConfigOperationResponse(
                result=ConfigOperationResult.FILE_ERROR,
                message=f"配置保存失败: {e}"
            )
    
    def get_handlers(self) -> List[HandlerConfig]:
        """获取所有处理器配置"""
        return self._config.handlers.copy()
    
    def get_handler(self, name: str) -> Optional[HandlerConfig]:
        """根据名称获取处理器配置"""
        return self._config.get_handler(name)
    
    def update_handler(self, handler: HandlerConfig) -> ConfigOperationResponse:
        """
        更新处理器配置
        
        Args:
            handler: 新的处理器配置
            
        Returns:
            ConfigOperationResponse: 操作结果
        """
        # 验证处理器配置
        result = ConfigValidator.validate_handler_config(handler)
        if not result.is_success:
            return result
        
        # 更新配置
        result = self._config.update_handler(handler)
        if not result.is_success:
            return result
        
        # 保存配置
        return self._save_config()
    
    def add_extension(self, handler_name: str, extension: str) -> ConfigOperationResponse:
        """
        为处理器添加扩展名
        
        Args:
            handler_name: 处理器名称
            extension: 扩展名
            
        Returns:
            ConfigOperationResponse: 操作结果
        """
        # 获取处理器
        handler = self._config.get_handler(handler_name)
        if handler is None:
            return ConfigOperationResponse(
                result=ConfigOperationResult.VALIDATION_ERROR,
                message=f"处理器不存在: {handler_name}"
            )
        
        # 验证扩展名格式
        result = ConfigValidator.validate_extension(extension)
        if not result.is_success:
            return result
        
        # 检查重复
        result = ConfigValidator.check_duplicate(handler, extension)
        if not result.is_success:
            return result
        
        # 检查冲突
        result = ConfigValidator.check_conflicts(self._config, extension, exclude_handler=handler_name)
        
        # 添加扩展名
        handler.add_extension(extension)
        
        # 保存配置
        save_result = self._save_config()
        
        # 如果有冲突，返回警告
        if result.is_warning:
            return ConfigOperationResponse(
                result=ConfigOperationResult.CONFLICT_ERROR,
                message=f"扩展名添加成功，但存在冲突: {result.message}",
                data=result.data
            )
        
        return save_result
    
    def remove_extension(self, handler_name: str, extension: str) -> ConfigOperationResponse:
        """
        从处理器移除扩展名
        
        Args:
            handler_name: 处理器名称
            extension: 扩展名
            
        Returns:
            ConfigOperationResponse: 操作结果
        """
        # 获取处理器
        handler = self._config.get_handler(handler_name)
        if handler is None:
            return ConfigOperationResponse(
                result=ConfigOperationResult.VALIDATION_ERROR,
                message=f"处理器不存在: {handler_name}"
            )
        
        # 移除扩展名
        result = handler.remove_extension(extension)
        if not result.is_success:
            return result
        
        # 保存配置
        return self._save_config()
    
    def set_handler_enabled(self, handler_name: str, enabled: bool) -> ConfigOperationResponse:
        """
        设置处理器启用状态
        
        Args:
            handler_name: 处理器名称
            enabled: 启用状态
            
        Returns:
            ConfigOperationResponse: 操作结果
        """
        handler = self._config.get_handler(handler_name)
        if handler is None:
            return ConfigOperationResponse(
                result=ConfigOperationResult.VALIDATION_ERROR,
                message=f"处理器不存在: {handler_name}"
            )
        
        handler.enabled = enabled
        
        # 保存配置
        return self._save_config()
    
    def set_handler_priority(self, handler_name: str, priority: int) -> ConfigOperationResponse:
        """
        设置处理器优先级
        
        Args:
            handler_name: 处理器名称
            priority: 优先级（1-100）
            
        Returns:
            ConfigOperationResponse: 操作结果
        """
        handler = self._config.get_handler(handler_name)
        if handler is None:
            return ConfigOperationResponse(
                result=ConfigOperationResult.VALIDATION_ERROR,
                message=f"处理器不存在: {handler_name}"
            )
        
        # 验证优先级范围
        if not (1 <= priority <= 100):
            return ConfigOperationResponse(
                result=ConfigOperationResult.VALIDATION_ERROR,
                message=f"优先级必须在1-100之间，当前值: {priority}"
            )
        
        handler.priority = priority
        
        # 保存配置
        return self._save_config()
    
    def reset_to_default(self) -> ConfigOperationResponse:
        """重置为默认配置"""
        try:
            self._config = DefaultPreviewConfig.get_default_config()
            
            # 保存配置
            result = self._save_config()
            
            if result.is_success:
                logger.info("预览配置已重置为默认配置")
            
            return result
        
        except Exception as e:
            logger.error(f"重置预览配置失败: {e}")
            return ConfigOperationResponse(
                result=ConfigOperationResult.UNKNOWN_ERROR,
                message=f"重置配置失败: {e}"
            )
    
    def export_config(self, file_path: str) -> ConfigOperationResponse:
        """
        导出配置到文件
        
        Args:
            file_path: 目标文件路径
            
        Returns:
            ConfigOperationResponse: 操作结果
        """
        if not HAS_YAML:
            return ConfigOperationResponse(
                result=ConfigOperationResult.FILE_ERROR,
                message="yaml模块未安装，无法导出配置"
            )
        
        try:
            config_data = self._config.to_dict()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(config_data, f, allow_unicode=True, default_flow_style=False)
            
            logger.info(f"预览配置导出成功: {file_path}")
            
            return ConfigOperationResponse(
                result=ConfigOperationResult.SUCCESS,
                message=f"配置导出成功: {file_path}"
            )
        
        except Exception as e:
            logger.error(f"导出预览配置失败: {e}")
            return ConfigOperationResponse(
                result=ConfigOperationResult.FILE_ERROR,
                message=f"配置导出失败: {e}"
            )
    
    def import_config(self, file_path: str) -> ConfigOperationResponse:
        """
        从文件导入配置
        
        Args:
            file_path: 源文件路径
            
        Returns:
            ConfigOperationResponse: 操作结果
        """
        try:
            if not os.path.exists(file_path):
                return ConfigOperationResponse(
                    result=ConfigOperationResult.FILE_ERROR,
                    message=f"配置文件不存在: {file_path}"
                )
            
            if not HAS_YAML:
                return ConfigOperationResponse(
                    result=ConfigOperationResult.FILE_ERROR,
                    message="yaml模块未安装，无法导入配置"
                )
            
            # 读取配置
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f) or {}
            
            # 执行迁移
            migrated_data = PreviewConfigMigration.migrate(config_data)
            
            # 创建配置对象
            new_config = PreviewConfigFile.from_dict(migrated_data)
            
            # 验证配置
            result = ConfigValidator.validate_config_file(new_config)
            if not result.is_success:
                return result
            
            # 应用配置
            self._config = new_config
            
            # 保存配置
            save_result = self._save_config()
            
            if save_result.is_success:
                logger.info(f"预览配置导入成功: {file_path}")
            
            return save_result
        
        except Exception as e:
            logger.error(f"导入预览配置失败: {e}")
            return ConfigOperationResponse(
                result=ConfigOperationResult.FILE_ERROR,
                message=f"配置导入失败: {e}"
            )
    
    def add_config_listener(self, listener: Callable) -> None:
        """
        添加配置变更监听器
        
        Args:
            listener: 监听器函数
        """
        if listener not in self._listeners:
            self._listeners.append(listener)
    
    def remove_config_listener(self, listener: Callable) -> None:
        """
        移除配置变更监听器
        
        Args:
            listener: 监听器函数
        """
        if listener in self._listeners:
            self._listeners.remove(listener)
    
    def _notify_config_changed(self) -> None:
        """通知配置变更"""
        for listener in self._listeners:
            try:
                listener(self._config)
            except Exception as e:
                logger.error(f"通知配置变更失败: {e}")
    
    def get_config(self) -> PreviewConfigFile:
        """获取当前配置"""
        return self._config


# 全局单例
preview_config_manager = PreviewConfigManager()