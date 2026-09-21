#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预览配置数据模型模块
定义预览处理器配置的数据结构
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
import re


class ConfigOperationResult(Enum):
    """配置操作结果枚举"""
    SUCCESS = "success"
    VALIDATION_ERROR = "validation_error"
    DUPLICATE_ERROR = "duplicate_error"
    CONFLICT_ERROR = "conflict_error"
    FILE_ERROR = "file_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ConfigOperationResponse:
    """配置操作响应"""
    result: ConfigOperationResult
    message: str = ""
    data: Optional[Any] = None
    
    @property
    def is_success(self) -> bool:
        """是否成功"""
        return self.result == ConfigOperationResult.SUCCESS
    
    @property
    def is_warning(self) -> bool:
        """是否为警告（冲突但可继续）"""
        return self.result == ConfigOperationResult.CONFLICT_ERROR


@dataclass
class HandlerConfig:
    """
    预览处理器配置
    """
    name: str
    enabled: bool = True
    priority: int = 50
    extensions: List[str] = field(default_factory=list)
    
    # 扩展名格式验证正则（支持复合扩展名如 .tar.gz）
    EXTENSION_PATTERN = re.compile(r'^\.[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*$')
    
    def __post_init__(self):
        """初始化后验证"""
        # 验证处理器名称
        if not self.name or not isinstance(self.name, str):
            raise ValueError("处理器名称不能为空且必须为字符串")
        
        # 验证优先级范围
        if not (1 <= self.priority <= 100):
            raise ValueError(f"优先级必须在1-100之间，当前值: {self.priority}")
        
        # 验证扩展名列表
        if not isinstance(self.extensions, list):
            raise ValueError("扩展名列表必须为列表类型")
        
        # 验证每个扩展名格式
        for ext in self.extensions:
            if not self.EXTENSION_PATTERN.match(ext):
                raise ValueError(f"扩展名格式无效: {ext}，必须为 .xxx 格式")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "priority": self.priority,
            "extensions": self.extensions.copy()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HandlerConfig':
        """从字典创建"""
        return cls(
            name=data.get("name", ""),
            enabled=data.get("enabled", True),
            priority=data.get("priority", 50),
            extensions=data.get("extensions", [])
        )
    
    def add_extension(self, extension: str) -> ConfigOperationResponse:
        """
        添加扩展名
        
        Args:
            extension: 要添加的扩展名
            
        Returns:
            ConfigOperationResponse: 操作结果
        """
        # 验证格式
        if not self.EXTENSION_PATTERN.match(extension):
            return ConfigOperationResponse(
                result=ConfigOperationResult.VALIDATION_ERROR,
                message=f"扩展名格式无效: {extension}，必须为 .xxx 格式"
            )
        
        # 检查重复
        if extension in self.extensions:
            return ConfigOperationResponse(
                result=ConfigOperationResult.DUPLICATE_ERROR,
                message=f"扩展名已存在: {extension}"
            )
        
        # 添加扩展名
        self.extensions.append(extension)
        return ConfigOperationResponse(
            result=ConfigOperationResult.SUCCESS,
            message=f"扩展名添加成功: {extension}"
        )
    
    def remove_extension(self, extension: str) -> ConfigOperationResponse:
        """
        移除扩展名
        
        Args:
            extension: 要移除的扩展名
            
        Returns:
            ConfigOperationResponse: 操作结果
        """
        if extension not in self.extensions:
            return ConfigOperationResponse(
                result=ConfigOperationResult.VALIDATION_ERROR,
                message=f"扩展名不存在: {extension}"
            )
        
        self.extensions.remove(extension)
        return ConfigOperationResponse(
            result=ConfigOperationResult.SUCCESS,
            message=f"扩展名移除成功: {extension}"
        )
    
    def has_extension(self, extension: str) -> bool:
        """检查是否包含指定扩展名"""
        return extension.lower() in [ext.lower() for ext in self.extensions]


