#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本文件预览处理器
支持txt、log、py等文本文件的预览
"""

import os
import re
from PySide6.QtWidgets import QWidget, QTextEdit, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

from .base_handler import PreviewHandler
from core.utils import detect_file_encoding
from core.config import config_manager
from core.logger import logger


class TextPreviewHandler(PreviewHandler):
    """
    文本文件预览处理器
    支持txt、log、py等文本文件
    """
    
    def can_handle(self, file_path: str) -> bool:
        """检查是否为文本文件"""
        text_extensions = [
            '.txt', '.log', '.py', '.yaml', '.yml', '.ini', 
            '.csv', '.html', '.css', '.js', '.sql', '.lrc',
            '.java', '.c', '.cpp', '.h', '.hpp', '.php', '.rb', '.go',
            '.sh', '.bat', '.ps1', '.lua', '.pl', '.swift', '.kt', '.rs',
            '.asm', '.pas', '.d', '.rust', '.scala', '.groovy', '.vb',
            '.cs', '.f', '.f90', '.fortran', '.m', '.matlab', '.r', '.sas',
            '.stata', '.sql', '.pgsql', '.mysql', '.mssql', '.oracle',
            '.jsonl', '.ndjson', '.toml', '.properties', '.env', '.gitignore',
            '.dockerfile', '.dockerignore', '.xsl',
            '.xslt', '.dtd', '.xsd', '.wsdl', '.wSDL', '.xhtml', '.xht',
            '.shtml', '.shtm', '.htm', '.html', '.css', '.scss', '.sass',
            '.less', '.styl', '.jsx', '.tsx', '.ts', '.js', '.mjs', '.cjs',
            '.vue', '.svelte', '.astro', '.mdx', '.rmd', '.qmd', '.ipynb',
            '.rtf'
        ]
        _, ext = os.path.splitext(file_path)
        return ext.lower() in text_extensions
    
    def preview(self, file_path: str, parent_widget: QWidget) -> QWidget:
        """生成文本文件预览"""
        content = ""
        encoding_used = ""
        
        try:
            # 检查文件大小，对于大文件使用分块读取
            try:
                file_size = os.path.getsize(file_path)
            except (OSError, PermissionError):
                file_size = 0
            max_file_size = config_manager.get("preview.max_file_size", 50) * 1024 * 1024  # 默认50MB
            
            if file_size > max_file_size:
                # 大文件处理
                encoding = detect_file_encoding(file_path)
                if encoding == '未知':
                    encoding = 'utf-8'  # 默认为utf-8
                
                try:
                    with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                        # 只读取前1000行，避免内存溢出
                        lines = []
                        for i, line in enumerate(f):
                            if i >= 1000:
                                lines.append("\n... (文件过大，仅显示前1000行)\n")
                                break
                            lines.append(line)
                        content = ''.join(lines)
                    encoding_used = f"{encoding} (大文件模式)"
                except Exception as e:
                    logger.error(f"读取大文本文件失败: {file_path}, 错误: {e}")
                    return self._create_error_widget(f"无法读取文件: {file_path}")
            else:
                # 检测文件扩展名
                _, ext = os.path.splitext(file_path.lower())
                
                # 对于RTF文件，尝试解析提取纯文本
                if ext == '.rtf':
                    try:
                        # 尝试使用rtfparse库解析RTF文件
                        try:
                            from rtfparse import parse
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                rtf_content = f.read()
                            parsed_content = parse(rtf_content)
                            content = parsed_content.text
                            encoding_used = 'utf-8 (RTF解析)'
                        except ImportError:
                            # 如果rtfparse库未安装，使用简单的RTF解析
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                rtf_content = f.read()
                            # 简单的RTF标签移除
                            content = re.sub(r'{[^}]*}', '', rtf_content)
                            # 移除控制字符
                            content = re.sub(r'\\[a-z]+', '', content)
                            # 移除多余的空白字符
                            content = ' '.join(content.split())
                            encoding_used = 'utf-8 (简单RTF解析)'
                    except Exception as rtf_error:
                        logger.warning(f"RTF解析失败: {file_path}, 错误: {rtf_error}")
                        # 降级为普通文本读取
                        encoding = detect_file_encoding(file_path)
                        if encoding == '未知':
                            encoding = 'utf-8'
                        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                            content = f.read()
                        encoding_used = encoding
                else:
                    # 普通文本文件
                    encoding = detect_file_encoding(file_path)
                    if encoding == '未知':
                        encoding = 'utf-8'
                    
                    with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                        content = f.read()
                    encoding_used = encoding
            
            # 创建预览组件
            widget = QWidget(parent_widget)
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(5, 5, 5, 5)
            
            # 添加编码信息标签
            info_label = QLabel(f"编码: {encoding_used} | 大小: {self._format_size(file_size)}")
            info_label.setStyleSheet("color: gray; font-size: 10px;")
            layout.addWidget(info_label)
            
            # 创建文本编辑器（只读）
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setPlainText(content)
            text_edit.setFontFamily("Consolas, Courier New, monospace")
            text_edit.setFontPointSize(10)
            
            layout.addWidget(text_edit)
            
            return widget
            
        except Exception as e:
            logger.error(f"文本预览失败: {file_path}, 错误: {e}")
            return self._create_error_widget(f"无法预览文件: {str(e)}")
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    def _create_error_widget(self, error_message: str) -> QWidget:
        """创建错误提示组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        label = QLabel(error_message)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: red; font-size: 12px;")
        
        layout.addWidget(label)
        return widget


# 创建单例实例
text_preview_handler = TextPreviewHandler()
