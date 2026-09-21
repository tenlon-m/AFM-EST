#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件预览服务模块
负责处理各种文件类型的预览功能
"""

import os
import mimetypes
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (QWidget, QTextEdit, QLabel, QVBoxLayout, 
                              QHBoxLayout, QScrollArea, QPushButton, 
                              QFileDialog, QSplitter, 
                              QTreeView, QFileSystemModel, QFrame, QSlider, QSizePolicy)
from core.utils import show_warning
from PySide6.QtCore import Qt, QUrl, QSize, QTimer
from PySide6.QtGui import QPixmap, QImage, QIcon
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from core.logger import logger
from core.config import config_manager

class PreviewHandler(ABC):
    """
    预览处理器基类
    所有类型的文件预览处理器都必须继承此类
    """
    
    def __init__(self):
        """初始化处理器"""
        self._extensions: list = []
        self._parent_widget: QWidget = None
        self._load_default_extensions()
    
    def _load_default_extensions(self) -> None:
        """加载默认扩展名列表（子类可重写）"""
        pass
    
    def set_extensions(self, extensions: list) -> None:
        """
        设置支持的扩展名列表
        
        Args:
            extensions: 扩展名列表
        """
        self._extensions = extensions
    
    def get_extensions(self) -> list:
        """获取当前扩展名列表"""
        return self._extensions.copy()
    
    @abstractmethod
    def can_handle(self, file_path: str) -> bool:
        """
        检查是否能处理指定文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否能处理
        """
        pass
    
    @abstractmethod
    def preview(self, file_path: str, parent_widget: QWidget) -> QWidget:
        """
        生成文件预览
        
        Args:
            file_path: 文件路径
            parent_widget: 父组件
            
        Returns:
            QWidget: 预览组件
        """
        pass

from core.utils import detect_file_encoding

class TextPreviewHandler(PreviewHandler):
    """
    文本文件预览处理器
    支持txt、log、py等文本文件
    """
    
    def _load_default_extensions(self) -> None:
        """加载默认扩展名"""
        self._extensions = [
            '.txt', '.log', '.py', '.yaml', '.yml', '.ini', 
            '.csv', '.html', '.css', '.js', '.sql', '.lrc',
            '.java', '.c', '.cpp', '.h', '.hpp', '.php', '.rb', '.go',
            '.sh', '.bat', '.ps1', '.lua', '.pl', '.swift', '.kt', '.rs',
            '.asm', '.pas', '.d', '.rust', '.scala', '.groovy', '.vb',
            '.cs', '.f', '.f90', '.fortran', '.m', '.matlab', '.r', '.sas',
            '.stata', '.sql', '.pgsql', '.mysql', '.mssql', '.oracle',
            '.jsonl', '.ndjson', '.toml', '.properties', '.env', '.gitignore',
            '.dockerfile', '.dockerignore', '.yml', '.yaml', '.xsl',
            '.xslt', '.dtd', '.xsd', '.wsdl', '.wSDL', '.xhtml', '.xht',
            '.shtml', '.shtm', '.htm', '.html', '.css', '.scss', '.sass',
            '.less', '.styl', '.jsx', '.tsx', '.ts', '.js', '.mjs', '.cjs',
            '.vue', '.svelte', '.astro', '.mdx', '.rmd', '.qmd', '.ipynb',
            '.rtf', '.m3u', '.m3u8', '.pls', '.xspf'
        ]
    
    def can_handle(self, file_path: str) -> bool:
        """
        检查是否为文本文件
        """
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self._extensions
    
    def preview(self, file_path: str, parent_widget: QWidget) -> QWidget:
        """
        生成文本文件预览
        """
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
                # 大文件处理 - 使用内存映射优化
                encoding = detect_file_encoding(file_path)

                
                try:
                    # 尝试使用内存映射处理大文件
                    import mmap
                    
                    try:
                        with open(file_path, 'rb') as f:
                            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                                max_read_size = 1024 * 1024  # 最多读取1MB
                                content = mm.read(max_read_size).decode(encoding, errors='replace')
                        encoding_used = f"{encoding} (大文件模式-mmap)"
                    except (ValueError, OSError):
                        # mmap文件大小为0或不支持时回退到普通读取
                        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                            lines = []
                            for i, line in enumerate(f):
                                if i >= 1000:
                                    lines.append("\n... (文件过大，仅显示前1000行)\n")
                                    break
                                lines.append(line)
                            content = ''.join(lines)
                        encoding_used = f"{encoding} (大文件模式-流式处理)"
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
                            import re
                            # 移除所有RTF标签
                            content = re.sub(r'{[^}]*}', '', rtf_content)
                            # 移除控制字符
                            content = re.sub(r'\\[a-z]+', '', content)
                            # 移除多余的空白字符
                            content = ' '.join(content.split())
                            encoding_used = 'utf-8 (简单RTF解析)'
                    except Exception as rtf_error:
                        logger.warning(f"RTF解析失败: {file_path}, 错误: {rtf_error}")
                        # 解析失败，回退到普通文本读取
                        encoding = detect_file_encoding(file_path)

                        
                        try:
                            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                                content = f.read()
                            encoding_used = f"{encoding} (RTF解析失败，回退到原始读取)"
                        except Exception as e:
                            logger.error(f"读取RTF文件失败: {file_path}, 错误: {e}")
                            return self._create_error_widget(f"无法读取RTF文件: {file_path}")
                else:
                    # 对于非RTF文件，使用正常的文本读取
                    # 使用优化的编码检测函数
                    encoding = detect_file_encoding(file_path)

                    
                    # 尝试使用检测到的编码打开文件
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            content = f.read()
                        encoding_used = encoding
                    except UnicodeDecodeError:
                        # 如果检测到的编码失败，尝试使用utf-8
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                            encoding_used = 'utf-8 (忽略错误)'
                        except Exception:
                            # 如果utf-8也失败，尝试使用gb18030
                            try:
                                with open(file_path, 'r', encoding='gb18030', errors='ignore') as f:
                                    content = f.read()
                                encoding_used = 'gb18030 (忽略错误)'
                            except Exception as e:
                                logger.error(f"读取文本文件失败: {file_path}, 错误: {e}")
                                return self._create_error_widget(f"无法读取文件: {file_path}")
        except Exception as e:
            logger.error(f"读取文本文件失败: {file_path}, 错误: {e}")
            return self._create_error_widget(f"无法读取文件: {file_path}")
        
        # 创建预览组件
        preview_widget = QWidget(parent_widget)
        layout = QVBoxLayout(preview_widget)
        
        # 添加编码信息标签
        encoding_label = QLabel(f"编码: {encoding_used}")
        encoding_label.setStyleSheet("font-size: 10px; color: #666;")
        layout.addWidget(encoding_label)
        
        # 创建文本编辑组件
        text_edit = QTextEdit()
        text_edit.setPlainText(content)
        text_edit.setReadOnly(True)
        text_edit.setLineWrapMode(QTextEdit.NoWrap)
        
        # 确保右键菜单启用，支持复制功能
        text_edit.setContextMenuPolicy(Qt.DefaultContextMenu)
        
        # 添加行号显示
        text_edit.setObjectName("textPreview")
        
        # 直接添加文本编辑组件，不使用额外的滚动区域
        layout.addWidget(text_edit)
        
        return preview_widget
    
    def _create_error_widget(self, message: str) -> QWidget:
        """
        创建错误提示组件
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        error_label = QLabel(message)
        error_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(error_label)
        return widget