@dataclass
class PreviewConfigFile:
    """
    预览配置文件数据结构
    """
    version: str = "1.0"
    handlers: List[HandlerConfig] = field(default_factory=list)
    
    def __post_init__(self):
        """初始化后验证"""
        # 验证版本号
        if not self.version or not isinstance(self.version, str):
            raise ValueError("版本号不能为空且必须为字符串")
        
        # 验证处理器列表
        if not isinstance(self.handlers, list):
            raise ValueError("处理器列表必须为列表类型")
        
        # 验证处理器名称唯一性
        handler_names = [h.name for h in self.handlers]
        if len(handler_names) != len(set(handler_names)):
            raise ValueError("处理器名称必须唯一")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "version": self.version,
            "handlers": [h.to_dict() for h in self.handlers]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PreviewConfigFile':
        """从字典创建"""
        handlers_data = data.get("handlers", [])
        handlers = [HandlerConfig.from_dict(h) for h in handlers_data]
        
        return cls(
            version=data.get("version", "1.0"),
            handlers=handlers
        )
    
    def get_handler(self, name: str) -> Optional[HandlerConfig]:
        """
        根据名称获取处理器配置
        
        Args:
            name: 处理器名称
            
        Returns:
            HandlerConfig: 处理器配置，不存在则返回None
        """
        for handler in self.handlers:
            if handler.name == name:
                return handler
        return None
    
    def update_handler(self, handler: HandlerConfig) -> ConfigOperationResponse:
        """
        更新处理器配置
        
        Args:
            handler: 新的处理器配置
            
        Returns:
            ConfigOperationResponse: 操作结果
        """
        for i, h in enumerate(self.handlers):
            if h.name == handler.name:
                self.handlers[i] = handler
                return ConfigOperationResponse(
                    result=ConfigOperationResult.SUCCESS,
                    message=f"处理器配置更新成功: {handler.name}"
                )
        
        return ConfigOperationResponse(
            result=ConfigOperationResult.VALIDATION_ERROR,
            message=f"处理器不存在: {handler.name}"
        )
    
    def add_handler(self, handler: HandlerConfig) -> ConfigOperationResponse:
        """
        添加处理器配置
        
        Args:
            handler: 处理器配置
            
        Returns:
            ConfigOperationResponse: 操作结果
        """
        if self.get_handler(handler.name) is not None:
            return ConfigOperationResponse(
                result=ConfigOperationResult.DUPLICATE_ERROR,
                message=f"处理器已存在: {handler.name}"
            )
        
        self.handlers.append(handler)
        return ConfigOperationResponse(
            result=ConfigOperationResult.SUCCESS,
            message=f"处理器添加成功: {handler.name}"
        )
    
    def get_all_extensions(self) -> List[str]:
        """获取所有扩展名（去重）"""
        all_exts = []
        for handler in self.handlers:
            all_exts.extend(handler.extensions)
        return list(set(all_exts))


class DefaultPreviewConfig:
    """默认预览配置"""
    
    @staticmethod
    def get_default_handlers() -> List[HandlerConfig]:
        """获取默认处理器配置列表"""
        return [
            HandlerConfig(
                name="MarkdownPreviewHandler",
                enabled=True,
                priority=1,
                extensions=[".md", ".markdown", ".mdown", ".mkd", ".mkdown"]
            ),
            HandlerConfig(
                name="CodeHighlightPreviewHandler",
                enabled=True,
                priority=2,
                extensions=[
                    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp",
                    ".h", ".hpp", ".cs", ".go", ".rs", ".rb", ".php", ".swift",
                    ".kt", ".scala", ".lua", ".sql", ".sh", ".bash", ".ps1",
                    ".html", ".htm", ".css", ".scss", ".less", ".xml", ".json",
                    ".yaml", ".yml", ".toml", ".ini", ".vue", ".svelte"
                ]
            ),
            HandlerConfig(
                name="TextPreviewHandler",
                enabled=True,
                priority=3,
                extensions=[
                    ".txt", ".log", ".yaml", ".yml", ".ini", ".csv", ".html",
                    ".css", ".js", ".sql", ".lrc", ".java", ".c", ".cpp", ".h",
                    ".hpp", ".php", ".rb", ".go", ".sh", ".bat", ".ps1", ".lua",
                    ".pl", ".swift", ".kt", ".rs", ".asm", ".pas", ".d", ".rust",
                    ".scala", ".groovy", ".vb", ".cs", ".f", ".f90", ".fortran",
                    ".m", ".matlab", ".r", ".sas", ".stata", ".pgsql", ".mysql",
                    ".mssql", ".oracle", ".jsonl", ".ndjson", ".toml", ".properties",
                    ".env", ".gitignore", ".dockerfile", ".dockerignore", ".xsl",
                    ".xslt", ".dtd", ".xsd", ".wsdl", ".wSDL", ".xhtml", ".xht",
                    ".shtml", ".shtm", ".htm", ".scss", ".sass", ".less", ".styl",
                    ".mjs", ".cjs", ".vue", ".svelte", ".astro", ".mdx", ".rmd",
                    ".qmd", ".ipynb", ".rtf", ".m3u", ".m3u8", ".pls", ".xspf"
                ]
            ),
            HandlerConfig(
                name="ImagePreviewHandler",
                enabled=True,
                priority=4,
                extensions=[".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg",
                           ".webp", ".ico", ".tiff", ".tif"]
            ),
            HandlerConfig(
                name="DocumentPreviewHandler",
                enabled=True,
                priority=5,
                extensions=[".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
                           ".pdf", ".wps", ".et", ".dps"]
            ),
            HandlerConfig(
                name="AudioVideoPreviewHandler",
                enabled=True,
                priority=6,
                extensions=[
                    ".mp3", ".mp4", ".avi", ".mkv", ".flac", ".wav", ".ogg",
                    ".mov", ".wmv", ".m4a", ".aac", ".wma", ".ac3", ".dts",
                    ".ape", ".m4v", ".3gp", ".flv", ".ts", ".m2ts", ".vob", ".webm"
                ]
            ),
            HandlerConfig(
                name="ArchivePreviewHandler",
                enabled=True,
                priority=7,
                extensions=[".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
                           ".tar.gz", ".tar.bz2", ".tar.xz", ".iso"]
            ),
            HandlerConfig(
                name="SpecialFormatPreviewHandler",
                enabled=True,
                priority=8,
                extensions=[".sqlite", ".db", ".ttf", ".otf", ".woff", ".woff2", ".eot"]
            ),
        ]
    
    @staticmethod
    def get_default_config() -> PreviewConfigFile:
        """获取默认配置文件"""
        return PreviewConfigFile(
            version="1.0",
            handlers=DefaultPreviewConfig.get_default_handlers()
        )