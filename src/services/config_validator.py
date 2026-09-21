#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置验证器模块
验证预览配置的完整性和正确性
"""

import re
from typing import List, Tuple, Optional
from models.preview_config import HandlerConfig, PreviewConfigFile, ConfigOperationResult, ConfigOperationResponse


class ConfigValidator:
    """配置验证器"""
    
    # 扩展名格式验证正则（支持复合扩展名如 .tar.gz）
    EXTENSION_PATTERN = re.compile(r'^\.[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*$')
    
    @staticmethod
    def validate_extension(extension: str) -> ConfigOperationResponse:
        """
        验证扩展名格式
        
        Args:
            extension: 扩展名
            
        Returns:
            ConfigOperationResponse: 验证结果
        """
        if not extension or not isinstance(extension, str):
            return ConfigOperationResponse(
                result=ConfigOperationResult.VALIDATION_ERROR,
                message="扩展名不能为空且必须为字符串"
            )
        
        if not ConfigValidator.EXTENSION_PATTERN.match(extension):
            return ConfigOperationResponse(
                result=ConfigOperationResult.VALIDATION_ERROR,
                message=f"扩展名格式无效: {extension}，必须为 .xxx 或 .xxx.xxx 格式（如 .txt 或 .tar.gz）"
            )
        
        return ConfigOperationResponse(
            result=ConfigOperationResult.SUCCESS,
            message="扩展名格式有效"
        )
    
    @staticmethod
    def check_duplicate(handler: HandlerConfig, extension: str) -> ConfigOperationResponse:
        """
        检查扩展名在处理器内是否重复
        
        Args:
            handler: 处理器配置
            extension: 扩展名
            
        Returns:
            ConfigOperationResponse: 检查结果
        """
        if extension.lower() in [ext.lower() for ext in handler.extensions]:
            return ConfigOperationResponse(
                result=ConfigOperationResult.DUPLICATE_ERROR,
                message=f"扩展名 {extension} 在处理器 {handler.name} 中已存在"
            )
        
        return ConfigOperationResponse(
            result=ConfigOperationResult.SUCCESS,
            message="扩展名不重复"
        )
    
    @staticmethod
    def check_conflicts(config: PreviewConfigFile, extension: str, 
                       exclude_handler: Optional[str] = None) -> ConfigOperationResponse:
        """
        检查扩展名是否与其他处理器冲突
        
        Args:
            config: 配置文件
            extension: 扩展名
            exclude_handler: 排除的处理器名称（用于更新场景）
            
        Returns:
            ConfigOperationResponse: 检查结果（冲突时返回警告而非错误）
        """
        conflicting_handlers = []
        
        for handler in config.handlers:
            # 跳过排除的处理器
            if exclude_handler and handler.name == exclude_handler:
                continue
            
            # 检查是否包含该扩展名
            if handler.has_extension(extension):
                conflicting_handlers.append(handler.name)
        
        if conflicting_handlers:
            return ConfigOperationResponse(
                result=ConfigOperationResult.CONFLICT_ERROR,
                message=f"扩展名 {extension} 与其他处理器冲突: {', '.join(conflicting_handlers)}",
                data=conflicting_handlers
            )
        
        return ConfigOperationResponse(
            result=ConfigOperationResult.SUCCESS,
            message="扩展名无冲突"
        )
    
    @staticmethod
    def validate_handler_config(handler: HandlerConfig) -> ConfigOperationResponse:
        """
        验证处理器配置完整性
        
        Args:
            handler: 处理器配置
            
        Returns:
            ConfigOperationResponse: 验证结果
        """
        # 验证名称
        if not handler.name or not isinstance(handler.name, str):
            return ConfigOperationResponse(
                result=ConfigOperationResult.VALIDATION_ERROR,
                message="处理器名称不能为空且必须为字符串"
            )
        
        # 验证优先级
        if not (1 <= handler.priority <= 100):
            return ConfigOperationResponse(
                result=ConfigOperationResult.VALIDATION_ERROR,
                message=f"优先级必须在1-100之间，当前值: {handler.priority}"
            )
        
        # 验证扩展名列表
        if not isinstance(handler.extensions, list):
            return ConfigOperationResponse(
                result=ConfigOperationResult.VALIDATION_ERROR,
                message="扩展名列表必须为列表类型"
            )
        
        # 验证每个扩展名格式
        for ext in handler.extensions:
            result = ConfigValidator.validate_extension(ext)
            if not result.is_success:
                return result
        
        return ConfigOperationResponse(
            result=ConfigOperationResult.SUCCESS,
            message=f"处理器配置验证通过: {handler.name}"
        )
    
    @staticmethod
    def validate_config_file(config: PreviewConfigFile) -> ConfigOperationResponse:
        """
        验证配置文件完整性
        
        Args:
            config: 配置文件
            
        Returns:
            ConfigOperationResponse: 验证结果
        """
        # 验证版本号
        if not config.version or not isinstance(config.version, str):
            return ConfigOperationResponse(
                result=ConfigOperationResult.VALIDATION_ERROR,
                message="版本号不能为空且必须为字符串"
            )
        
        # 验证处理器列表
        if not isinstance(config.handlers, list):
            return ConfigOperationResponse(
                result=ConfigOperationResult.VALIDATION_ERROR,
                message="处理器列表必须为列表类型"
            )
        
        # 验证处理器名称唯一性
        handler_names = [h.name for h in config.handlers]
        if len(handler_names) != len(set(handler_names)):
            duplicates = [name for name in handler_names if handler_names.count(name) > 1]
            return ConfigOperationResponse(
                result=ConfigOperationResult.VALIDATION_ERROR,
                message=f"处理器名称重复: {', '.join(set(duplicates))}"
            )
        
        # 验证每个处理器配置
        for handler in config.handlers:
            result = ConfigValidator.validate_handler_config(handler)
            if not result.is_success:
                return result
        
        return ConfigOperationResponse(
            result=ConfigOperationResult.SUCCESS,
            message="配置文件验证通过"
        )
    
    @staticmethod
    def find_all_conflicts(config: PreviewConfigFile) -> List[Tuple[str, str, List[str]]]:
        """
        查找所有扩展名冲突
        
        Args:
            config: 配置文件
            
        Returns:
            List[Tuple[str, str, List[str]]]: 冲突列表 [(扩展名, 处理器名, [冲突处理器列表])]
        """
        conflicts = []
        all_extensions = {}
        
        # 收集所有扩展名及其所属处理器
        for handler in config.handlers:
            for ext in handler.extensions:
                ext_lower = ext.lower()
                if ext_lower not in all_extensions:
                    all_extensions[ext_lower] = []
                all_extensions[ext_lower].append(handler.name)
        
        # 找出冲突的扩展名
        for ext, handlers in all_extensions.items():
            if len(handlers) > 1:
                for handler in handlers:
                    conflicts.append((ext, handler, [h for h in handlers if h != handler]))
        
        return conflicts