class MarkdownPreviewHandler(PreviewHandler):
    """
    Markdown文件预览处理器
    支持Markdown渲染和预览
    """
    
    def _load_default_extensions(self) -> None:
        """加载默认扩展名"""
        self._extensions = ['.md', '.markdown', '.mdown', '.mkd', '.mkdown']
    
    def can_handle(self, file_path: str) -> bool:
        """检查是否为Markdown文件"""
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self._extensions
    
    def preview(self, file_path: str, parent_widget: QWidget) -> QWidget:
        """生成Markdown预览"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        try:
            # 读取Markdown内容
            with open(file_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # 尝试使用markdown库渲染
            try:
                import markdown
                html_content = markdown.markdown(
                    md_content,
                    extensions=[
                        'extra',
                        'codehilite',
                        'tables',
                        'toc',
                        'fenced_code',
                        'nl2br'
                    ]
                )
                
                # 添加CSS样式
                html_with_style = f"""
                <html>
                <head>
                <style>
                    body {{
                        font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
                        font-size: 14px;
                        line-height: 1.6;
                        color: #333;
                        background-color: #fff;
                        padding: 20px;
                    }}
                    h1, h2, h3, h4, h5, h6 {{
                        color: #2c3e50;
                        margin-top: 24px;
                        margin-bottom: 16px;
                        font-weight: 600;
                    }}
                    h1 {{ font-size: 2em; border-bottom: 1px solid #eee; padding-bottom: 0.3em; }}
                    h2 {{ font-size: 1.5em; border-bottom: 1px solid #eee; padding-bottom: 0.3em; }}
                    h3 {{ font-size: 1.25em; }}
                    code {{
                        background-color: #f4f4f4;
                        padding: 2px 6px;
                        border-radius: 3px;
                        font-family: "Consolas", "Monaco", monospace;
                        font-size: 0.9em;
                    }}
                    pre {{
                        background-color: #f4f4f4;
                        padding: 16px;
                        border-radius: 6px;
                        overflow-x: auto;
                    }}
                    pre code {{
                        background-color: transparent;
                        padding: 0;
                    }}
                    blockquote {{
                        border-left: 4px solid #ddd;
                        padding-left: 16px;
                        margin-left: 0;
                        color: #666;
                    }}
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                        margin-bottom: 16px;
                    }}
                    th, td {{
                        border: 1px solid #ddd;
                        padding: 8px;
                        text-align: left;
                    }}
                    th {{
                        background-color: #f4f4f4;
                        font-weight: bold;
                    }}
                    a {{
                        color: #0366d6;
                        text-decoration: none;
                    }}
                    a:hover {{
                        text-decoration: underline;
                    }}
                    img {{
                        max-width: 100%;
                        height: auto;
                    }}
                </style>
                </head>
                <body>
                {html_content}
                </body>
                </html>
                """
                
                # 使用QTextEdit显示HTML
                text_edit = QTextEdit()
                text_edit.setHtml(html_with_style)
                text_edit.setReadOnly(True)
                text_edit.setOpenExternalLinks(True)
                layout.addWidget(text_edit)
                
            except ImportError:
                # 如果markdown库不可用，显示原始文本
                text_edit = QTextEdit()
                text_edit.setPlainText(md_content)
                text_edit.setReadOnly(True)
                layout.addWidget(text_edit)
                
                # 添加提示标签
                tip_label = QLabel("提示：安装markdown库可获得更好的渲染效果\npip install markdown")
                tip_label.setStyleSheet("color: #666; font-size: 12px; padding: 10px;")
                layout.addWidget(tip_label)
        
        except Exception as e:
            error_label = QLabel(f"无法预览Markdown文件: {str(e)}")
            error_label.setStyleSheet("color: red; padding: 20px;")
            layout.addWidget(error_label)
        
        return widget

class CodeHighlightPreviewHandler(PreviewHandler):
    """
    代码文件预览处理器（带语法高亮）
    支持多种编程语言的语法高亮
    """
    
    def __init__(self):
        """初始化代码高亮预览器"""
        # 先定义language_map，再调用父类__init__
        self.language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.jsx': 'JavaScript (React)',
            '.tsx': 'TypeScript (React)',
            '.java': 'Java',
            '.c': 'C',
            '.cpp': 'C++',
            '.h': 'C Header',
            '.hpp': 'C++ Header',
            '.cs': 'C#',
            '.go': 'Go',
            '.rs': 'Rust',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.scala': 'Scala',
            '.lua': 'Lua',
            '.sql': 'SQL',
            '.sh': 'Shell',
            '.bash': 'Bash',
            '.ps1': 'PowerShell',
            '.html': 'HTML',
            '.htm': 'HTML',
            '.css': 'CSS',
            '.scss': 'SCSS',
            '.less': 'Less',
            '.xml': 'XML',
            '.json': 'JSON',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.toml': 'TOML',
            '.ini': 'INI',
            '.vue': 'Vue',
            '.svelte': 'Svelte',
        }
        # 然后调用父类初始化
        super().__init__()
    
    def _load_default_extensions(self) -> None:
        """加载默认扩展名"""
        self._extensions = list(self.language_map.keys())
    
    def can_handle(self, file_path: str) -> bool:
        """检查是否为代码文件"""
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self._extensions
    
    def preview(self, file_path: str, parent_widget: QWidget) -> QWidget:
        """生成代码高亮预览"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        try:
            # 获取文件扩展名和语言
            _, ext = os.path.splitext(file_path)
            language = self.language_map.get(ext.lower(), 'Unknown')
            
            # 读取代码内容
            encoding = detect_file_encoding(file_path)

            
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                encoding = 'utf-8 (忽略错误)'
            
            # 创建代码编辑器
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            
            # 尝试使用pygments进行语法高亮
            try:
                from pygments import highlight
                from pygments.lexers import get_lexer_by_name, guess_lexer_for_filename
                from pygments.formatters import HtmlFormatter
                
                # 获取合适的lexer
                try:
                    lexer = guess_lexer_for_filename(file_path, content)
                except Exception:
                    # 根据扩展名选择lexer
                    lexer_name_map = {
                        '.py': 'python',
                        '.js': 'javascript',
                        '.ts': 'typescript',
                        '.java': 'java',
                        '.c': 'c',
                        '.cpp': 'cpp',
                        '.cs': 'csharp',
                        '.go': 'go',
                        '.rs': 'rust',
                        '.rb': 'ruby',
                        '.php': 'php',
                        '.swift': 'swift',
                        '.kt': 'kotlin',
                        '.sql': 'sql',
                        '.html': 'html',
                        '.css': 'css',
                        '.xml': 'xml',
                        '.json': 'json',
                        '.yaml': 'yaml',
                        '.yml': 'yaml',
                    }
                    lexer_name = lexer_name_map.get(ext.lower(), 'text')
                    lexer = get_lexer_by_name(lexer_name)
                
                # 创建HTML格式化器
                formatter = HtmlFormatter(
                    style='colorful',
                    noclasses=True,
                    linenos=True,
                    cssstyles='font-family: "Consolas", "Monaco", monospace; font-size: 13px;'
                )
                
                # 生成高亮HTML
                highlighted_html = highlight(content, lexer, formatter)
                
                # 添加完整HTML结构
                html_with_style = f"""
                <html>
                <head>
                <style>
                    body {{
                        background-color: #f8f8f8;
                        margin: 0;
                        padding: 10px;
                    }}
                </style>
                </head>
                <body>
                {highlighted_html}
                </body>
                </html>
                """
                
                text_edit.setHtml(html_with_style)
                
            except ImportError:
                # 如果pygments不可用，使用普通文本显示
                text_edit.setPlainText(content)
                
                # 添加提示
                tip_label = QLabel("提示：安装pygments可获得语法高亮\npip install pygments")
                tip_label.setStyleSheet("color: #666; font-size: 12px; padding: 10px;")
                layout.addWidget(tip_label)
            
            layout.addWidget(text_edit)
            
            # 添加文件信息栏
            info_label = QLabel(f"语言: {language} | 编码: {encoding} | 大小: {len(content)} 字符")
            info_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px; background-color: #f0f0f0;")
            layout.addWidget(info_label)
        
        except Exception as e:
            error_label = QLabel(f"无法预览代码文件: {str(e)}")
            error_label.setStyleSheet("color: red; padding: 20px;")
            layout.addWidget(error_label)
        
        return widget

class ImagePreviewHandler(PreviewHandler):
    """
    图片文件预览处理器
    支持jpg、png、gif等图片文件
    """
    
    def __init__(self):
        """
        初始化图片预览处理器，添加图片缓存管理
        """
        super().__init__()
        # 图片缓存，使用LRU策略
        self.image_cache = {}
        self.cache_size = 0
        self.max_cache_size = config_manager.get("preview.image_cache_size", 100) * 1024 * 1024  # 默认100MB
        self.max_cache_count = 50  # 最大缓存图片数量
    
    def _load_default_extensions(self) -> None:
        """加载默认扩展名"""
        self._extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg',
            '.webp', '.ico', '.tiff', '.tif'
        ]
    
    def can_handle(self, file_path: str) -> bool:
        """
        检查是否为图片文件
        """
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self._extensions
    
    def _clean_cache(self):
        """
        清理图片缓存，使用LRU策略
        """
        # 按数量清理
        while len(self.image_cache) > self.max_cache_count:
            oldest_path = next(iter(self.image_cache))
            if oldest_path in self.image_cache:
                del self.image_cache[oldest_path]
                self.cache_size -= 1024 * 1024
        
        # 按大小清理
        while self.cache_size > self.max_cache_size and self.image_cache:
            # 移除最早使用的图片
            oldest_path = next(iter(self.image_cache))
            if oldest_path in self.image_cache:
                del self.image_cache[oldest_path]
                # 估算图片大小
                self.cache_size -= 1024 * 1024  # 假设每张图片平均1MB
    
    def preview(self, file_path: str, parent_widget: QWidget) -> QWidget:
        """
        生成图片文件预览
        """
        try:
            # 检查图片大小，避免加载过大的图片
            try:
                file_size = os.path.getsize(file_path)
            except (OSError, PermissionError):
                file_size = 0
            max_image_size = 50 * 1024 * 1024  # 50MB
            if file_size > max_image_size:
                widget = QWidget()
                layout = QVBoxLayout(widget)
                error_label = QLabel(f"无法预览图片: 文件过大（{file_size/1024/1024:.2f}MB）")
                error_label.setAlignment(Qt.AlignCenter)
                layout.addWidget(error_label)
                return widget
            
            # 检查缓存中是否已有此图片
            if file_path in self.image_cache:
                # 移动到缓存末尾，表示最近使用
                pixmap = self.image_cache.pop(file_path)
                self.image_cache[file_path] = pixmap
            else:
                # 加载图片
                pixmap = QPixmap(file_path)
                if pixmap.isNull():
                    raise Exception("无法加载图片")
                
                # 添加到缓存
                self.image_cache[file_path] = pixmap
                # 估算图片大小并更新缓存大小
                self.cache_size += file_size
                # 清理缓存
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

class DocumentPreviewHandler(PreviewHandler):
    """
    文档文件预览处理器
    支持doc/docx、xls/xlsx、ppt/pptx、pdf等文档文件
    """
    
    def _load_default_extensions(self) -> None:
        """加载默认扩展名"""
        self._extensions = [
            '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.pdf', '.wps', '.et', '.dps'
        ]
    
    def can_handle(self, file_path: str) -> bool:
        """
        检查是否为文档文件
        """
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self._extensions
    
    def preview(self, file_path: str, parent_widget: QWidget) -> QWidget:
        """
        生成文档文件预览
        对于doc/wps文件，调用wps系统控件API进行预览
        """
        self._parent_widget = parent_widget
        preview_widget = QWidget(parent_widget)
        layout = QVBoxLayout(preview_widget)
        
        # 获取文件信息
        file_name = os.path.basename(file_path)
        try:
            file_size = os.path.getsize(file_path)
        except (OSError, PermissionError):
            file_size = 0
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        # 创建信息标签
        info_label = QLabel(f"<h3>{file_name}</h3>")
        info_label.setAlignment(Qt.AlignCenter)
        
        details_layout = QVBoxLayout()
        details_layout.addWidget(QLabel(f"类型: {ext[1:].upper()}"))
        details_layout.addWidget(QLabel(f"大小: {file_size / 1024:.2f} KB"))
        
        # 根据文件类型实现不同的预览功能
        if ext in ['.doc', '.docx', '.wps']:
            self._setup_word_preview(file_path, layout, details_layout, parent_widget)
        elif ext in ['.xls', '.xlsx', '.et']:
            self._setup_excel_preview(file_path, layout, details_layout)
        elif ext in ['.ppt', '.pptx', '.dps']:
            self._setup_ppt_preview(file_path, layout, details_layout)
        elif ext in ['.pdf']:
            self._setup_pdf_preview(file_path, layout, details_layout)
        
        # 添加操作按钮
        button_layout = QHBoxLayout()
        open_btn = QPushButton("使用默认程序打开")
        open_btn.clicked.connect(lambda: self._open_file(file_path))
        

        
        button_layout.addWidget(open_btn)
        button_layout.addStretch()
        
        # 添加到主布局
        layout.addWidget(info_label)
        layout.addLayout(details_layout)
        layout.addLayout(button_layout)
        
        return preview_widget
    
    def _setup_word_preview(self, file_path: str, layout: QVBoxLayout, details_layout: QVBoxLayout, parent_widget: QWidget):
        """
        设置Word文档预览
        """
        from PySide6.QtWidgets import QLabel
        
        details_layout.addWidget(QLabel("预览: 支持分页预览、缩放、文本提取（可复制）"))
        
        # 添加预览特性说明
        features_label = QLabel("支持特性: 分页导航 | 缩放控制 | 文本搜索 | 内容复制")
        features_label.setStyleSheet("color: #0066cc")
        details_layout.addWidget(features_label)
        
        # 添加Word/WPS内容预览
        try:
            from PySide6.QtWidgets import QTextEdit, QScrollArea, QHBoxLayout, QPushButton, QLineEdit, QComboBox
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                error_label = QLabel(f"Word/WPS内容预览失败: 文件不存在")
                error_label.setStyleSheet("color: #ff0000")
                layout.addWidget(error_label)
                return
            
            # 检查文件是否可读
            if not os.access(file_path, os.R_OK):
                error_label = QLabel(f"Word/WPS内容预览失败: 无法读取文件")
                error_label.setStyleSheet("color: #ff0000")
                layout.addWidget(error_label)
                return
            
            # 检查文件大小
            try:
                file_size = os.path.getsize(file_path)
            except (OSError, PermissionError):
                file_size = 0
            if file_size > 50 * 1024 * 1024:  # 超过50MB
                error_label = QLabel(f"Word/WPS内容预览失败: 文件过大（{file_size/1024/1024:.2f}MB），无法预览")
                error_label.setStyleSheet("color: #ff0000")
                layout.addWidget(error_label)
                return
            
            # 创建滚动区域
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 设置大小策略
            
            # 创建文本编辑控件
            word_content = QTextEdit()
            word_content.setReadOnly(True)
            word_content.setLineWrapMode(QTextEdit.WidgetWidth)
            word_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 设置大小策略
            
            # 限制预览框宽度，使其不超过父窗口宽度
            if parent_widget:
                max_width = parent_widget.width() - 20  # 减去边距
                scroll_area.setMaximumWidth(max_width)
                word_content.setMaximumWidth(max_width)
            
            # 确保右键菜单启用，支持复制功能
            word_content.setContextMenuPolicy(Qt.DefaultContextMenu)
            
            # 获取文件扩展名
            _, ext = os.path.splitext(file_path.lower())
            
            # 尝试提取文档内容
            content = None
            paragraphs = []
            
            # 方法1：对于.doc和.wps文件，尝试使用pywin32调用WPS COM接口
            if ext in ['.doc', '.wps']:
                try:
                    import pythoncom
                    import win32com.client
                    
                    # 初始化COM
                    pythoncom.CoInitialize()
                    
                    # 统一使用WPS COM接口
                    wps_apps = [
                        {"name": "WPS", "prog_id": "Kwps.Application"}
                    ]
                    
                    content_found = False
                    
                    for app in wps_apps:
                        try:
                            logger.info(f"尝试使用{app['name']} COM接口打开文件: {file_path}")
                            # 创建应用程序对象
                            wps = win32com.client.Dispatch(app['prog_id'])
                            wps.Visible = False
                            wps.DisplayAlerts = False
                            
                            try:
                                # 尝试打开文件
                                doc = wps.Documents.Open(os.path.abspath(file_path), ReadOnly=True)
                                
                                try:
                                    # 读取文档内容
                                    content = doc.Content.Text
                                    # 分割内容为段落
                                    if content:
                                        paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
                                    content_found = True
                                    logger.info(f"{app['name']} COM接口读取成功: {file_path}")
                                    break
                                finally:
                                    # 关闭文档，无论是否成功读取内容
                                    try:
                                        doc.Close(SaveChanges=False)
                                    except Exception as e:
                                        logger.debug(f"关闭文档失败: {file_path}, 错误: {e}")
                            except Exception as e:
                                logger.warning(f"{app['name']}打开文件失败: {e}")
                                # 尝试以只读模式打开
                                try:
                                    doc = wps.Documents.Open(os.path.abspath(file_path), ConfirmConversions=False, ReadOnly=True)
                                    
                                    try:
                                        # 读取文档内容
                                        content = doc.Content.Text
                                        # 分割内容为段落
                                        if content:
                                            paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
                                        content_found = True
                                        logger.info(f"{app['name']} COM接口（只读模式）读取成功: {file_path}")
                                        break
                                    finally:
                                        # 关闭文档
                                        try:
                                            doc.Close(SaveChanges=False)
                                        except Exception as e:
                                            logger.debug(f"关闭文档失败: {file_path}, 错误: {e}")
                                except Exception as e:
                                    logger.debug(f"操作失败: {e}")
                            finally:
                                # 确保关闭应用程序
                                try:
                                    wps.Quit()
                                except Exception as e:
                                    logger.debug(f"退出{app['name']}应用程序失败: {e}")
                                    # 尝试直接终止进程（最后手段）
                                    try:
                                        wps._oleobj_.Invoke(419, 0, 1, 0)  # 419是Quit方法的调度ID
                                    except Exception as e2:
                                        logger.debug(f"强制退出{app['name']}应用程序失败: {e2}")
                        except Exception as e:
                            logger.warning(f"创建{app['name']}对象失败: {e}")
                            continue
                    
                except ImportError:
                    logger.warning("pywin32库未安装，无法使用COM接口")
                except Exception as e:
                    logger.warning(f"COM接口调用失败: {e}")
                finally:
                    # 释放COM资源
                    try:
                        pythoncom.CoUninitialize()
                    except Exception as e:
                        logger.debug(f"释放COM资源失败: {e}")
                # 注意：即使COM接口调用失败，也会继续尝试其他方法
            
            # 方法2：尝试使用python-docx读取.docx文件
            if not content and ext in ['.docx']:
                try:
                    from docx import Document
                    
                    try:
                        doc = Document(file_path)
                        paragraphs = [para.text.strip() for para in doc.paragraphs if para.text.strip()]
                        logger.info(f"python-docx读取成功: {file_path}")
                    except Exception as doc_error:
                        logger.warning(f"python-docx解析失败: {file_path}, 错误: {doc_error}")
                except ImportError:
                    logger.warning("python-docx库未安装")
            
            # 方法3：尝试使用docx2txt作为备选
            if not paragraphs:
                try:
                    import docx2txt
                    content = docx2txt.process(file_path)
                    if content:
                        paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
                    logger.info(f"docx2txt读取成功: {file_path}")
                except ImportError:
                    logger.warning("docx2txt库未安装")
                except Exception as e:
                    logger.warning(f"docx2txt解析失败: {e}")
            
            # 如果成功提取内容，显示内容
            if paragraphs:
                total_paragraphs = len(paragraphs)
                
                # 分页设置
                paragraphs_per_page = 10
                total_pages = (total_paragraphs + paragraphs_per_page - 1) // paragraphs_per_page
                
                # 初始显示第一页
                current_page = 1
                
                def show_page(page_num):
                    start_idx = (page_num - 1) * paragraphs_per_page
                    end_idx = min(start_idx + paragraphs_per_page, total_paragraphs)
                    
                    text = f"Word/WPS文档内容 (第 {page_num}/{total_pages} 页)\n\n"
                    for i in range(start_idx, end_idx):
                        para_text = paragraphs[i]
                        if para_text:
                            text += f"{para_text}\n\n"
                    
                    word_content.setPlainText(text)
                
                show_page(current_page)
                
                scroll_area.setWidget(word_content)
                layout.addWidget(scroll_area, 1)
                
                # 添加Word控制功能
                # 创建垂直布局，包含两行控件
                control_vertical_layout = QVBoxLayout()
                control_vertical_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
                control_vertical_layout.setSpacing(10)  # 设置行间距
                
                # 计算最大宽度
                max_control_width = parent_widget.width() - 20 if parent_widget else 500
                
                # 第一行：页码导航和缩放控制
                first_row_layout = QHBoxLayout()
                first_row_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
                first_row_layout.setSpacing(20)  # 设置控件间距
                
                # 分页导航
                page_layout = QHBoxLayout()
                page_layout.setContentsMargins(0, 0, 0, 0)
                page_layout.setSpacing(5)
                page_label = QLabel("页码:")
                page_label.setFixedWidth(35)  # 固定标签宽度
                page_layout.addWidget(page_label)
                page_combo = QComboBox()
                for i in range(1, total_pages + 1):
                    page_combo.addItem(str(i))
                page_combo.setMaximumWidth(60)  # 限制页码下拉框宽度，仅显示3位数字
                page_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)  # 根据内容调整大小
                page_layout.addWidget(page_combo)
                first_row_layout.addLayout(page_layout)
                
                # 缩放控制
                zoom_layout = QHBoxLayout()
                zoom_layout.setContentsMargins(0, 0, 0, 0)
                zoom_layout.setSpacing(5)
                zoom_label = QLabel("缩放:")
                zoom_label.setFixedWidth(35)  # 固定标签宽度
                zoom_layout.addWidget(zoom_label)
                zoom_combo = QComboBox()
                zoom_combo.addItems(["50%", "75%", "100%", "125%", "150%", "200%"])
                zoom_combo.setCurrentText("100%")
                zoom_combo.setMaximumWidth(60)  # 限制缩放下拉框宽度，仅显示"100%"宽度
                zoom_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)  # 根据内容调整大小
                zoom_layout.addWidget(zoom_combo)
                first_row_layout.addLayout(zoom_layout)
                
                # 添加拉伸因子到末尾，确保控件靠左对齐
                first_row_layout.addStretch(1)
                
                # 第二行：文本搜索（靠左显示）
                second_row_layout = QHBoxLayout()
                second_row_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
                
                # 文本搜索
                search_layout = QHBoxLayout()
                search_layout.setContentsMargins(0, 0, 0, 0)
                search_layout.setSpacing(5)         
                search_label = QLabel("搜索:")
                search_label.setFixedWidth(35)  # 固定标签宽度
                search_layout.addWidget(search_label)
                search_input = QLineEdit()
                search_input.setPlaceholderText("输入搜索内容")
                # 动态计算搜索输入框宽度
                search_input_width = max(150, min(200, max_control_width - 100))  # 最小150px，最大200px
                search_input.setMaximumWidth(search_input_width)
                search_input.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)  # 设置大小策略
                search_btn = QPushButton("搜索")
                search_btn.setMaximumWidth(45)  # 限制搜索按钮宽度，仅需要3个中文汉字宽度
                search_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # 设置大小策略
                search_layout.addWidget(search_input)
                search_layout.addWidget(search_btn)
                second_row_layout.addLayout(search_layout)
                
                # 添加拉伸因子到末尾，确保控件靠左对齐
                second_row_layout.addStretch(1)
                
                # 将两行添加到垂直布局
                control_vertical_layout.addLayout(first_row_layout)
                control_vertical_layout.addLayout(second_row_layout)
                
                # 限制整个控制布局的宽度
                control_widget = QWidget()
                control_widget.setMaximumWidth(max_control_width)
                control_widget.setLayout(control_vertical_layout)
                
                # 添加到主布局
                control_wrapper = QHBoxLayout()
                control_wrapper.addWidget(control_widget)
                control_wrapper.addStretch(1)
                layout.addLayout(control_wrapper)
                
                # 实现搜索功能
                def search_word():
                    search_text = search_input.text().strip()
                    if not search_text:
                        return
                    
                    # 搜索Word内容
                    results = []
                    for i, para in enumerate(paragraphs):
                        if para and search_text.lower() in para.lower():
                            results.append((i + 1, para))
                    
                    # 显示搜索结果
                    if results:
                        # 重建完整文档内容，用于高亮显示
                        full_content = "\n".join(paragraphs)
                        
                        # 重新显示搜索结果信息
                        result_text = f"搜索结果: 找到 {len(results)} 个匹配项\n\n"
                        for para_num, para_text in results:
                            result_text += f"段落 {para_num}:\n{para_text}\n\n"
                        # 在文本开头添加搜索结果信息
                        final_content = result_text + "\n" + full_content
                        word_content.setPlainText(final_content)
                        
                        # 高亮显示所有匹配的关键字
                        # 创建新的光标对象
                        cursor = word_content.textCursor()
                        word_content.moveCursor(cursor.Start)
                        
                        # 清除之前的高亮
                        cursor.clearSelection()
                        word_content.setTextCursor(cursor)
                        
                        # 查找并高亮第一个匹配项
                        found = word_content.find(search_text)
                        if found:
                            # 聚焦到找到的文本
                            word_content.ensureCursorVisible()
                            
                            # 高亮显示所有其他匹配项
                            while word_content.find(search_text):
                                pass
                    else:
                        word_content.setPlainText("未找到匹配内容")
                
                # 实现页码切换功能
                def switch_page():
                    page_num = int(page_combo.currentText())
                    show_page(page_num)
                
                page_combo.currentIndexChanged.connect(switch_page)
                
                # 实现缩放功能
                def change_zoom():
                    zoom_level = zoom_combo.currentText()
                    zoom = int(zoom_level.replace("%", "")) / 100
                    word_content.setFontPointSize(10 * zoom)
                
                zoom_combo.currentIndexChanged.connect(change_zoom)
                
                # 连接搜索按钮点击事件
                search_btn.clicked.connect(search_word)
                
                return
            
            # 备选方案：尝试以二进制方式读取文件信息
            try:
                text = f"Word/WPS文档信息:\n\n"
                text += f"文件路径: {file_path}\n"
                text += f"文件大小: {file_size/1024:.2f} KB\n"
                text += f"文件格式: {ext[1:].upper()}\n"
                text += "\n提示: 无法解析此文档，可能是格式不兼容或文件损坏。\n"
                text += "请尝试使用WPS或Microsoft Word打开此文件。\n"
                text += "\n建议：\n"
                text += "1. 确保系统已安装WPS Office或Microsoft Office\n"

                
                word_content.setPlainText(text)
                scroll_area.setWidget(word_content)
                layout.addWidget(scroll_area, 1)
                
                # 添加基本控制
                # 创建垂直布局，包含两行控件
                control_vertical_layout = QVBoxLayout()
                control_vertical_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
                control_vertical_layout.setSpacing(10)  # 设置行间距
                
                # 计算最大宽度
                max_control_width = parent_widget.width() - 20 if parent_widget else 500
                
                # 第一行：页码导航和缩放控制
                first_row_layout = QHBoxLayout()
                first_row_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
                first_row_layout.setSpacing(20)  # 设置控件间距
                
                # 分页导航（即使在备选方案中也添加，保持界面一致性）
                page_layout = QHBoxLayout()
                page_layout.setContentsMargins(0, 0, 0, 0)
                page_layout.setSpacing(5)
                page_label = QLabel("页码:")
                page_label.setFixedWidth(35)  # 固定标签宽度
                page_layout.addWidget(page_label)
                page_combo = QComboBox()
                page_combo.addItem("1")  # 默认只有一页
                page_combo.setMaximumWidth(60)  # 限制页码下拉框宽度，仅显示3位数字
                page_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)  # 根据内容调整大小
                page_layout.addWidget(page_combo)
                first_row_layout.addLayout(page_layout)
                
                # 缩放控制
                zoom_layout = QHBoxLayout()
                zoom_layout.setContentsMargins(0, 0, 0, 0)
                zoom_layout.setSpacing(5)
                zoom_label = QLabel("缩放:")
                zoom_label.setFixedWidth(35)  # 固定标签宽度
                zoom_layout.addWidget(zoom_label)
                zoom_combo = QComboBox()
                zoom_combo.addItems(["50%", "75%", "100%", "125%", "150%", "200%"])
                zoom_combo.setCurrentText("100%")
                zoom_combo.setMaximumWidth(60)  # 限制缩放下拉框宽度，仅显示"100%"宽度
                zoom_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)  # 根据内容调整大小
                zoom_layout.addWidget(zoom_combo)
                first_row_layout.addLayout(zoom_layout)
                
                # 添加拉伸因子到末尾，确保控件靠左对齐
                first_row_layout.addStretch(1)
                
                # 第二行：文本搜索（靠左显示）
                second_row_layout = QHBoxLayout()
                second_row_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
                
                # 文本搜索（即使在备选方案中也添加，保持界面一致性）
                search_layout = QHBoxLayout()
                search_layout.setContentsMargins(0, 0, 0, 0)
                search_layout.setSpacing(5)
                search_label = QLabel("搜索:")
                search_label.setFixedWidth(35)  # 固定标签宽度
                search_layout.addWidget(search_label)
                search_input = QLineEdit()
                search_input.setPlaceholderText("输入搜索内容")
                # 动态计算搜索输入框宽度
                search_input_width = max(150, min(200, max_control_width - 100))  # 最小150px，最大200px
                search_input.setMaximumWidth(search_input_width)
                search_input.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)  # 设置大小策略
                search_btn = QPushButton("搜索")
                search_btn.setMaximumWidth(45)  # 限制搜索按钮宽度，仅需要3个中文汉字宽度
                search_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # 设置大小策略
                search_layout.addWidget(search_input)
                search_layout.addWidget(search_btn)
                second_row_layout.addLayout(search_layout)
                
                # 添加拉伸因子到末尾，确保控件靠左对齐
                second_row_layout.addStretch(1)
                
                # 将两行添加到垂直布局
                control_vertical_layout.addLayout(first_row_layout)
                control_vertical_layout.addLayout(second_row_layout)
                
                # 限制整个控制布局的宽度
                control_widget = QWidget()
                control_widget.setMaximumWidth(max_control_width)
                control_widget.setLayout(control_vertical_layout)
                
                # 添加到主布局
                control_wrapper = QHBoxLayout()
                control_wrapper.addWidget(control_widget)
                control_wrapper.addStretch(1)
                layout.addLayout(control_wrapper)
                
                # 实现页码切换功能（备选方案中简单实现）
                def switch_page():
                    # 在备选方案中，页码切换功能简单处理
                    pass
                
                page_combo.currentIndexChanged.connect(switch_page)
                
                # 实现搜索功能（备选方案中简单实现）
                def search_word():
                    # 在备选方案中，搜索功能简单处理
                    search_text = search_input.text().strip()
                    if search_text:
                        word_content.setPlainText(f"搜索: {search_text}\n\n(在备选方案中，搜索功能不可用)")
                    else:
                        word_content.setPlainText(text)
                
                search_btn.clicked.connect(search_word)
                
                # 实现缩放功能
                def change_zoom():
                    zoom_level = zoom_combo.currentText()
                    zoom = int(zoom_level.replace("%", "")) / 100
                    word_content.setFontPointSize(10 * zoom)
                
                zoom_combo.currentIndexChanged.connect(change_zoom)
                
                return
                
            except Exception as alt_error:
                logger.error(f"备选方案失败: {file_path}, 错误: {alt_error}")
                # 备选方案也失败
                error_label = QLabel(f"Word/WPS内容预览失败: 无法解析文档")
                error_label.setStyleSheet("color: #ff0000")
                layout.addWidget(error_label)
                return
            
        except Exception as e:
            logger.error(f"Word/WPS预览失败: {file_path}, 错误: {e}")
            # 如果Word/WPS读取失败，添加错误提示
            error_label = QLabel(f"Word/WPS内容预览失败: {str(e)}")
            error_label.setStyleSheet("color: #ff0000")
            layout.addWidget(error_label)
    
    def _setup_excel_preview(self, file_path: str, layout: QVBoxLayout, details_layout: QVBoxLayout):
        """
        设置Excel文档预览
        """
        from PySide6.QtWidgets import QLabel
        
        details_layout.addWidget(QLabel("预览: 支持表格内容预览、工作表切换"))
        
        # 添加预览特性说明
        features_label = QLabel("支持特性: 工作表切换 | 单元格查看 | 数据筛选 | 内容复制")
        features_label.setStyleSheet("color: #0066cc")
        details_layout.addWidget(features_label)
        
        # 添加Excel/ET内容预览
        try:
            from PySide6.QtWidgets import QTextEdit, QScrollArea, QHBoxLayout, QPushButton, QLineEdit, QComboBox
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                error_label = QLabel(f"Excel/ET内容预览失败: 文件不存在")
                error_label.setStyleSheet("color: #ff0000")
                layout.addWidget(error_label)
                return
            
            # 检查文件是否可读
            if not os.access(file_path, os.R_OK):
                error_label = QLabel(f"Excel/ET内容预览失败: 无法读取文件")
                error_label.setStyleSheet("color: #ff0000")
                layout.addWidget(error_label)
                return
            
            # 检查文件大小
            try:
                file_size = os.path.getsize(file_path)
            except (OSError, PermissionError):
                file_size = 0
            if file_size > 50 * 1024 * 1024:  # 超过50MB
                error_label = QLabel(f"Excel/ET内容预览失败: 文件过大（{file_size/1024/1024:.2f}MB），无法预览")
                error_label.setStyleSheet("color: #ff0000")
                layout.addWidget(error_label)
                return
            
            # 创建滚动区域
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            
            # 创建文本编辑控件
            excel_content = QTextEdit()
            excel_content.setReadOnly(True)
            excel_content.setLineWrapMode(QTextEdit.WidgetWidth)
            
            # 确保右键菜单启用，支持复制功能
            excel_content.setContextMenuPolicy(Qt.DefaultContextMenu)
            
            # 获取文件扩展名
            _, ext = os.path.splitext(file_path.lower())
            
            # 尝试提取表格数据
            sheets_data = None
            wb = None
            
            # 方法1：对于.et文件，优先使用pywin32调用WPS COM接口
            if ext == '.et':
                try:
                    import pythoncom
                    import win32com.client
                    
                    # 初始化COM
                    pythoncom.CoInitialize()
                    
                    # 统一使用WPS COM接口
                    wps_apps = [
                        {"name": "WPS表格", "prog_id": "KET.Application"},
                        {"name": "WPS表格", "prog_id": "KWPS.Application"}  # 兼容旧版WPS
                    ]
                    
                    content_found = False
                    
                    for app in wps_apps:
                        try:
                            logger.info(f"尝试使用{app['name']} COM接口打开.et文件: {file_path}")
                            # 创建应用程序对象
                            wps = win32com.client.Dispatch(app['prog_id'])
                            wps.Visible = False
                            wps.DisplayAlerts = False
                            
                            try:
                                # 尝试打开文件
                                workbook = wps.Workbooks.Open(os.path.abspath(file_path), ReadOnly=True)
                                
                                try:
                                    # 提取工作表数据
                                    sheets_data = {}
                                    for sheet_idx in range(workbook.Sheets.Count):
                                        sheet = workbook.Sheets(sheet_idx + 1)
                                        sheet_name = sheet.Name
                                        
                                        # 获取使用范围
                                        used_range = sheet.UsedRange
                                        max_row = min(used_range.Rows.Count, 20)  # 最多显示前20行
                                        max_col = min(used_range.Columns.Count, 10)  # 最多显示前10列
                                        
                                        # 读取数据
                                        data = []
                                        # 读取表头
                                        header_row = []
                                        for col in range(1, max_col + 1):
                                            cell_value = sheet.Cells(1, col).Value
                                            header_row.append(str(cell_value) if cell_value is not None else "")
                                        if header_row:
                                            data.append(header_row)
                                        
                                        # 读取数据行
                                        for row in range(2, max_row + 1):
                                            row_data = []
                                            for col in range(1, max_col + 1):
                                                cell_value = sheet.Cells(row, col).Value
                                                row_data.append(str(cell_value) if cell_value is not None else "")
                                            data.append(row_data)
                                        
                                        if data:
                                            sheets_data[sheet_name] = data
                                    
                                    content_found = True
                                    logger.info(f"{app['name']} COM接口读取成功: {file_path}")
                                    break
                                finally:
                                    # 关闭工作簿，无论是否成功读取内容
                                    try:
                                        workbook.Close(SaveChanges=False)
                                    except Exception as e:
                                        logger.debug(f"关闭工作簿失败: {file_path}, 错误: {e}")
                            except Exception as e:
                                logger.warning(f"{app['name']}打开文件失败: {e}")
                                # 尝试以只读模式打开
                                try:
                                    workbook = wps.Workbooks.Open(os.path.abspath(file_path), ConfirmConversions=False, ReadOnly=True)
                                    
                                    try:
                                        # 提取工作表数据
                                        sheets_data = {}
                                        for sheet_idx in range(workbook.Sheets.Count):
                                            sheet = workbook.Sheets(sheet_idx + 1)
                                            sheet_name = sheet.Name
                                            
                                            # 获取使用范围
                                            used_range = sheet.UsedRange
                                            max_row = min(used_range.Rows.Count, 20)
                                            max_col = min(used_range.Columns.Count, 10)
                                            
                                            # 读取数据
                                            data = []
                                            # 读取表头
                                            header_row = []
                                            for col in range(1, max_col + 1):
                                                cell_value = sheet.Cells(1, col).Value
                                                header_row.append(str(cell_value) if cell_value is not None else "")
                                            if header_row:
                                                data.append(header_row)
                                            
                                            # 读取数据行
                                            for row in range(2, max_row + 1):
                                                row_data = []
                                                for col in range(1, max_col + 1):
                                                    cell_value = sheet.Cells(row, col).Value
                                                    row_data.append(str(cell_value) if cell_value is not None else "")
                                                data.append(row_data)
                                            
                                            if data:
                                                sheets_data[sheet_name] = data
                                        
                                        content_found = True
                                        logger.info(f"{app['name']} COM接口（只读模式）读取成功: {file_path}")
                                        break
                                    finally:
                                        # 关闭工作簿
                                        try:
                                            workbook.Close(SaveChanges=False)
                                        except Exception as e:
                                            logger.debug(f"关闭工作簿失败: {file_path}, 错误: {e}")
                                except Exception as e:
                                    logger.debug(f"操作失败: {e}")
                            finally:
                                # 确保关闭应用程序
                                try:
                                    wps.Quit()
                                except Exception as e:
                                    logger.debug(f"退出{app['name']}应用程序失败: {e}")
                                    # 尝试直接终止进程（最后手段）
                                    try:
                                        wps._oleobj_.Invoke(419, 0, 1, 0)  # 419是Quit方法的调度ID
                                    except Exception as e2:
                                        logger.debug(f"强制退出{app['name']}应用程序失败: {e2}")
                        except Exception as e:
                            logger.warning(f"创建{app['name']}对象失败: {e}")
                            continue
                    
                except ImportError:
                    logger.warning("pywin32库未安装，无法使用COM接口")
                except Exception as e:
                    logger.warning(f"COM接口调用失败: {e}")
                finally:
                    # 释放COM资源
                    try:
                        pythoncom.CoUninitialize()
                    except Exception as e:
                        logger.debug(f"释放COM资源失败: {e}")
                # 注意：即使COM接口调用失败，也会继续尝试其他方法
            
            # 方法2：尝试使用openpyxl读取（适用于.xlsx和新版.et文件）
            if not sheets_data:
                try:
                    from openpyxl import load_workbook
                    
                    wb = load_workbook(filename=file_path, read_only=True)
                    sheets = wb.sheetnames
                    
                    # 提取工作表数据
                    sheets_data = {}
                    for sheet_name in sheets:
                        ws = wb[sheet_name]
                        
                        # 读取前几行数据
                        max_rows = min(ws.max_row, 20)  # 最多显示前20行
                        max_cols = min(ws.max_column, 10)  # 最多显示前10列
                        
                        # 读取数据
                        data = []
                        # 读取表头
                        header_row = []
                        for col in range(1, max_cols + 1):
                            cell_value = ws.cell(row=1, column=col).value
                            header_row.append(str(cell_value) if cell_value is not None else "")
                        if header_row:
                            data.append(header_row)
                        
                        # 读取数据行
                        for row in range(2, max_rows + 1):
                            row_data = []
                            for col in range(1, max_cols + 1):
                                cell_value = ws.cell(row=row, column=col).value
                                row_data.append(str(cell_value) if cell_value is not None else "")
                            data.append(row_data)
                        
                        if data:
                            sheets_data[sheet_name] = data
                    
                    logger.info(f"openpyxl读取成功: {file_path}")
                except ImportError:
                    logger.warning("openpyxl库未安装")
                except Exception as e:
                    logger.warning(f"openpyxl解析失败: {e}")
            
            # 方法3：尝试使用xlrd读取（适用于.xls和老版.et文件）
            if not sheets_data:
                try:
                    import xlrd
                    
                    workbook = xlrd.open_workbook(file_path)
                    
                    # 提取工作表数据
                    sheets_data = {}
                    for sheet_idx in range(workbook.nsheets):
                        sheet = workbook.sheet_by_index(sheet_idx)
                        sheet_name = sheet.name
                        
                        # 读取前几行数据
                        max_rows = min(sheet.nrows, 20)  # 最多显示前20行
                        max_cols = min(sheet.ncols, 10)  # 最多显示前10列
                        
                        # 读取数据
                        data = []
                        # 读取表头
                        if sheet.nrows > 0:
                            header_row = []
                            for col in range(min(sheet.ncols, max_cols)):
                                cell_value = sheet.cell_value(0, col)
                                header_row.append(str(cell_value) if cell_value is not None else "")
                            if header_row:
                                data.append(header_row)
                        
                        # 读取数据行
                        for row in range(1, max_rows):
                            row_data = []
                            for col in range(min(sheet.ncols, max_cols)):
                                cell_value = sheet.cell_value(row, col)
                                row_data.append(str(cell_value) if cell_value is not None else "")
                            data.append(row_data)
                        
                        if data:
                            sheets_data[sheet_name] = data
                    
                    logger.info(f"xlrd读取成功: {file_path}")
                except ImportError:
                    logger.warning("xlrd库未安装")
                except Exception as e:
                    logger.warning(f"xlrd解析失败: {e}")
            
            # 如果成功提取数据，显示内容
            if sheets_data:
                sheets = list(sheets_data.keys())
                total_sheets = len(sheets)
                
                # 初始显示第一个工作表
                current_sheet = sheets[0] if sheets else None
                
                def show_sheet(sheet_name):
                    if not sheet_name or sheet_name not in sheets_data:
                        return
                    
                    data = sheets_data[sheet_name]
                    
                    text = f"Excel/ET文档内容 (工作表: {sheet_name})\n\n"
                    
                    if data:
                        # 显示表头
                        if len(data) > 0:
                            header_row = data[0]
                            text += "\t".join(header_row) + "\n"
                            text += "\t".join(["-" * len(h) for h in header_row]) + "\n"
                        
                        # 显示数据行
                        for row in data[1:]:
                            text += "\t".join(row) + "\n"
                        
                        if len(data) == 1:
                            text += "(无数据行)"
                    else:
                        text += "(无数据)"
                    
                    excel_content.setPlainText(text)
                
                if current_sheet:
                    show_sheet(current_sheet)
                
                scroll_area.setWidget(excel_content)
                layout.addWidget(scroll_area, 1)
                
                # 添加Excel控制功能
                control_layout = QHBoxLayout()
                
                # 工作表切换
                sheet_layout = QHBoxLayout()
                sheet_layout.addWidget(QLabel("工作表:"))
                sheet_combo = QComboBox()
                for sheet_name in sheets:
                    sheet_combo.addItem(sheet_name)
                sheet_combo.setMaximumWidth(150)  # 限制工作表下拉框宽度
                sheet_layout.addWidget(sheet_combo)
                control_layout.addLayout(sheet_layout)
                
                # 数据筛选
                filter_layout = QHBoxLayout()
                filter_layout.addWidget(QLabel("筛选:"))
                filter_input = QLineEdit()
                filter_input.setPlaceholderText("输入筛选内容")
                filter_input.setMaximumWidth(150)  # 限制筛选输入框宽度
                filter_btn = QPushButton("筛选")
                filter_btn.setMaximumWidth(60)  # 限制筛选按钮宽度
                filter_layout.addWidget(filter_input)
                filter_layout.addWidget(filter_btn)
                control_layout.addLayout(filter_layout)
                
                layout.addLayout(control_layout)
                
                # 实现工作表切换功能
                def switch_sheet():
                    sheet_name = sheet_combo.currentText()
                    show_sheet(sheet_name)
                
                sheet_combo.currentIndexChanged.connect(switch_sheet)
                
                # 实现数据筛选功能
                def filter_data():
                    filter_text = filter_input.text().strip()
                    if not filter_text:
                        return
                    
                    sheet_name = sheet_combo.currentText()
                    if sheet_name not in sheets_data:
                        return
                    
                    data = sheets_data[sheet_name]
                    
                    # 筛选数据
                    results = []
                    
                    # 检查是否有表头
                    has_header = len(data) > 0
                    header_row = data[0] if has_header else []
                    
                    # 筛选数据行
                    for row in data[1:]:  # 从第二行开始筛选
                        row_match = False
                        for cell_value in row:
                            if filter_text.lower() in cell_value.lower():
                                row_match = True
                                break
                        if row_match:
                            results.append(row)
                    
                    # 显示筛选结果
                    text = f"Excel/ET文档内容 (工作表: {sheet_name})\n\n"
                    text += f"筛选结果: 找到 {len(results)} 行匹配数据\n\n"
                    
                    if header_row:
                        text += "\t".join(header_row) + "\n"
                        text += "\t".join(["-" * len(h) for h in header_row]) + "\n"
                    
                    for row_data in results:
                        text += "\t".join(row_data) + "\n"
                    
                    if not results:
                        text += "未找到匹配数据"
                    
                    excel_content.setPlainText(text)
                
                filter_btn.clicked.connect(filter_data)
                
                return
            
            # 备选方案：尝试以二进制方式读取文件信息
            try:
                text = f"Excel/ET文档信息:\n\n"
                text += f"文件路径: {file_path}\n"
                text += f"文件大小: {file_size/1024:.2f} KB\n"
                text += f"文件格式: {ext[1:].upper()}\n"
                text += "\n提示: 无法解析此文档，可能是格式不兼容或文件损坏。\n"
                text += "请尝试使用WPS或Microsoft Excel打开此文件。\n"
                text += "\n建议：\n"
                text += "1. 确保系统已安装WPS Office或Microsoft Excel\n"
                
                excel_content.setPlainText(text)
                scroll_area.setWidget(excel_content)
                layout.addWidget(scroll_area, 1)
                
                return
                
            except Exception as alt_error:
                logger.error(f"备选方案失败: {file_path}, 错误: {alt_error}")
                # 备选方案也失败
                error_label = QLabel(f"Excel/ET内容预览失败: 无法解析文档")
                error_label.setStyleSheet("color: #ff0000")
                layout.addWidget(error_label)
                return
            
        except Exception as e:
            logger.error(f"Excel/ET预览失败: {file_path}, 错误: {e}")
            # 如果Excel/ET读取失败，添加错误提示
            error_label = QLabel(f"Excel/ET内容预览失败: {str(e)}")
            error_label.setStyleSheet("color: #ff0000")
            layout.addWidget(error_label)
    
    def _setup_ppt_preview(self, file_path: str, layout: QVBoxLayout, details_layout: QVBoxLayout):
        """
        设置PowerPoint文档预览
        """
        from PySide6.QtWidgets import QLabel
        
        details_layout.addWidget(QLabel("预览: 支持幻灯片预览、播放控制"))
        
        # 添加预览特性说明
        features_label = QLabel("支持特性: 幻灯片导航 | 播放控制 | 缩放查看 | 内容复制")
        features_label.setStyleSheet("color: #0066cc")
        details_layout.addWidget(features_label)
        
        # 添加PowerPoint/DPS内容预览
        try:
            from pptx import Presentation
            from PySide6.QtWidgets import QTextEdit, QScrollArea, QHBoxLayout, QPushButton, QLineEdit, QComboBox
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                error_label = QLabel(f"PowerPoint/DPS内容预览失败: 文件不存在")
                error_label.setStyleSheet("color: #ff0000")
                layout.addWidget(error_label)
                return
            
            # 检查文件是否可读
            if not os.access(file_path, os.R_OK):
                error_label = QLabel(f"PowerPoint/DPS内容预览失败: 无法读取文件")
                error_label.setStyleSheet("color: #ff0000")
                layout.addWidget(error_label)
                return
            
            # 创建滚动区域
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            
            # 创建文本编辑控件
            ppt_content = QTextEdit()
            ppt_content.setReadOnly(True)
            ppt_content.setLineWrapMode(QTextEdit.WidgetWidth)
            
            # 确保右键菜单启用，支持复制功能
            ppt_content.setContextMenuPolicy(Qt.DefaultContextMenu)
            
            # 读取PowerPoint/DPS文件内容
            prs = Presentation(file_path)
            slides = prs.slides
            total_slides = len(slides)
            
            # 初始显示第一张幻灯片
            current_slide = 1
            
            def show_slide(slide_num):
                if 1 <= slide_num <= total_slides:
                    slide = slides[slide_num - 1]
                    text = f"PowerPoint/DPS文档内容 (幻灯片: {slide_num}/{total_slides})\n\n"
                    
                    slide_has_content = False
                    for shape in slide.shapes:
                        if hasattr(shape, 'text'):
                            shape_text = shape.text.strip()
                            if shape_text:
                                text += f"  - {shape_text}\n"
                                slide_has_content = True
                    
                    if not slide_has_content:
                        text += "  (无文本内容)"
                    
                    ppt_content.setPlainText(text)
            
            if total_slides > 0:
                show_slide(current_slide)
            
            scroll_area.setWidget(ppt_content)
            layout.addWidget(scroll_area, 1)
            
            # 添加PowerPoint控制功能
            control_layout = QHBoxLayout()
            
            # 幻灯片导航
            slide_layout = QHBoxLayout()
            slide_layout.addWidget(QLabel("幻灯片:"))
            slide_combo = QComboBox()
            for i in range(1, total_slides + 1):
                slide_combo.addItem(str(i))
            slide_combo.setMaximumWidth(80)  # 限制幻灯片编号下拉框宽度
            slide_layout.addWidget(slide_combo)
            control_layout.addLayout(slide_layout)
            
            # 播放控制
            play_layout = QHBoxLayout()
            prev_btn = QPushButton("上一张")
            prev_btn.setMaximumWidth(80)  # 限制上一张按钮宽度
            play_btn = QPushButton("播放")
            play_btn.setMaximumWidth(60)  # 限制播放按钮宽度
            next_btn = QPushButton("下一张")
            next_btn.setMaximumWidth(80)  # 限制下一张按钮宽度
            play_layout.addWidget(prev_btn)
            play_layout.addWidget(play_btn)
            play_layout.addWidget(next_btn)
            control_layout.addLayout(play_layout)
            
            # 缩放控制
            zoom_layout = QHBoxLayout()
            zoom_layout.addWidget(QLabel("缩放:"))
            zoom_combo = QComboBox()
            zoom_combo.addItems(["50%", "75%", "100%", "125%", "150%", "200%"])
            zoom_combo.setCurrentText("100%")
            zoom_combo.setMaximumWidth(100)  # 限制缩放下拉框宽度
            zoom_layout.addWidget(zoom_combo)
            control_layout.addLayout(zoom_layout)
            
            layout.addLayout(control_layout)
            
            # 实现幻灯片切换功能
            def switch_slide():
                slide_num = int(slide_combo.currentText())
                show_slide(slide_num)
            
            slide_combo.currentIndexChanged.connect(switch_slide)
            
            # 实现上一张功能
            def prev_slide():
                current_idx = slide_combo.currentIndex()
                if current_idx > 0:
                    new_idx = current_idx - 1
                    slide_combo.setCurrentIndex(new_idx)
                    show_slide(new_idx + 1)
            
            prev_btn.clicked.connect(prev_slide)
            
            # 实现下一张功能
            def next_slide():
                current_idx = slide_combo.currentIndex()
                if current_idx < total_slides - 1:
                    new_idx = current_idx + 1
                    slide_combo.setCurrentIndex(new_idx)
                    show_slide(new_idx + 1)
            
            next_btn.clicked.connect(next_slide)
            
            # 实现播放功能
            def play_slideshow():
                # 这里实现简单的幻灯片播放功能
                # 实际项目中可以考虑使用更复杂的播放模式
                current_idx = slide_combo.currentIndex()
                
                def auto_play(idx):
                    if idx < total_slides:
                        show_slide(idx + 1)
                        slide_combo.setCurrentIndex(idx)
                        # 3秒后自动切换到下一张
                        from PySide6.QtCore import QTimer
                        QTimer.singleShot(3000, lambda: auto_play(idx + 1))
                
                auto_play(current_idx)
            
            play_btn.clicked.connect(play_slideshow)
            
            # 实现缩放功能
            def change_zoom():
                zoom_level = zoom_combo.currentText()
                zoom = int(zoom_level.replace("%", "")) / 100
                ppt_content.setFontPointSize(10 * zoom)
            
            zoom_combo.currentIndexChanged.connect(change_zoom)
            
        except ImportError:
            logger.warning("python-pptx库未安装，尝试使用COM接口预览PPT")
            try:
                import pythoncom
                import win32com.client
                from PySide6.QtWidgets import QTextEdit, QScrollArea
                
                pythoncom.CoInitialize()
                try:
                    ppt_apps = [
                        {"name": "WPS", "prog_id": "Kwpp.Application"},
                        {"name": "PowerPoint", "prog_id": "PowerPoint.Application"}
                    ]
                    content_found = False
                    for app in ppt_apps:
                        try:
                            ppt_app = win32com.client.Dispatch(app['prog_id'])
                            ppt_app.Visible = False
                            pres = ppt_app.Presentations.Open(os.path.abspath(file_path), ReadOnly=True)
                            try:
                                total_slides = pres.Slides.Count
                                paragraphs = []
                                for i in range(1, total_slides + 1):
                                    slide = pres.Slides(i)
                                    slide_text = f"幻灯片 {i}/{total_slides}:\n"
                                    for shape in slide.Shapes:
                                        if shape.HasTextFrame:
                                            slide_text += f"  {shape.TextFrame.TextRange.Text}\n"
                                    paragraphs.append(slide_text)
                                content_found = True
                                logger.info(f"{app['name']} COM接口读取PPT成功: {file_path}")
                                break
                            finally:
                                pres.Close()
                        except Exception as e:
                            logger.warning(f"{app['name']} COM接口打开PPT失败: {e}")
                            continue
                    if content_found and paragraphs:
                        scroll_area = QScrollArea()
                        scroll_area.setWidgetResizable(True)
                        ppt_content = QTextEdit()
                        ppt_content.setReadOnly(True)
                        ppt_content.setPlainText("\n\n".join(paragraphs))
                        scroll_area.setWidget(ppt_content)
                        layout.addWidget(scroll_area, 1)
                    else:
                        error_label = QLabel("PowerPoint/DPS内容预览失败: 无法通过COM接口读取文件")
                        error_label.setStyleSheet("color: #ff0000")
                        layout.addWidget(error_label)
                finally:
                    try:
                        pythoncom.CoUninitialize()
                    except Exception as e:
                        logger.debug(f"操作失败: {e}")
            except ImportError:
                logger.warning("pywin32库未安装，无法使用COM接口预览PPT")
                error_label = QLabel("PowerPoint/DPS内容预览失败: python-pptx和pywin32库均未安装")
                error_label.setStyleSheet("color: #ff0000")
                layout.addWidget(error_label)
            except Exception as e:
                logger.warning(f"COM接口预览PPT失败: {e}")
                error_label = QLabel(f"PowerPoint/DPS内容预览失败: {str(e)}")
                error_label.setStyleSheet("color: #ff0000")
                layout.addWidget(error_label)
        except Exception as e:
            logger.error(f"PowerPoint/DPS预览失败: {file_path}, 错误: {e}")
            # 如果PowerPoint/DPS读取失败，添加错误提示
            error_label = QLabel(f"PowerPoint/DPS内容预览失败: {str(e)}")
            error_label.setStyleSheet("color: #ff0000")
            layout.addWidget(error_label)
    
    def _setup_pdf_preview(self, file_path: str, layout: QVBoxLayout, details_layout: QVBoxLayout):
        """
        设置PDF文档预览
        """
        from PySide6.QtWidgets import QLabel
        
        details_layout.addWidget(QLabel("预览: 支持分页预览、缩放、文本提取"))
        
        # 添加预览特性说明
        features_label = QLabel("支持特性: 分页导航 | 缩放控制 | 文本搜索 | 大纲导航 | 内容复制")
        features_label.setStyleSheet("color: #0066cc")
        details_layout.addWidget(features_label)
        
        # 添加PDF内容预览
        try:
            import PyPDF2
            from PySide6.QtWidgets import QTextEdit, QScrollArea, QHBoxLayout, QPushButton, QLineEdit, QComboBox, QTreeWidget, QTreeWidgetItem, QSplitter
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                error_label = QLabel(f"PDF内容预览失败: 文件不存在")
                error_label.setStyleSheet("color: #ff0000")
                layout.addWidget(error_label)
                return
            
            # 检查文件是否可读
            if not os.access(file_path, os.R_OK):
                error_label = QLabel(f"PDF内容预览失败: 无法读取文件")
                error_label.setStyleSheet("color: #ff0000")
                layout.addWidget(error_label)
                return
            
            # 创建分割器，用于显示大纲和内容
            splitter = QSplitter(Qt.Horizontal)
            
            # 创建大纲树控件
            outline_tree = QTreeWidget()
            outline_tree.setHeaderLabel("PDF大纲")
            outline_tree.setMinimumWidth(200)
            
            # 创建滚动区域
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            
            # 创建文本编辑控件
            pdf_content = QTextEdit()
            pdf_content.setReadOnly(True)
            pdf_content.setLineWrapMode(QTextEdit.WidgetWidth)
            
            # 确保右键菜单启用，支持复制功能
            pdf_content.setContextMenuPolicy(Qt.DefaultContextMenu)
            
            # 读取PDF文件内容
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                num_pages = len(reader.pages)
                
                # 读取PDF大纲
                outline_items = []
                if hasattr(reader, 'outlines') and reader.outlines:
                    def add_outline_items(parent, outlines):
                        for outline in outlines:
                            if isinstance(outline, PyPDF2.generic.Destination):
                                # 处理单个大纲项
                                item = QTreeWidgetItem([outline.title])
                                item.setData(0, Qt.UserRole, outline.page.number + 1)  # 存储页码
                                parent.addChild(item)
                                outline_items.append((outline.title, outline.page.number + 1))
                            elif isinstance(outline, list):
                                # 处理大纲子列表
                                add_outline_items(parent, outline)
                    
                    add_outline_items(outline_tree.invisibleRootItem(), reader.outlines)
                else:
                    # 如果没有大纲，添加提示
                    no_outline_item = QTreeWidgetItem(["无大纲"])
                    outline_tree.invisibleRootItem().addChild(no_outline_item)
                
                # 初始显示第一页
                page = reader.pages[0]
                page_text = page.extract_text()
                if page_text:
                    pdf_content.setPlainText(f"第 1 页:\n{page_text}")
                else:
                    pdf_content.setPlainText("第 1 页: 无文本内容")
            
            scroll_area.setWidget(pdf_content)
            
            # 添加到分割器
            splitter.addWidget(outline_tree)
            splitter.addWidget(scroll_area)
            splitter.setStretchFactor(1, 1)  # 内容区域可拉伸
            
            layout.addWidget(splitter, 1)
            
            # 添加PDF控制功能
            control_layout = QHBoxLayout()
            
            # 分页导航
            page_layout = QHBoxLayout()
            page_layout.addWidget(QLabel("页码:"))
            page_combo = QComboBox()
            for i in range(1, num_pages + 1):
                page_combo.addItem(str(i))
            page_combo.setMaximumWidth(60)  # 限制页码下拉框宽度
            page_layout.addWidget(page_combo)
            control_layout.addLayout(page_layout)
            
            # 文本搜索
            search_layout = QHBoxLayout()
            search_layout.addWidget(QLabel("搜索:"))
            search_input = QLineEdit()
            search_input.setPlaceholderText("输入搜索内容")
            search_input.setMaximumWidth(150)  # 限制搜索输入框宽度
            search_btn = QPushButton("搜索")
            search_btn.setMaximumWidth(60)  # 限制搜索按钮宽度
            search_layout.addWidget(search_input)
            search_layout.addWidget(search_btn)
            control_layout.addLayout(search_layout)
            
            # 缩放控制
            zoom_layout = QHBoxLayout()
            zoom_layout.addWidget(QLabel("缩放:"))
            zoom_combo = QComboBox()
            zoom_combo.addItems(["50%", "75%", "100%", "125%", "150%", "200%"])
            zoom_combo.setCurrentText("100%")
            zoom_combo.setMaximumWidth(100)  # 限制缩放下拉框宽度
            zoom_layout.addWidget(zoom_combo)
            control_layout.addLayout(zoom_layout)
            
            layout.addLayout(control_layout)
            
            # 实现大纲点击功能
            def on_outline_clicked(item, column):
                page_num = item.data(0, Qt.UserRole)
                if page_num:
                    with open(file_path, 'rb') as file:
                        reader = PyPDF2.PdfReader(file)
                        if 1 <= page_num <= len(reader.pages):
                            page = reader.pages[page_num - 1]
                            page_text = page.extract_text()
                            if page_text:
                                pdf_content.setPlainText(f"第 {page_num} 页:\n{page_text}")
                            else:
                                pdf_content.setPlainText(f"第 {page_num} 页: 无文本内容")
                            # 更新页码下拉框
                            page_combo.setCurrentText(str(page_num))
            
            outline_tree.itemClicked.connect(on_outline_clicked)
            
            # 实现搜索功能
            def search_pdf():
                search_text = search_input.text().strip()
                if not search_text:
                    return
                
                # 搜索PDF内容
                results = []
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    for i in range(len(reader.pages)):
                        page = reader.pages[i]
                        page_text = page.extract_text()
                        if page_text and search_text.lower() in page_text.lower():
                            results.append((i + 1, page_text))
                
                # 显示搜索结果
                if results:
                    result_text = f"搜索结果: 找到 {len(results)} 个匹配项\n\n"
                    for page_num, page_text in results:
                        result_text += f"第 {page_num} 页:\n{page_text[:500]}...\n\n"  # 只显示前500个字符
                    pdf_content.setPlainText(result_text)
                else:
                    pdf_content.setPlainText("未找到匹配内容")
            
            search_btn.clicked.connect(search_pdf)
            
            # 实现页码切换功能
            def switch_page():
                page_num = int(page_combo.currentText()) - 1
                if 0 <= page_num < num_pages:
                    with open(file_path, 'rb') as file:
                        reader = PyPDF2.PdfReader(file)
                        page = reader.pages[page_num]
                        page_text = page.extract_text()
                        if page_text:
                            pdf_content.setPlainText(f"第 {page_num + 1} 页:\n{page_text}")
                        else:
                            pdf_content.setPlainText(f"第 {page_num + 1} 页: 无文本内容")
            
            page_combo.currentIndexChanged.connect(switch_page)
            
            # 实现缩放功能
            def change_zoom():
                zoom_level = zoom_combo.currentText()
                zoom = int(zoom_level.replace("%", "")) / 100
                pdf_content.setFontPointSize(10 * zoom)
            
            zoom_combo.currentIndexChanged.connect(change_zoom)
            
        except ImportError:
            logger.warning("PyPDF2库未安装，尝试使用pypdf备选库预览PDF")
            try:
                import pypdf
                from PySide6.QtWidgets import QTextEdit, QScrollArea
                
                scroll_area = QScrollArea()
                scroll_area.setWidgetResizable(True)
                pdf_content = QTextEdit()
                pdf_content.setReadOnly(True)
                pdf_content.setContextMenuPolicy(Qt.DefaultContextMenu)
                
                with open(file_path, 'rb') as file:
                    reader = pypdf.PdfReader(file)
                    total_pages = len(reader.pages)
                    all_text = ""
                    for page_num in range(total_pages):
                        page_text = reader.pages[page_num].extract_text()
                        if page_text:
                            all_text += f"第 {page_num + 1} 页:\n{page_text}\n\n"
                
                if all_text:
                    pdf_content.setPlainText(all_text)
                else:
                    pdf_content.setPlainText("PDF文件无文本内容")
                
                scroll_area.setWidget(pdf_content)
                layout.addWidget(scroll_area, 1)
                logger.info(f"pypdf备选库读取PDF成功: {file_path}")
            except ImportError:
                logger.warning("pypdf库也未安装，无法预览PDF")
                error_label = QLabel("PDF内容预览失败: PyPDF2和pypdf库均未安装")
                error_label.setStyleSheet("color: #ff0000")
                layout.addWidget(error_label)
            except Exception as e:
                logger.warning(f"pypdf备选库预览PDF失败: {e}")
                error_label = QLabel(f"PDF内容预览失败: {str(e)}")
                error_label.setStyleSheet("color: #ff0000")
                layout.addWidget(error_label)
        except Exception as e:
            logger.error(f"PDF预览失败: {file_path}, 错误: {e}")
            # 如果PDF读取失败，添加错误提示
            error_label = QLabel(f"PDF内容预览失败: {str(e)}")
            error_label.setStyleSheet("color: #ff0000")
            layout.addWidget(error_label)
    
    def _open_file(self, file_path: str) -> None:
        """
        使用默认程序打开文件
        """
        try:
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.name == 'posix':  # Linux/macOS
                import subprocess
                subprocess.call(['open', file_path])
            logger.info(f"已打开文件: {file_path}")
        except Exception as e:
            logger.error(f"打开文件失败: {file_path}, 错误: {e}")
            show_warning(self._parent_widget, "打开失败", f"无法打开文件: {e}")
    


