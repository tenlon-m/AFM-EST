#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜索服务模块
负责处理文件搜索功能
"""

import os
import fnmatch
from typing import List, Dict, Any, Optional
from datetime import datetime
from core.logger import logger
from core.config import config_manager

try:
    from services.whoosh_search_service import WhooshSearchService
    HAS_WHOOSH = True
except ImportError:
    HAS_WHOOSH = False

try:
    from services.file_metadata_cache import get_file_metadata_cache
    HAS_METADATA_CACHE = True
    file_metadata_cache = get_file_metadata_cache()
except ImportError:
    HAS_METADATA_CACHE = False
    file_metadata_cache = None

class SearchService:
    """
    搜索服务类
    负责处理文件搜索功能
    """
    
    def __init__(self):
        """
        初始化搜索服务
        """
        self.logger = logger
        self.config = config_manager
        
        # 初始化Whoosh全文搜索服务
        self.whoosh_service = None
        if HAS_WHOOSH and config_manager.get("search.enable_whoosh", True):
            try:
                index_dir = config_manager.get("search.whoosh_index_dir", None)
                self.whoosh_service = WhooshSearchService(index_dir)
                self.logger.info("Whoosh全文搜索服务已启用")
            except Exception as e:
                self.logger.warning(f"Whoosh全文搜索服务初始化失败: {e}")
        
        self.logger.info("搜索服务已初始化")
    
    def search_in_directory(self, directory: str, keyword: str, include_subdirectories: bool = True, 
                          file_types: List[str] = None, min_size: int = 0, max_size: int = None, 
                          min_date: datetime = None, max_date: datetime = None, 
                          progress_callback: callable = None, 
                          stop_flag: callable = None,  # 停止标志函数，返回True表示停止
                          pause_flag: callable = None,  # 暂停标志函数，返回True表示暂停
                          page: int = 1, page_size: int = 100   # 分页参数
                          ) -> Dict[str, Any]:
        """
        在指定目录中搜索文件（支持分页）
        
        Args:
            directory: 搜索目录
            keyword: 搜索关键字
            include_subdirectories: 是否包含子目录
            file_types: 文件类型列表（如['.txt', '.pdf']）
            min_size: 最小文件大小（字节）
            max_size: 最大文件大小（字节）
            min_date: 最小修改日期
            max_date: 最大修改日期
            progress_callback: 进度回调函数，接收(current_file, total_files, progress_text, success_count)参数
            stop_flag: 停止标志函数，返回True表示停止搜索
            pause_flag: 暂停标志函数，返回True表示暂停搜索
            page: 页码（从1开始）
            page_size: 每页大小
            
        Returns:
            Dict[str, Any]: 包含results、total、page、page_size的分页结果
        """
        results = []
        success_count = 0
        
        # 确保目录存在
        if not os.path.exists(directory):
            self.logger.error(f"搜索目录不存在: {directory}")
            return results
        
        # 构建搜索模式
        search_pattern = f"*{keyword}*"
        
        # 优化：合并统计和搜索为一次遍历，避免重复os.walk
        # 首先进行一次快速估算，或者直接开始搜索并动态更新总文件数
        total_files = 0
        processed_files = 0
        
        # 第一次遍历：同时统计文件数和执行搜索
        for root, dirs, files in os.walk(directory):
            # 更新总文件数
            total_files += len(files)
            
            for file in files:
                # 检查是否需要停止
                if stop_flag and stop_flag():
                    self.logger.info("搜索已停止")
                    return results
                
                # 检查是否需要暂停
                if pause_flag and pause_flag():
                    if progress_callback:
                        progress_callback(processed_files, total_files, "搜索已暂停", success_count)
                    # 等待，直到恢复或停止
                    import time
                    while pause_flag():
                        if stop_flag and stop_flag():
                            self.logger.info("搜索已停止")
                            return results
                        time.sleep(0.1)
                    if progress_callback:
                        progress_callback(processed_files, total_files, f"正在搜索: {file}", success_count)
                
                processed_files += 1
                
                # 调用进度回调，实时更新总文件数
                if progress_callback:
                    progress_text = f"正在搜索: {file}"
                    progress_callback(processed_files, total_files, progress_text, success_count)
                
                # 匹配文件名
                is_match = fnmatch.fnmatch(file.lower(), search_pattern.lower())
                
                if is_match:
                    file_path = os.path.join(root, file)
                    
                    # 检查文件类型
                    if file_types:
                        file_ext = os.path.splitext(file)[1].lower()
                        if file_ext not in file_types:
                            is_match = False
                
                # 如果匹配成功，添加到结果列表
                if is_match:
                    file_path = os.path.join(root, file)
                    
                    # 获取文件信息
                    try:
                        if HAS_METADATA_CACHE and file_metadata_cache:
                            metadata = file_metadata_cache.get_metadata(file_path)
                            if metadata:
                                file_size = metadata["size"]
                                file_mtime = datetime.fromtimestamp(metadata["mtime"])
                            else:
                                stat_info = os.stat(file_path)
                                file_size = stat_info.st_size
                                file_mtime = datetime.fromtimestamp(stat_info.st_mtime)
                                file_metadata_cache.cache_metadata(file_path, stat_info)
                        else:
                            stat_info = os.stat(file_path)
                            file_size = stat_info.st_size
                            file_mtime = datetime.fromtimestamp(stat_info.st_mtime)
                        
                        # 检查文件大小
                        if file_size < min_size:
                            is_match = False
                        if max_size and file_size > max_size:
                            is_match = False
                        
                        # 检查修改日期
                        if min_date and file_mtime < min_date:
                            is_match = False
                        if max_date and file_mtime > max_date:
                            is_match = False
                        
                        # 添加到结果列表
                        if is_match:
                            results.append({
                                "name": file,
                                "path": file_path,
                                "size": file_size,
                                "modified_time": file_mtime,
                                "is_dir": False
                            })
                            success_count += 1
                    except Exception as e:
                        self.logger.error(f"获取文件信息失败: {file_path}, 错误: {e}")
            
            # 是否继续搜索子目录
            if not include_subdirectories:
                break
        
        self.logger.info(f"在 {directory} 中搜索到 {len(results)} 个文件")
        
        # 分页处理
        total = len(results)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_results = results[start:end]
        
        return {
            "results": paginated_results,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": end < total
        }
    
    def search_by_content(self, directory: str, keyword: str, file_types: List[str] = None, 
                         include_subdirectories: bool = True, progress_callback: callable = None,
                         stop_flag: callable = None,  # 停止标志函数，返回True表示停止
                         pause_flag: callable = None,  # 暂停标志函数，返回True表示暂停
                         page: int = 1, page_size: int = 100   # 分页参数
                         ) -> Dict[str, Any]:
        """
        在文件内容中搜索关键字
        
        Args:
            directory: 搜索目录
            keyword: 搜索关键字
            file_types: 文件类型列表（如['.txt', '.py']）
            include_subdirectories: 是否包含子目录
            progress_callback: 进度回调函数，接收(current_file, total_files, progress_text, success_count)参数
            stop_flag: 停止标志函数，返回True表示停止搜索
            pause_flag: 暂停标志函数，返回True表示暂停搜索
            
        Returns:
            List[Dict[str, Any]]: 搜索结果列表
        """
        results = []
        
        # 支持的文本文件类型
        text_file_types = [
            '.txt', '.log', '.py', '.json', '.yaml', '.yml', '.ini',
            '.csv', '.md', '.html', '.css', '.js', '.xml', '.sql', '.lrc',
            '.java', '.c', '.cpp', '.h', '.hpp', '.php', '.rb', '.go',
            '.doc', '.docx', '.wps', '.pdf', '.xls', '.xlsx', '.ppt', '.pptx'
        ]
        
        # 如果没有指定文件类型，默认只搜索文本文件
        if not file_types:
            file_types = text_file_types
        
        # 优化：合并统计和搜索为一次遍历，避免重复os.walk
        total_files = 0
        processed_files = 0
        success_count = 0
        
        # 遍历目录，同时统计文件数和执行搜索
        for root, dirs, files in os.walk(directory, topdown=True):
            # 更新总文件数
            total_files += len(files)
            
            # 记录当前目录，用于调试
            self.logger.debug(f"正在搜索目录: {root}")
            
            for file in files:
                # 检查是否需要停止
                if stop_flag and stop_flag():
                    self.logger.info("搜索已停止")
                    return results
                
                # 检查是否需要暂停
                if pause_flag and pause_flag():
                    if progress_callback:
                        progress_callback(processed_files, total_files, "搜索已暂停", success_count)
                    # 等待，直到恢复或停止
                    import time
                    while pause_flag():
                        if stop_flag and stop_flag():
                            self.logger.info("搜索已停止")
                            return results
                        time.sleep(0.1)
                    if progress_callback:
                        progress_callback(processed_files, total_files, f"正在搜索: {file}", success_count)
                
                processed_files += 1
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1].lower()
                
                # 调用进度回调，实时更新总文件数
                if progress_callback:
                    progress_text = f"正在搜索: {file}"
                    progress_callback(processed_files, total_files, progress_text, success_count)
                
                # 记录当前文件，用于调试
                self.logger.debug(f"正在检查文件: {file_path}")
                
                # 检查文件类型
                if file_ext not in file_types:
                    self.logger.debug(f"文件类型 {file_ext} 不在允许的列表中")
                    continue
                
                # 读取文件内容并搜索关键字
                try:
                    content = ""
                    file_ext = file_ext.lower()
                    
                    # 根据文件类型选择不同的读取方式
                    if file_ext in ['.txt', '.log', '.py', '.json', '.yaml', '.yml', '.ini',
                                  '.csv', '.md', '.html', '.css', '.js', '.xml', '.sql',
                                  '.java', '.c', '.cpp', '.h', '.hpp', '.php', '.rb', '.go']:
                        # 文本文件，使用改进的编码检测功能
                        from core.utils import detect_file_encoding
                        encoding = detect_file_encoding(file_path)
                        self.logger.debug(f"检测到文件 {file_path} 的编码为: {encoding}")
                        
                        try:
                            if encoding != '未知':
                                with open(file_path, 'r', encoding=encoding) as f:
                                    content = f.read()
                            else:
                                # 尝试默认编码
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                        except UnicodeDecodeError as e:
                            # 修复：如果检测到的编码是utf-16-le或utf-16-be，但读取失败，尝试使用utf-8
                            self.logger.debug(f"使用编码 {encoding} 读取文件失败: {file_path}, 错误: {e}")
                            try:
                                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    content = f.read()
                                self.logger.debug(f"使用utf-8编码忽略错误读取文件: {file_path}")
                            except Exception as e2:
                                self.logger.error(f"读取文件内容失败: {file_path}, 错误: {e2}")
                                continue
                    elif file_ext == '.docx':
                        # Word文档(.docx)
                        try:
                            from docx import Document
                            doc = Document(file_path)
                            for para in doc.paragraphs:
                                content += para.text + '\n'
                            for table in doc.tables:
                                for row in table.rows:
                                    for cell in row.cells:
                                        content += cell.text + '\t'
                                    content += '\n'
                            self.logger.debug(f"成功读取docx文件: {file_path}")
                        except Exception as e:
                            self.logger.debug(f"读取docx文件失败: {file_path}, 错误: {e}")
                            continue
                    elif file_ext == '.doc':
                        # Word文档(.doc) - 尝试使用不同的方法
                        content_found = False
                        # 方法1：尝试使用pywin32（Windows平台）
                        try:
                            import pythoncom
                            import win32com.client
                            
                            # 初始化COM
                            pythoncom.CoInitialize()
                            
                            try:
                                # 创建Word应用程序对象
                                word = win32com.client.Dispatch('Word.Application')
                                word.Visible = False  # 隐藏Word窗口
                                
                                try:
                                    # 打开文档
                                    doc = word.Documents.Open(os.path.abspath(file_path))
                                    
                                    try:
                                        # 读取文档内容
                                        content = doc.Content.Text
                                        content_found = True
                                        self.logger.debug(f"使用pywin32成功读取doc文件: {file_path}, 内容长度: {len(content)}")
                                    finally:
                                        # 关闭文档，无论是否成功读取内容
                                        try:
                                            doc.Close(SaveChanges=False)
                                        except Exception as e:
                                            self.logger.debug(f"关闭doc文件失败: {file_path}, 错误: {e}")
                                finally:
                                    # 退出Word应用程序，无论是否成功打开文档
                                    try:
                                        # 使用更可靠的方式退出Word应用程序
                                        word.Quit()
                                    except Exception as e:
                                        # 忽略Quit方法可能出现的错误
                                        self.logger.debug(f"退出Word应用程序失败: {file_path}, 错误: {e}")
                                        # 尝试直接终止进程（最后手段）
                                        try:
                                            word._oleobj_.Invoke(419, 0, 1, 0)  # 419是Quit方法的调度ID
                                        except Exception as e2:
                                            self.logger.debug(f"强制退出Word应用程序失败: {file_path}, 错误: {e2}")
                            except Exception as e:
                                self.logger.debug(f"Word操作失败: {file_path}, 错误: {e}")
                            finally:
                                # 释放COM资源
                                pythoncom.CoUninitialize()
                        except Exception as e:
                            self.logger.debug(f"使用pywin32读取doc文件失败: {file_path}, 错误: {e}")
                        
                        # 方法2：尝试使用textract库（跨平台方案）
                        if not content_found:
                            try:
                                import textract
                                content = textract.process(file_path, encoding='utf-8').decode('utf-8', errors='ignore')
                                content_found = True
                                self.logger.debug(f"使用textract成功读取doc文件: {file_path}, 内容长度: {len(content)}")
                            except Exception as e:
                                self.logger.debug(f"使用textract读取doc文件失败: {file_path}, 错误: {e}")
                        
                        # 方法3：如果上述方法都失败，跳过该文件
                        if not content_found:
                            self.logger.debug(f"所有方法都无法读取doc文件: {file_path}")
                            continue
                    elif file_ext == '.pdf':
                        # PDF文件
                        try:
                            import PyPDF2
                            with open(file_path, 'rb') as f:
                                pdf_reader = PyPDF2.PdfReader(f)
                                for page in pdf_reader.pages:
                                    content += page.extract_text() + '\n'
                            self.logger.debug(f"成功读取pdf文件: {file_path}")
                        except Exception as e:
                            self.logger.debug(f"读取pdf文件失败: {file_path}, 错误: {e}")
                            # 尝试使用pdfplumber
                            try:
                                import pdfplumber
                                with pdfplumber.open(file_path) as pdf:
                                    for page in pdf.pages:
                                        content += page.extract_text() + '\n'
                                self.logger.debug(f"使用pdfplumber成功读取pdf文件: {file_path}")
                            except Exception as e2:
                                self.logger.debug(f"使用pdfplumber读取pdf文件失败: {file_path}, 错误: {e2}")
                                continue
                    elif file_ext == '.xlsx':
                        # Excel文件(.xlsx)
                        try:
                            from openpyxl import load_workbook
                            workbook = load_workbook(file_path)
                            for sheet in workbook.sheetnames:
                                worksheet = workbook[sheet]
                                for row in worksheet.iter_rows(values_only=True):
                                    for cell in row:
                                        if cell is not None:
                                            content += str(cell) + '\t'
                                    content += '\n'
                            self.logger.debug(f"成功读取xlsx文件: {file_path}")
                        except Exception as e:
                            self.logger.debug(f"读取xlsx文件失败: {file_path}, 错误: {e}")
                            continue
                    elif file_ext == '.pptx':
                        # PowerPoint文件(.pptx)
                        try:
                            from pptx import Presentation
                            prs = Presentation(file_path)
                            for slide in prs.slides:
                                for shape in slide.shapes:
                                    if hasattr(shape, 'text'):
                                        content += shape.text + '\n'
                            self.logger.debug(f"成功读取pptx文件: {file_path}")
                        except Exception as e:
                            self.logger.debug(f"读取pptx文件失败: {file_path}, 错误: {e}")
                            continue
                    elif file_ext in ['.wps', '.et', '.dps']:
                        # WPS文件 - 暂时跳过或使用特殊处理
                        self.logger.debug(f"WPS文件暂不支持内容搜索: {file_path}")
                        continue
                    else:
                        # 其他文件类型，尝试使用文本方式读取
                        from core.utils import detect_file_encoding
                        encoding = detect_file_encoding(file_path)
                        if encoding != '未知':
                            with open(file_path, 'r', encoding=encoding) as f:
                                content = f.read()
                        else:
                            # 尝试默认编码
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                    
                    # 搜索关键字
                    if keyword.lower() in content.lower():
                        # 获取文件信息
                        stat_info = os.stat(file_path)
                        file_size = stat_info.st_size
                        file_mtime = datetime.fromtimestamp(stat_info.st_mtime)
                        
                        results.append({
                            "name": file,
                            "path": file_path,
                            "size": file_size,
                            "modified_time": file_mtime,
                            "is_dir": False,
                            "content_match": True
                        })
                        success_count += 1
                        self.logger.debug(f"找到匹配文件: {file_path}")
                except UnicodeDecodeError as e:
                    self.logger.debug(f"文件 {file_path} 解码失败，错误: {e}")
                    # 尝试使用gbk编码
                    try:
                        with open(file_path, 'r', encoding='gbk') as f:
                            content = f.read()
                            if keyword.lower() in content.lower():
                                # 获取文件信息
                                stat_info = os.stat(file_path)
                                file_size = stat_info.st_size
                                file_mtime = datetime.fromtimestamp(stat_info.st_mtime)
                                
                                results.append({
                                    "name": file,
                                    "path": file_path,
                                    "size": file_size,
                                    "modified_time": file_mtime,
                                    "is_dir": False,
                                    "content_match": True
                                })
                                success_count += 1
                                self.logger.debug(f"找到匹配文件: {file_path}")
                    except Exception as e:
                        # 忽略无法读取的文件
                        self.logger.debug(f"无法读取文件内容: {file_path}, 错误: {e}")
                except Exception as e:
                    self.logger.error(f"搜索文件内容失败: {file_path}, 错误: {e}")
            
            # 是否继续搜索子目录
            if not include_subdirectories:
                # 清空dirs列表，这样os.walk就不会继续遍历子目录
                dirs.clear()
        
        self.logger.info(f"在 {directory} 中搜索到 {len(results)} 个包含关键字的文件")
        
        # 分页处理
        total = len(results)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_results = results[start:end]
        
        return {
            "results": paginated_results,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": end < total
        }
    
    def get_recent_files(self, directory: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        获取最近修改的文件
        
        Args:
            directory: 搜索目录
            days: 天数
            
        Returns:
            List[Dict[str, Any]]: 最近修改的文件列表
        """
        from datetime import timedelta
        
        # 计算最小修改日期
        min_date = datetime.now() - timedelta(days=days)
        
        # 搜索文件
        result = self.search_in_directory(directory, "", include_subdirectories=True, min_date=min_date)
        return result.get("results", result) if isinstance(result, dict) else result
    
    def get_large_files(self, directory: str, min_size: int = 100 * 1024 * 1024, include_subdirectories: bool = True) -> List[Dict[str, Any]]:
        """
        获取大文件
        
        Args:
            directory: 搜索目录
            min_size: 最小文件大小（字节），默认100MB
            include_subdirectories: 是否包含子目录
            
        Returns:
            List[Dict[str, Any]]: 大文件列表
        """
        # 搜索文件
        result = self.search_in_directory(directory, "", include_subdirectories=include_subdirectories, min_size=min_size)
        return result.get("results", result) if isinstance(result, dict) else result
    
    def format_search_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        格式化搜索结果
        
        Args:
            results: 搜索结果列表
            
        Returns:
            List[Dict[str, Any]]: 格式化后的搜索结果
        """
        formatted_results = []
        
        for result in results:
            formatted_result = result.copy()
            
            # 格式化文件大小
            formatted_result['size_str'] = self._format_size(result['size'])
            
            # 格式化修改日期
            formatted_result['modified_str'] = result['modified_time'].strftime('%Y-%m-%d %H:%M:%S')
            
            formatted_results.append(formatted_result)
        
        return formatted_results
    
    def _format_size(self, size: int) -> str:
        """
        格式化文件大小
        
        Args:
            size: 文件大小（字节）
            
        Returns:
            str: 格式化后的文件大小
        """
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.2f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.2f} GB"
    
    def get_supported_file_types(self) -> List[str]:
        """
        获取支持的文件类型
        
        Returns:
            List[str]: 支持的文件类型列表
        """
        return [
            '.txt', '.log', '.py', '.json', '.yaml', '.yml', '.ini',
            '.csv', '.md', '.html', '.css', '.js', '.xml', '.sql',
            '.java', '.c', '.cpp', '.h', '.hpp', '.php', '.rb', '.go',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp',
            '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
            '.mp3', '.wav', '.ogg', '.mp4', '.avi', '.mov', '.mkv'
        ]
    
    def search_async(self, directory: str, keyword: str, callback: callable = None, **kwargs):
        """
        异步搜索文件（使用线程池）
        
        Args:
            directory: 搜索目录
            keyword: 搜索关键字
            callback: 完成回调函数，接收(results)参数
            **kwargs: 其他搜索参数
            
        Returns:
            threading.Thread: 搜索线程对象
        """
        from core.thread_pool import thread_pool_manager
        import threading
        
        def search_task():
            try:
                result = self.search_in_directory(directory, keyword, **kwargs)
                results = result.get("results", result) if isinstance(result, dict) else result
                if callback:
                    callback(results)
                return results
            except Exception as e:
                self.logger.error(f"异步搜索失败: {e}")
                if callback:
                    callback([])
                return []
        
        # 提交到线程池
        future = thread_pool_manager.submit(search_task)
        return future

# 创建全局搜索服务实例
search_service = SearchService()