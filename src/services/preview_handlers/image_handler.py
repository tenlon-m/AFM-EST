#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片文件预览处理器
支持jpg、png、gif等图片文件的预览，带LRU缓存管理
"""

import os
import threading
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from .base_handler import PreviewHandler
from core.config import config_manager
from core.logger import logger


class ImagePreviewHandler(PreviewHandler):
    
    def __init__(self):
        self.image_cache = {}
        self.cache_size = 0
        self.max_cache_size = config_manager.get("preview.image_cache_size", 100) * 1024 * 1024
        self._cache_lock = threading.Lock()
    
    def can_handle(self, file_path: str) -> bool:
        """检查是否为图片文件"""
        image_extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg',
            '.webp', '.ico', '.tiff', '.tif'
        ]
        _, ext = os.path.splitext(file_path)
        return ext.lower() in image_extensions
    
    def _clean_cache(self):
        while self.cache_size > self.max_cache_size:
            oldest_path = next(iter(self.image_cache))
            if oldest_path in self.image_cache:
                del self.image_cache[oldest_path]
                self.cache_size -= 1024 * 1024
    
    def preview(self, file_path: str, parent_widget: QWidget) -> QWidget:
        try:
            try:
                file_size = os.path.getsize(file_path)
            except (OSError, PermissionError):
                file_size = 0
            max_image_size = 50 * 1024 * 1024
            if file_size > max_image_size:
                widget = QWidget()
                layout = QVBoxLayout(widget)
                error_label = QLabel(f"无法预览图片: 文件过大（{file_size/1024/1024:.2f}MB）")
                error_label.setAlignment(Qt.AlignCenter)
                layout.addWidget(error_label)
                return widget
            
            with self._cache_lock:
                if file_path in self.image_cache:
                    pixmap = self.image_cache.pop(file_path)
                    self.image_cache[file_path] = pixmap
                else:
                    pixmap = None
            
            if pixmap is None:
                pixmap = QPixmap(file_path)
                if pixmap.isNull():
                    raise Exception("无法加载图片")
                
                with self._cache_lock:
                    self.image_cache[file_path] = pixmap
                    self.cache_size += file_size
                    self._clean_cache()
            
            # 创建预览组件
            preview_widget = QWidget(parent_widget)
            layout = QVBoxLayout(preview_widget)
            
            # 添加图片信息
            info_layout = QHBoxLayout()
            width_label = QLabel(f"宽度: {pixmap.width()}px")
            height_label = QLabel(f"高度: {pixmap.height()}px")
            try:
                try:
                    size_label = QLabel(f"大小: {os.path.getsize(file_path) / 1024:.2f}KB")
                except (OSError, PermissionError):
                    pass
            except (OSError, PermissionError):
                pass
            
            info_layout.addWidget(width_label)
            info_layout.addWidget(height_label)
            info_layout.addWidget(size_label)
            info_layout.addStretch()
            
            # 添加图片标签
            image_label = QLabel()
            image_label.setPixmap(pixmap)
            image_label.setScaledContents(True)
            image_label.setAlignment(Qt.AlignCenter)
            image_label.setMinimumSize(200, 200)
            
            # 添加到主布局
            layout.addLayout(info_layout)
            layout.addWidget(image_label, 1)
            
            return preview_widget
            
        except Exception as e:
            logger.error(f"读取图片文件失败: {file_path}, 错误: {e}")
            widget = QWidget()
            layout = QVBoxLayout(widget)
            error_label = QLabel(f"无法预览图片: {e}")
            error_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(error_label)
            return widget


# 创建单例实例
image_preview_handler = ImagePreviewHandler()