class ArchivePreviewHandler(PreviewHandler):
    """
    压缩包预览处理器
    支持zip、7z、tar、rar、iso等压缩包文件
    """
    
    def _load_default_extensions(self) -> None:
        """加载默认扩展名"""
        self._extensions = [
            '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
            '.tar.gz', '.tar.bz2', '.tar.xz', '.iso'
        ]
    
    def can_handle(self, file_path: str) -> bool:
        """
        检查是否为压缩包文件
        """
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self._extensions
    
    def preview(self, file_path: str, parent_widget: QWidget) -> QWidget:
        """
        生成压缩包文件预览
        """
        self._parent_widget = parent_widget
        preview_widget = QWidget(parent_widget)
        layout = QVBoxLayout(preview_widget)
        
        # 创建提示信息
        info_label = QLabel(f"压缩包: {os.path.basename(file_path)}")
        try:
            try:
                size_label = QLabel(f"大小: {os.path.getsize(file_path) / (1024 * 1024):.2f} MB")
            except (OSError, PermissionError):
                pass
        except (OSError, PermissionError):
            pass
        
        # 创建文件列表视图
        tree_view = QTreeView()
        tree_view.setRootIsDecorated(True)
        tree_view.setHeaderHidden(False)
        
        # 创建模型
        from PySide6.QtGui import QStandardItemModel, QStandardItem
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["文件名", "大小"])
        
        # 尝试解析压缩包内容
        try:
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            
            # 根据扩展名选择解析方式
            if ext == '.zip':
                self._parse_zip(file_path, model)
            elif ext == '.7z':
                self._parse_7z(file_path, model)
            elif ext == '.rar':
                self._parse_rar(file_path, model)
            elif ext in ['.tar', '.tar.gz', '.tar.bz2', '.tar.xz', '.gz', '.bz2', '.xz']:
                self._parse_tar(file_path, model)
            elif ext == '.iso':
                self._parse_iso(file_path, model)
            else:
                error_label = QLabel("不支持的压缩格式")
                layout.addWidget(error_label)
                layout.addWidget(info_label)
                layout.addWidget(size_label)
                return preview_widget
            
            # 设置树视图的模型
            tree_view.setModel(model)
            # 调整列宽
            tree_view.resizeColumnToContents(0)
            tree_view.resizeColumnToContents(1)
            
            # 添加按钮
            button_layout = QHBoxLayout()
            extract_btn = QPushButton("解压到...")
            open_btn = QPushButton("打开")
            
            button_layout.addWidget(extract_btn)
            button_layout.addWidget(open_btn)
            button_layout.addStretch()
            
            # 添加到主布局
            layout.addWidget(info_label)
            layout.addWidget(size_label)
            layout.addWidget(tree_view, 1)
            layout.addLayout(button_layout)
        except Exception as e:
            logger.error(f"解析压缩包失败: {e}")
            error_label = QLabel(f"解析压缩包失败: {str(e)}")
            layout.addWidget(error_label)
            layout.addWidget(info_label)
            layout.addWidget(size_label)
            return preview_widget
        
        return preview_widget
    
    def _parse_zip(self, file_path: str, model):
        """解析ZIP文件"""
        import zipfile
        if zipfile.is_zipfile(file_path):
            with zipfile.ZipFile(file_path, 'r') as zf:
                file_list = zf.namelist()
                for file_name in file_list:
                    if file_name.endswith('/'):
                        continue
                    try:
                        info = zf.getinfo(file_name)
                        size = info.file_size
                        size_str = self._format_size(size)
                        item_name = QStandardItem(file_name)
                        item_size = QStandardItem(size_str)
                        model.appendRow([item_name, item_size])
                    except Exception as e:
                        logger.debug(f"操作失败: {e}")
                        item_name = QStandardItem(file_name)
                        item_size = QStandardItem("未知")
                        model.appendRow([item_name, item_size])
    
    def _parse_7z(self, file_path: str, model):
        """解析7z文件"""
        try:
            import py7zr
            with py7zr.SevenZipFile(file_path, 'r') as zf:
                for entry in zf.getnames():
                    if entry.endswith('/'):
                        continue
                    try:
                        info = zf.getinfo(entry)
                        size = info.uncompressed
                        size_str = self._format_size(size)
                        item_name = QStandardItem(entry)
                        item_size = QStandardItem(size_str)
                        model.appendRow([item_name, item_size])
                    except Exception as e:
                        logger.debug(f"操作失败: {e}")
                        item_name = QStandardItem(entry)
                        item_size = QStandardItem("未知")
                        model.appendRow([item_name, item_size])
        except ImportError:
            model.appendRow([QStandardItem("需要安装py7zr库"), QStandardItem("pip install py7zr")])
    
    def _parse_rar(self, file_path: str, model):
        """解析RAR文件"""
        try:
            import rarfile
            with rarfile.RarFile(file_path, 'r') as rf:
                for entry in rf.infolist():
                    if entry.filename.endswith('/'):
                        continue
                    try:
                        size = entry.file_size
                        size_str = self._format_size(size)
                        item_name = QStandardItem(entry.filename)
                        item_size = QStandardItem(size_str)
                        model.appendRow([item_name, item_size])
                    except Exception as e:
                        logger.debug(f"操作失败: {e}")
                        item_name = QStandardItem(entry.filename)
                        item_size = QStandardItem("未知")
                        model.appendRow([item_name, item_size])
        except ImportError:
            model.appendRow([QStandardItem("需要安装rarfile库"), QStandardItem("pip install rarfile")])
    
    def _parse_tar(self, file_path: str, model):
        """解析TAR文件"""
        import tarfile
        mode = 'r:*'
        try:
            with tarfile.open(file_path, mode) as tf:
                for member in tf.getmembers():
                    if member.isdir():
                        continue
                    try:
                        size = member.size
                        size_str = self._format_size(size)
                        item_name = QStandardItem(member.name)
                        item_size = QStandardItem(size_str)
                        model.appendRow([item_name, item_size])
                    except Exception as e:
                        logger.debug(f"操作失败: {e}")
                        item_name = QStandardItem(member.name)
                        item_size = QStandardItem("未知")
                        model.appendRow([item_name, item_size])
        except Exception as e:
            model.appendRow([QStandardItem(f"TAR文件解析失败: {str(e)}"), QStandardItem("")])
    
    def _parse_iso(self, file_path: str, model):
        """解析ISO文件"""
        try:
            import pycdlib
            iso = pycdlib.PyCdlib()
            try:
                iso.open(file_path)
                for child in iso.list_children(iso_path='/'):
                    if child.is_directory:
                        continue
                    try:
                        size = child.data_length
                        size_str = self._format_size(size)
                        item_name = QStandardItem(child.file_identifier.decode('utf-8', errors='ignore'))
                        item_size = QStandardItem(size_str)
                        model.appendRow([item_name, item_size])
                    except Exception as e:
                        logger.debug(f"操作失败: {e}")
                        item_name = QStandardItem(child.file_identifier.decode('utf-8', errors='ignore'))
                        item_size = QStandardItem("未知")
                        model.appendRow([item_name, item_size])
            finally:
                iso.close()
        except ImportError:
            model.appendRow([QStandardItem("需要安装pycdlib库"), QStandardItem("pip install pycdlib")])
        except Exception as e:
            model.appendRow([QStandardItem(f"ISO文件解析失败: {str(e)}"), QStandardItem("")])
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        if size < 1024:
            return f"{size} 字节"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        else:
            return f"{size / (1024 * 1024):.2f} MB"

