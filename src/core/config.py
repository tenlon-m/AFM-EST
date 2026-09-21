#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
负责加载、保存和管理应用配置
"""

import logging
from pathlib import Path
from typing import Any, Dict

_config_logger = logging.getLogger(__name__)

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

class ConfigManager:
    """
    配置管理器类
    使用YAML格式存储配置文件
    """
    
    def __init__(self, config_path: str = "config/default.yaml"):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = self._load_default_config()
        self._load_config()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """
        加载默认配置
        
        Returns:
            默认配置字典
        """
        return {
            "ui": {
                "window_size": [1200, 600],
                "splitter_ratio": [4/11, 4/11, 3/11],
                "theme": "light",
                "default_view": "detail",
                "show_hidden_files": False,
                "auto_expand_folder_tree": False
            },
            "search": {
                "enable_indexing": True,
                "index_locations": [],
                "index_update_interval": 60,
                "max_search_threads": 8
            },
            "transfer": {
                "ftp_connections": [],
                "p2p_port": 58432,
                "max_transfer_threads": 4,
                "chunk_size": 8,
                "speed_limit": 0
            },
            "preview": {
                "max_file_size": 50,
                "text_encoding_detection": "advanced",
                "image_cache_size": 100
            },
            "tools": {
                "batch_rename_template": "{prefix}_{index:03d}_{suffix}",
                "default_compress_format": "zip",
                "compress_level": 6
            }
        }
    
    def _load_config(self) -> None:
        """
        从文件加载配置
        """
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    if HAS_YAML:
                        file_config = yaml.safe_load(f)
                    else:
                        import json
                        file_config = json.load(f)
                    if file_config:
                        self._merge_config(self.config, file_config)
            except Exception as e:
                _config_logger.warning(f"加载配置文件失败: {e}")
        else:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.save_config()
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """
        合并配置字典
        
        Args:
            base: 基础配置
            override: 覆盖配置
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def save_config(self) -> None:
        """
        保存配置到文件
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                if HAS_YAML:
                    yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
                else:
                    import json
                    json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            _config_logger.warning(f"保存配置文件失败: {e}")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key_path: 配置键路径，如 "ui.theme"
            default: 默认值
            
        Returns:
            配置值或默认值
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key_path: 配置键路径，如 "ui.theme"
            value: 配置值
        """
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
        self.save_config()
    
    def get_ui_config(self) -> Dict[str, Any]:
        """
        获取UI配置
        
        Returns:
            UI配置字典
        """
        return self.config.get("ui", {})
    
    def get_search_config(self) -> Dict[str, Any]:
        """
        获取搜索配置
        
        Returns:
            搜索配置字典
        """
        return self.config.get("search", {})
    
    def get_transfer_config(self) -> Dict[str, Any]:
        """
        获取传输配置
        
        Returns:
            传输配置字典
        """
        return self.config.get("transfer", {})
    
    def get_preview_config(self) -> Dict[str, Any]:
        """
        获取预览配置
        
        Returns:
            预览配置字典
        """
        return self.config.get("preview", {})
    
    def get_tools_config(self) -> Dict[str, Any]:
        """
        获取工具配置
        
        Returns:
            工具配置字典
        """
        return self.config.get("tools", {})

# 创建全局配置管理器实例
config_manager = ConfigManager()
