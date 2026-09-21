#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预览处理器包
包含各种文件类型的预览处理器
"""

from .base_handler import PreviewHandler
from .text_handler import text_preview_handler, TextPreviewHandler
from .image_handler import image_preview_handler, ImagePreviewHandler

# 导出所有处理器
__all__ = [
    'PreviewHandler',
    'TextPreviewHandler', 'text_preview_handler',
    'ImagePreviewHandler', 'image_preview_handler',
]