class AudioVideoPreviewHandler(PreviewHandler):
    """
    音视频文件预览处理器
    支持MP3/MP4/AVI/MKV/FLAC/WAV等音视频文件
    """
    
    def _load_default_extensions(self) -> None:
        """加载默认扩展名"""
        self._extensions = [
            '.mp3', '.mp4', '.avi', '.mkv', '.flac', '.wav',
            '.ogg', '.mov', '.wmv', '.m4a', '.aac', '.wma',
            '.ac3', '.dts', '.ape', '.m4v', '.3gp', '.flv',
            '.ts', '.m2ts', '.vob', '.webm'
        ]
    
    def can_handle(self, file_path: str) -> bool:
        """
        检查是否为音视频文件
        """
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self._extensions
    
    def preview(self, file_path: str, parent_widget: QWidget) -> QWidget:
        """
        生成音视频文件预览
        内置播放器（播放 / 暂停 / 进度条）、显示时长 / 码率、音量调节
        """
        import os  # 显式导入os模块，确保作用域正确
        self._parent_widget = parent_widget
        preview_widget = QWidget(parent_widget)
        layout = QVBoxLayout(preview_widget)
        
        # 获取文件信息
        file_name = os.path.basename(file_path)
        try:
            file_size = os.path.getsize(file_path)
        except (OSError, PermissionError):
            file_size = 0
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        # 保存文件路径，在播放时才设置媒体源
        self.file_path = file_path
        
        # 创建信息标签
        info_label = QLabel(f"<h3>{file_name}</h3>")
        info_label.setAlignment(Qt.AlignCenter)
        
        details_layout = QVBoxLayout()
        details_layout.addWidget(QLabel(f"类型: {ext[1:].upper()}"))
        details_layout.addWidget(QLabel(f"大小: {file_size / 1024:.2f} KB"))
        
        # 创建媒体播放器和音频输出
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        # 设置播放器参数，优化MP3播放，减少时间戳警告
        self.media_player.setPlaybackRate(1.0)  # 正常播放速度
        self.media_player.setLoops(0)  # 不循环播放
        
        # 连接错误信号处理
        self.media_player.errorOccurred.connect(self._handle_media_error)
        
        # 创建视频部件（如果是音频文件，也可以使用）
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(300)
        self.video_widget.setStyleSheet("border: 1px solid #ccc;")
        self.media_player.setVideoOutput(self.video_widget)
        
        # 创建播放控制按钮
        control_layout = QHBoxLayout()
        
        # 播放按钮
        self.play_btn = QPushButton("播放")
        self.play_btn.clicked.connect(self._play_media)
        control_layout.addWidget(self.play_btn)
        
        # 暂停按钮
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.clicked.connect(self._pause_media)
        self.pause_btn.setEnabled(False)  # 初始禁用
        control_layout.addWidget(self.pause_btn)
        
        # 停止按钮
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self._stop_media)
        self.stop_btn.setEnabled(False)  # 初始禁用
        control_layout.addWidget(self.stop_btn)
        
        # 当前时间和总时长
        self.time_label = QLabel("00:00 / 00:00")
        control_layout.addWidget(self.time_label)
        control_layout.addStretch()
        
        # 添加进度条
        progress_layout = QHBoxLayout()
        progress_label = QLabel("进度:")
        progress_layout.addWidget(progress_label)
        
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(100)
        self.progress_slider.setValue(0)
        self.progress_slider.sliderPressed.connect(self._progress_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._progress_slider_released)
        self.progress_slider.valueChanged.connect(self._progress_slider_value_changed)
        progress_layout.addWidget(self.progress_slider, 1)
        
        # 添加音量控制
        volume_layout = QHBoxLayout()
        volume_label = QLabel("音量:")
        volume_layout.addWidget(volume_label)
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(70)  # 默认音量70%
        self.volume_slider.valueChanged.connect(self._volume_slider_changed)
        self.audio_output.setVolume(0.7)  # 默认音量70%
        volume_layout.addWidget(self.volume_slider, 1)
        
        # 音量值显示
        self.volume_value_label = QLabel("70%")
        volume_layout.addWidget(self.volume_value_label)
        volume_layout.addStretch()
        
        # 连接媒体播放器信号
        self.media_player.positionChanged.connect(self._position_changed)
        self.media_player.durationChanged.connect(self._duration_changed)
        self.media_player.playbackStateChanged.connect(self._playback_state_changed)
        
        # 创建定时器，用于更新播放时间
        self.timer = QTimer()
        self.timer.setInterval(1000)  # 每秒更新一次
        self.timer.timeout.connect(self._update_time_display)
        
        # 添加到主布局
        layout.addWidget(info_label)
        layout.addLayout(details_layout)
        layout.addWidget(self.video_widget, 1)
        layout.addLayout(control_layout)
        layout.addLayout(progress_layout)
        layout.addLayout(volume_layout)
        
        # 添加操作按钮
        button_layout = QHBoxLayout()
        open_btn = QPushButton("使用默认程序打开")
        open_btn.clicked.connect(lambda: self._open_file(file_path))
        
        button_layout.addWidget(open_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 连接预览widget的destroyed信号，确保资源正确释放
        # 使用lambda函数保存对self的引用，确保在preview_widget被销毁时self仍然存在
        def cleanup_on_destroyed(obj):
            # 确保self仍然存在
            if hasattr(self, 'media_player'):
                self._cleanup_resources()
        
        preview_widget.destroyed.connect(cleanup_on_destroyed)
        
        return preview_widget
    
    def _cleanup_resources(self):
        """
        清理媒体播放资源
        当预览widget被销毁时调用，确保媒体播放停止并释放资源
        """
        try:
            logger.info("开始清理媒体播放资源")
            
            # 停止定时器
            if hasattr(self, 'timer'):
                try:
                    if self.timer.isActive():
                        self.timer.stop()
                        logger.info("已停止媒体播放定时器")
                except Exception as e:
                    logger.error(f"停止定时器时发生错误: {e}")
            
            # 停止媒体播放
            if hasattr(self, 'media_player'):
                try:
                    # 先暂停再停止，确保资源正确释放
                    self.media_player.pause()
                    self.media_player.stop()
                    logger.info("已停止媒体播放")
                except Exception as e:
                    logger.error(f"停止媒体播放时发生错误: {e}")
            
            # 断开所有信号连接
            if hasattr(self, 'media_player'):
                try:
                    self.media_player.positionChanged.disconnect()
                except Exception as e:
                    logger.error(f"断开positionChanged信号时发生错误: {e}")
                try:
                    self.media_player.durationChanged.disconnect()
                except Exception as e:
                    logger.error(f"断开durationChanged信号时发生错误: {e}")
                try:
                    self.media_player.playbackStateChanged.disconnect()
                except Exception as e:
                    logger.error(f"断开playbackStateChanged信号时发生错误: {e}")
                try:
                    self.media_player.errorOccurred.disconnect()
                except Exception as e:
                    logger.error(f"断开errorOccurred信号时发生错误: {e}")
            
            # 删除引用
            if hasattr(self, 'media_player'):
                del self.media_player
                logger.info("已删除media_player引用")
            
            if hasattr(self, 'audio_output'):
                del self.audio_output
                logger.info("已删除audio_output引用")
            
            if hasattr(self, 'video_widget'):
                del self.video_widget
                logger.info("已删除video_widget引用")
            
            if hasattr(self, 'timer'):
                del self.timer
                logger.info("已删除timer引用")
            
            logger.info("已清除媒体播放相关资源引用")
        except Exception as e:
            logger.error(f"清理媒体播放资源时发生错误: {e}")

    
    def _play_media(self):
        """
        播放媒体
        """
        try:
            # 确保media_player存在
            if not hasattr(self, 'media_player'):
                logger.error("media_player不存在，无法播放")
                return
            
            # 首次播放时才设置媒体源
            if not hasattr(self, '_media_source_set') or not self._media_source_set:
                # 设置媒体源
                media_url = QUrl.fromLocalFile(self.file_path)
                self.media_player.setSource(media_url)
                self._media_source_set = True
            
            self.media_player.play()
            self.timer.start()
        except Exception as e:
            logger.error(f"播放媒体失败: {self.file_path}, 错误: {e}")
            # 显示错误信息
            from core.utils import show_error
            show_error(self._parent_widget, "播放失败", f"无法播放媒体文件: {e}")
    
    def _handle_media_error(self, error, error_string):
        """
        处理媒体播放错误
        """
        logger.error(f"媒体播放错误: {error}, 错误描述: {error_string}")
        # 仅记录错误，不影响用户体验
        # 对于MP3时间戳警告等非致命错误，允许继续播放
        if error != 0:  # 0表示无错误
            logger.warning(f"媒体播放警告: {error_string}")
            # 处理硬件加速错误
            if "d3d11" in error_string.lower() or "hwaccel" in error_string.lower():
                logger.warning("硬件加速初始化失败，尝试使用软件解码")
                # 对于硬件加速错误，我们可以尝试重新播放，系统会自动切换到软件解码
                try:
                    if hasattr(self, 'media_player'):
                        # 停止当前播放
                        self.media_player.stop()
                        # 重新播放
                        self.media_player.play()
                except Exception as e:
                    logger.error(f"尝试重新播放时发生错误: {e}")
    
    def _pause_media(self):
        """
        暂停媒体
        """
        self.media_player.pause()
        self.timer.stop()
    
    def _stop_media(self):
        """
        停止媒体
        """
        self.media_player.stop()
        self.timer.stop()
        self.progress_slider.setValue(0)
        self.time_label.setText("00:00 / 00:00")
    
    def _position_changed(self, position):
        """
        媒体位置变化
        """
        # 只有在没有拖动滑块时才更新进度条
        if not hasattr(self, '_is_slider_dragging') or not self._is_slider_dragging:
            duration = self.media_player.duration()
            if duration > 0:
                progress = int((position / duration) * 100)
                self.progress_slider.setValue(progress)
    
    def _duration_changed(self, duration):
        """
        媒体时长变化
        """
        if hasattr(self, 'progress_slider') and self.progress_slider:
            self.progress_slider.setRange(0, int(duration))
    
    def _playback_state_changed(self, state):
        """
        播放状态变化
        """
        from PySide6.QtMultimedia import QMediaPlayer
        
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.play_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            self.play_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
    
    def _progress_slider_pressed(self):
        """
        进度条被按下，准备拖动
        """
        self._is_slider_dragging = True
    
    def _progress_slider_released(self):
        """
        进度条被释放，设置媒体位置
        """
        self._is_slider_dragging = False
        # 设置媒体位置
        progress = self.progress_slider.value()
        duration = self.media_player.duration()
        if duration > 0:
            position = int((progress / 100) * duration)
            self.media_player.setPosition(position)
    
    def _progress_slider_value_changed(self, value):
        """
        进度条值变化
        """
        if hasattr(self, 'media_player') and self.media_player:
            self.media_player.setPosition(value)
    
    def _volume_slider_changed(self, value):
        """
        音量滑块变化
        """
        volume = value / 100.0
        self.audio_output.setVolume(volume)
        self.volume_value_label.setText(f"{value}%")
    
    def _update_time_display(self):
        """
        更新时间显示
        """
        current_position = self.media_player.position()
        duration = self.media_player.duration()
        
        # 格式化时间为 mm:ss
        current_str = self._format_time(current_position)
        duration_str = self._format_time(duration)
        
        self.time_label.setText(f"{current_str} / {duration_str}")
    
    def _format_time(self, milliseconds):
        """
        将毫秒转换为 mm:ss 格式
        """
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def _open_file(self, file_path: str) -> None:
        """
        使用默认程序打开文件
        """
        try:
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.name == 'posix':  # Linux/macOS
                import subprocess
                subprocess.call(['open', file_path])
            logger.info(f"已打开文件: {file_path}")
        except Exception as e:
            logger.error(f"打开文件失败: {file_path}, 错误: {e}")
            show_warning(self._parent_widget, "打开失败", f"无法打开文件: {e}")

class SpecialFormatPreviewHandler(PreviewHandler):
    """
    特殊格式文件预览处理器
    支持SQLite、字体文件（TTF/OTF）等特殊格式
    """
    
    def _load_default_extensions(self) -> None:
        """加载默认扩展名"""
        self._extensions = [
            '.sqlite', '.db', '.ttf', '.otf', '.woff', '.woff2', '.eot'
        ]
    
    def can_handle(self, file_path: str) -> bool:
        """
        检查是否为特殊格式文件
        """
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self._extensions
    
    def preview(self, file_path: str, parent_widget: QWidget) -> QWidget:
        """
        生成特殊格式文件预览
        MD 实时渲染、JSON/XML 树形结构、SQLite 表浏览、字体预览
        """
        self._parent_widget = parent_widget
        preview_widget = QWidget(parent_widget)
        layout = QVBoxLayout(preview_widget)
        
        # 获取文件信息
        file_name = os.path.basename(file_path)
        try:
            file_size = os.path.getsize(file_path)
        except (OSError, PermissionError):
            file_size = 0
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        # 创建信息标签
        info_label = QLabel(f"<h3>{file_name}</h3>")
        info_label.setAlignment(Qt.AlignCenter)
        
        details_layout = QVBoxLayout()
        details_layout.addWidget(QLabel(f"类型: {ext[1:].upper()}"))
        details_layout.addWidget(QLabel(f"大小: {file_size / 1024:.2f} KB"))
        
        # 根据文件类型实现不同的预览功能
        if ext in ['.md', '.markdown']:
            details_layout.addWidget(QLabel("预览: Markdown 实时渲染"))
            details_layout.addWidget(QLabel("支持: 语法高亮、实时预览"))
            preview_content = QLabel("[Markdown 预览区域]")
        elif ext in ['.json', '.xml']:
            details_layout.addWidget(QLabel("预览: JSON/XML 树形结构"))
            details_layout.addWidget(QLabel("支持: 树形展示、折叠/展开、语法高亮"))
            preview_content = QLabel("[JSON/XML 树形结构预览]")
        elif ext in ['.sqlite', '.db']:
            details_layout.addWidget(QLabel("预览: SQLite 表浏览"))
            details_layout.addWidget(QLabel("支持: 表结构查看、数据浏览"))
            preview_content = QLabel("[SQLite 表浏览区域]")
        elif ext in ['.ttf', '.otf', '.woff', '.woff2', '.eot']:
            details_layout.addWidget(QLabel("预览: 字体文件预览"))
            details_layout.addWidget(QLabel("支持: 字体样式展示、字符映射"))
            preview_content = QLabel("[字体预览区域]")
        else:
            preview_content = QLabel("[特殊格式预览区域]")
        
        preview_content.setAlignment(Qt.AlignCenter)
        preview_content.setStyleSheet("border: 1px solid #ccc; padding: 20px;")
        
        # 添加到主布局
        layout.addWidget(info_label)
        layout.addLayout(details_layout)
        layout.addWidget(preview_content, 1)
        
        # 添加操作按钮
        button_layout = QHBoxLayout()
        open_btn = QPushButton("使用默认程序打开")
        open_btn.clicked.connect(lambda: self._open_file(file_path))
        
        button_layout.addWidget(open_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        return preview_widget
    
    def _open_file(self, file_path: str) -> None:
        """
        使用默认程序打开文件
        """
        try:
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.name == 'posix':  # Linux/macOS
                import subprocess
                subprocess.call(['open', file_path])
            logger.info(f"已打开文件: {file_path}")
        except Exception as e:
            logger.error(f"打开文件失败: {file_path}, 错误: {e}")
            show_warning(self._parent_widget, "打开失败", f"无法打开文件: {e}")

class DefaultPreviewHandler(PreviewHandler):
    """
    默认预览处理器
    用于处理无法识别的文件类型，采用十六进制+编码方式显示
    """
    
    def can_handle(self, file_path: str) -> bool:
        """
        始终能处理
        """
        return True
    
    def preview(self, file_path: str, parent_widget: QWidget) -> QWidget:
        """
        生成默认预览，采用十六进制+编码方式显示
        """
        self._parent_widget = parent_widget
        preview_widget = QWidget(parent_widget)
        layout = QVBoxLayout(preview_widget)
        
        # 获取文件信息
        file_name = os.path.basename(file_path)
        try:
            file_size = os.path.getsize(file_path)
        except (OSError, PermissionError):
            file_size = 0
        mime_type, _ = mimetypes.guess_type(file_path)
        
        # 创建信息标签
        name_label = QLabel(f"<h3>{file_name}</h3>")
        name_label.setAlignment(Qt.AlignCenter)
        
        info_layout = QVBoxLayout()
        info_layout.addWidget(QLabel(f"类型: {mime_type or '未知'}"))
        info_layout.addWidget(QLabel(f"大小: {file_size / 1024:.2f} KB"))
        info_layout.addWidget(QLabel(f"路径: {file_path}"))
        
        # 尝试以十六进制+编码方式显示文件内容
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(4096)  # 只读取前4KB用于预览
            
            # 生成十六进制视图
            hex_view = QTextEdit()
            hex_view.setReadOnly(True)
            hex_view.setLineWrapMode(QTextEdit.NoWrap)
            
            # 构建十六进制内容
            hex_content = []
            ascii_content = []
            line_count = 0
            
            for i, byte in enumerate(raw_data):
                if i % 16 == 0:
                    if i > 0:
                        # 添加行号、十六进制和ASCII
                        hex_line = f"{line_count:08x}  {''.join(hex_content)}  {''.join(ascii_content)}"
                        hex_view.append(hex_line)
                        hex_content.clear()
                        ascii_content.clear()
                        line_count += 16
                
                # 十六进制部分
                hex_content.append(f"{byte:02x} ")
                
                # ASCII部分
                if 32 <= byte <= 126:
                    ascii_content.append(chr(byte))
                else:
                    ascii_content.append('.')
            
            # 添加最后一行
            if hex_content:
                # 补全空格
                hex_content += ['   '] * (16 - len(hex_content))
                hex_line = f"{line_count:08x}  {''.join(hex_content)}  {''.join(ascii_content)}"
                hex_view.append(hex_line)
            
            # 添加编码信息
            encoding = detect_file_encoding(file_path)
            info_layout.addWidget(QLabel(f"检测到的编码: {encoding}"))
            
            # 添加十六进制视图
            layout.addLayout(info_layout)
            layout.addWidget(QLabel("十六进制预览（前4KB）:"))
            layout.addWidget(hex_view, 1)
        except Exception as e:
            logger.error(f"生成十六进制预览失败: {file_path}, 错误: {e}")
            layout.addLayout(info_layout)
            layout.addWidget(QLabel("无法生成十六进制预览"))
        
        # 创建打开按钮
        open_btn = QPushButton("使用默认程序打开")
        open_btn.clicked.connect(lambda: self._open_file(file_path))
        
        # 添加到主布局
        layout.addWidget(open_btn)
        
        return preview_widget
    
    def _open_file(self, file_path: str) -> None:
        """
        使用默认程序打开文件
        """
        try:
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.name == 'posix':  # Linux/macOS
                import subprocess
                subprocess.call(['open', file_path])
            logger.info(f"已打开文件: {file_path}")
        except Exception as e:
            logger.error(f"打开文件失败: {file_path}, 错误: {e}")
            show_warning(self._parent_widget, "打开失败", f"无法打开文件: {e}")

class PreviewService:
    """
    文件预览服务类
    管理所有文件预览处理器
    """
    
    def __init__(self):
        """
        初始化预览服务
        """
        # 注册所有预览处理器（按优先级排序）
        self.handlers = [
            MarkdownPreviewHandler(),      # Markdown文件
            CodeHighlightPreviewHandler(), # 代码文件（带语法高亮）
            TextPreviewHandler(),          # 普通文本文件
            ImagePreviewHandler(),         # 图片文件
            DocumentPreviewHandler(),      # 文档文件
            ArchivePreviewHandler(),       # 压缩文件
            AudioVideoPreviewHandler(),    # 音视频文件
            SpecialFormatPreviewHandler(), # 特殊格式文件
            DefaultPreviewHandler()        # 默认处理器
        ]
        
        # 初始化配置适配器（动态加载配置）
        try:
            from services.preview_service_adapter import PreviewServiceAdapter
            self._adapter = PreviewServiceAdapter(self)
            logger.info("预览配置适配器已初始化")
        except Exception as e:
            logger.warning(f"预览配置适配器初始化失败: {e}，使用默认配置")
            self._adapter = None
        
        logger.info("文件预览服务已初始化")
    
    def preview(self, file_path: str, parent_widget: QWidget) -> QWidget:
        """
        预览指定文件（preview_file的别名）
        
        Args:
            file_path: 文件路径
            parent_widget: 父组件
            
        Returns:
            QWidget: 预览组件
        """
        return self.preview_file(file_path, parent_widget)
    
    def preview_file(self, file_path: str, parent_widget: QWidget) -> QWidget:
        """
        预览指定文件
        
        Args:
            file_path: 文件路径
            parent_widget: 父组件
            
        Returns:
            QWidget: 预览组件
        """
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            widget = QWidget()
            layout = QVBoxLayout(widget)
            error_label = QLabel("文件不存在")
            error_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(error_label)
            return widget
        
        # 查找合适的处理器
        for handler in self.handlers:
            if handler.can_handle(file_path):
                logger.info(f"使用{handler.__class__.__name__}处理文件: {file_path}")
                preview_widget = handler.preview(file_path, parent_widget)
                # 为preview_widget添加handler属性，指向使用的处理器实例
                preview_widget.handler = handler
                return preview_widget
        
        # 默认使用最后一个处理器
        logger.info(f"使用默认处理器处理文件: {file_path}")
        handler = self.handlers[-1]
        preview_widget = handler.preview(file_path, parent_widget)
        # 为preview_widget添加handler属性，指向使用的处理器实例
        preview_widget.handler = handler
        return preview_widget
    
    def get_supported_types(self) -> Dict[str, str]:
        """
        获取支持的文件类型
        
        Returns:
            Dict[str, str]: 文件类型映射
        """
        return {
            "文本文件": ".txt, .log, .py, .yaml, .yml, .ini, .csv, .html, .css, .js, .sql, .java, .c, .cpp, .h, .hpp, .php, .rb, .go, .sh, .bat, .ps1, .lua, .pl, .swift, .kt, .rs, .asm, .pas, .d, .rust, .scala, .groovy, .vb, .cs, .f, .f90, .fortran, .m, .matlab, .r, .sas, .stata, .sql, .pgsql, .mysql, .mssql, .oracle, .jsonl, .ndjson, .toml, .properties, .env, .gitignore, .dockerfile, .dockerignore, .yml, .yaml, .xsl, .xslt, .dtd, .xsd, .wsdl, .wSDL, .xhtml, .xht, .shtml, .shtm, .htm, .scss, .sass, .less, .styl, .jsx, .tsx, .ts, .js, .mjs, .cjs, .vue, .svelte, .astro, .mdx, .rmd, .qmd, .ipynb, .m3u, .m3u8, .pls, .xspf",
            "图片文件": ".jpg, .jpeg, .png, .gif, .bmp, .svg, .webp, .ico, .tiff, .tif",
            "文档文件": ".doc, .docx, .xls, .xlsx, .ppt, .pptx, .pdf, .wps, .et, .dps",
            "压缩文件": ".zip, .rar, .7z, .tar, .gz, .bz2, .xz, .tar.gz, .tar.bz2, .tar.xz, .iso",
            "音视频文件": ".mp3, .mp4, .avi, .mkv, .flac, .wav, .ogg, .mov, .wmv, .m4a, .aac, .wma, .ac3, .dts, .ape, .m4v, .3gp, .flv, .ts, .m2ts, .vob, .webm",
            "特殊格式文件": ".md, .markdown, .json, .xml, .sqlite, .db, .ttf, .otf, .woff, .woff2, .eot"
        }

# 创建全局预览服务实例
preview_service = PreviewService()