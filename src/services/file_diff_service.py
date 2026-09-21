#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件对比服务模块
实现文本文件和文件夹的差异对比功能
"""

import os
import difflib
from datetime import datetime
from typing import List, Dict, Tuple, Optional

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from core.logger import logger

def read_document_text(file_path):
    """
    读取文档文件的文本内容，使用预览服务中的逻辑
    """
    import os
    
    _, ext = os.path.splitext(file_path.lower())
    
    paragraphs = []
    
    if ext in ['.doc', '.docx', '.wps']:
        try:
            import pythoncom
            import win32com.client
            
            pythoncom.CoInitialize()
            
            wps_apps = [
                {"name": "WPS", "prog_id": "Kwps.Application"}
            ]
            
            content_found = False
            
            for app in wps_apps:
                try:
                    wps = win32com.client.Dispatch(app['prog_id'])
                    wps.Visible = False
                    wps.DisplayAlerts = False
                    
                    try:
                        doc = wps.Documents.Open(os.path.abspath(file_path), ReadOnly=True)
                        
                        try:
                            content = doc.Content.Text
                            if content:
                                paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
                            content_found = True
                            break
                        finally:
                            try:
                                doc.Close(SaveChanges=False)
                            except Exception as e:
                                logger.debug(f"操作失败: {e}")
                    except Exception as e:
                        logger.debug(f"操作失败: {e}")
                        try:
                            doc = wps.Documents.Open(os.path.abspath(file_path), ConfirmConversions=False, ReadOnly=True)
                            
                            try:
                                content = doc.Content.Text
                                if content:
                                    paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
                                content_found = True
                                break
                            finally:
                                try:
                                    doc.Close(SaveChanges=False)
                                except Exception as e:
                                    logger.debug(f"操作失败: {e}")
                        except Exception as e:
                            logger.debug(f"操作失败: {e}")
                    finally:
                        try:
                            wps.Visible = False
                        except Exception as e:
                            logger.debug(f"操作失败: {e}")
                except Exception as e:
                    logger.debug(f"操作跳过: {e}")
                    continue
        except ImportError:
            logger.debug("win32com模块未安装，跳过WPS文档读取")
        except Exception as e:
            logger.debug(f"操作失败: {e}")
        finally:
            try:
                pythoncom.CoUninitialize()
            except Exception as e:
                logger.debug(f"操作失败: {e}")
    if not paragraphs and ext in ['.docx']:
        try:
            from docx import Document
            
            try:
                doc = Document(file_path)
                paragraphs = [para.text.strip() for para in doc.paragraphs if para.text.strip()]
            except Exception as e:
                logger.debug(f"操作失败: {e}")
        except ImportError:
            pass
    
    if not paragraphs:
        try:
            import docx2txt
            content = docx2txt.process(file_path)
            if content:
                paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
        except ImportError:
            logger.debug("win32com模块未安装，跳过WPS文档读取")
        except Exception as e:
            logger.debug(f"操作失败: {e}")
    if not paragraphs and ext in ['.xls', '.xlsx', '.et']:
        try:
            try:
                from openpyxl import load_workbook
                
                wb = load_workbook(filename=file_path, read_only=True)
                sheets = wb.sheetnames
                
                for sheet_name in sheets:
                    ws = wb[sheet_name]
                    
                    max_rows = ws.max_row
                    max_cols = ws.max_column
                    
                    paragraphs.append(f"工作表: {sheet_name}")
                    
                    if max_rows > 0:
                        header_row = []
                        for col in range(1, min(max_cols + 1, 100)):
                            cell_value = ws.cell(row=1, column=col).value
                            header_row.append(str(cell_value) if cell_value is not None else "")
                        if header_row:
                            paragraphs.append('\t'.join(header_row))
                        
                    for row in range(2, min(max_rows + 1, 1000)):
                        row_data = []
                        for col in range(1, min(max_cols + 1, 100)):
                            cell_value = ws.cell(row=row, column=col).value
                            row_data.append(str(cell_value) if cell_value is not None else "")
                        if row_data:
                            paragraphs.append('\t'.join(row_data))
            
            except ImportError:
                pass
            except Exception as e:
                logger.debug(f"操作失败: {e}")
            if not paragraphs:
                try:
                    import xlrd
                    
                    workbook = xlrd.open_workbook(file_path)
                    
                    for sheet_idx in range(workbook.nsheets):
                        sheet = workbook.sheet_by_index(sheet_idx)
                        sheet_name = sheet.name
                        
                        paragraphs.append(f"工作表: {sheet_name}")
                        
                        if sheet.nrows > 0:
                            header_row = []
                            for col in range(min(sheet.ncols, 100)):
                                cell_value = sheet.cell_value(0, col)
                                header_row.append(str(cell_value) if cell_value is not None else "")
                            if header_row:
                                paragraphs.append('\t'.join(header_row))
                            
                        for row in range(1, min(sheet.nrows, 1000)):
                            row_data = []
                            for col in range(min(sheet.ncols, 100)):
                                cell_value = sheet.cell_value(row, col)
                                row_data.append(str(cell_value) if cell_value is not None else "")
                            if row_data:
                                paragraphs.append('\t'.join(row_data))
                    
                except ImportError:
                    pass
                except Exception as e:
                    logger.debug(f"操作失败: {e}")
            if not paragraphs and ext == '.et':
                try:
                    import pythoncom
                    import win32com.client
                    
                    pythoncom.CoInitialize()
                    
                    wps_apps = [
                        {"name": "WPS表格", "prog_id": "KET.Application"},
                        {"name": "WPS表格", "prog_id": "KWPS.Application"}
                    ]
                    
                    content_found = False
                    
                    for app in wps_apps:
                        try:
                            wps = win32com.client.Dispatch(app['prog_id'])
                            wps.Visible = False
                            wps.DisplayAlerts = False
                            
                            try:
                                workbook = wps.Workbooks.Open(os.path.abspath(file_path), ReadOnly=True)
                                
                                try:
                                    for sheet_idx in range(workbook.Sheets.Count):
                                        sheet = workbook.Sheets(sheet_idx + 1)
                                        sheet_name = sheet.Name
                                        
                                        paragraphs.append(f"工作表: {sheet_name}")
                                        
                                        used_range = sheet.UsedRange
                                        max_row = min(used_range.Rows.Count, 1000)
                                        max_col = min(used_range.Columns.Count, 100)
                                        
                                        header_row = []
                                        for col in range(1, max_col + 1):
                                            cell_value = sheet.Cells(1, col).Value
                                            header_row.append(str(cell_value) if cell_value is not None else "")
                                        if header_row:
                                            paragraphs.append('\t'.join(header_row))
                                        
                                        for row in range(2, max_row + 1):
                                            row_data = []
                                            for col in range(1, max_col + 1):
                                                cell_value = sheet.Cells(row, col).Value
                                                row_data.append(str(cell_value) if cell_value is not None else "")
                                            if row_data:
                                                paragraphs.append('\t'.join(row_data))
                                    
                                    content_found = True
                                    break
                                finally:
                                    try:
                                        workbook.Close(SaveChanges=False)
                                    except Exception as e:
                                        logger.debug(f"操作失败: {e}")
                            except Exception as e:
                                logger.debug(f"操作失败: {e}")
                                try:
                                    workbook = wps.Workbooks.Open(os.path.abspath(file_path), ConfirmConversions=False, ReadOnly=True)
                                    
                                    try:
                                        for sheet_idx in range(workbook.Sheets.Count):
                                            sheet = workbook.Sheets(sheet_idx + 1)
                                            sheet_name = sheet.Name
                                            
                                            paragraphs.append(f"工作表: {sheet_name}")
                                            
                                            used_range = sheet.UsedRange
                                            max_row = min(used_range.Rows.Count, 1000)
                                            max_col = min(used_range.Columns.Count, 100)
                                            
                                            header_row = []
                                            for col in range(1, max_col + 1):
                                                cell_value = sheet.Cells(1, col).Value
                                                header_row.append(str(cell_value) if cell_value is not None else "")
                                            if header_row:
                                                paragraphs.append('\t'.join(header_row))
                                            
                                            for row in range(2, max_row + 1):
                                                row_data = []
                                                for col in range(1, max_col + 1):
                                                    cell_value = sheet.Cells(row, col).Value
                                                    row_data.append(str(cell_value) if cell_value is not None else "")
                                                if row_data:
                                                    paragraphs.append('\t'.join(row_data))
                                        
                                        content_found = True
                                        break
                                    finally:
                                        try:
                                            workbook.Close(SaveChanges=False)
                                        except Exception as e:
                                            logger.debug(f"操作失败: {e}")
                                except Exception as e:
                                    logger.debug(f"操作失败: {e}")
                            finally:
                                try:
                                    wps.Visible = False
                                except Exception as e:
                                    logger.debug(f"操作失败: {e}")
                        except Exception as e:
                            logger.debug(f"操作跳过: {e}")
                            continue
                except ImportError:
                    pass
                except Exception as e:
                    logger.debug(f"操作失败: {e}")
                finally:
                    try:
                        pythoncom.CoUninitialize()
                    except Exception as e:
                        logger.debug(f"操作失败: {e}")
        except Exception as e:
            logger.debug(f"操作失败: {e}")
    if not paragraphs and ext in ['.ppt', '.pptx', '.dps']:
        try:
            import pythoncom
            import win32com.client
            
            pythoncom.CoInitialize()
            
            wps_apps = [
                {"name": "WPS演示", "prog_id": "KPPS.Application"},
                {"name": "WPS演示", "prog_id": "KWPS.Application"}
            ]
            
            content_found = False
            
            for app in wps_apps:
                try:
                    wps = win32com.client.Dispatch(app['prog_id'])
                    wps.Visible = False
                    wps.DisplayAlerts = False
                    
                    try:
                        presentation = wps.Presentations.Open(os.path.abspath(file_path), ReadOnly=True)
                        
                        try:
                            for slide_idx in range(presentation.Slides.Count):
                                slide = presentation.Slides(slide_idx + 1)
                                paragraphs.append(f"幻灯片 {slide_idx + 1}")
                                
                                for shape in slide.Shapes:
                                    if shape.HasTextFrame:
                                        if shape.TextFrame.HasText:
                                            text = shape.TextFrame.TextRange.Text
                                            if text.strip():
                                                paragraphs.append(f"  - {text.strip()}")
                            
                            content_found = True
                            break
                        finally:
                            try:
                                presentation.Close()
                            except Exception as e:
                                logger.debug(f"操作失败: {e}")
                    except Exception as e:
                        logger.debug(f"操作失败: {e}")
                        try:
                            presentation = wps.Presentations.Open(os.path.abspath(file_path), ReadOnly=True)
                            
                            for slide_idx in range(presentation.Slides.Count):
                                slide = presentation.Slides(slide_idx + 1)
                                paragraphs.append(f"幻灯片 {slide_idx + 1}")
                                
                                for shape in slide.Shapes:
                                    if shape.HasTextFrame:
                                        if shape.TextFrame.HasText:
                                            text = shape.TextFrame.TextRange.Text
                                            if text.strip():
                                                paragraphs.append(f"  - {text.strip()}")
                            
                            content_found = True
                            break
                        finally:
                            try:
                                presentation.Close()
                            except Exception as e:
                                logger.debug(f"操作失败: {e}")
                    finally:
                        try:
                            wps.Visible = False
                        except Exception as e:
                            logger.debug(f"操作失败: {e}")
                except Exception as e:
                    logger.debug(f"操作跳过: {e}")
                    continue
        except ImportError:
            logger.debug("win32com模块未安装，跳过WPS文档读取")
        except Exception as e:
            logger.debug(f"操作失败: {e}")
        finally:
            try:
                pythoncom.CoUninitialize()
            except Exception as e:
                logger.debug(f"操作失败: {e}")
    if not paragraphs and ext == '.pdf':
        try:
            try:
                import pdfplumber
                
                with pdfplumber.open(file_path) as pdf:
                    for page_num, page in enumerate(pdf.pages, 1):
                        paragraphs.append(f"页码 {page_num}")
                        text = page.extract_text()
                        if text:
                            for line in text.split('\n'):
                                if line.strip():
                                    paragraphs.append(f"  - {line.strip()}")
            except ImportError:
                try:
                    from PyPDF2 import PdfReader
                    
                    reader = PdfReader(file_path)
                    for page_num, page in enumerate(reader.pages, 1):
                        paragraphs.append(f"页码 {page_num}")
                        text = page.extract_text()
                        if text:
                            for line in text.split('\n'):
                                if line.strip():
                                    paragraphs.append(f"  - {line.strip()}")
                except ImportError:
                    pass
                except Exception as e:
                    logger.debug(f"操作失败: {e}")
            except Exception as e:
                logger.debug(f"操作失败: {e}")
        except Exception as e:
            logger.debug(f"操作失败: {e}")
    if paragraphs:
        return '\n'.join(paragraphs)
    else:
        return ''

class FileDiffService:
    """
    文件对比服务类
    实现文本文件和文件夹的差异对比功能
    """
    
    def __init__(self):
        """
        初始化文件对比服务
        """
        pass
    
    def compare_files(self, file1_path: str, file2_path: str, ignore_whitespace: bool = False, ignore_case: bool = False) -> Dict:
        """
        对比两个文件，根据文件类型选择合适的对比方式
        
        Args:
            file1_path: 第一个文件路径
            file2_path: 第二个文件路径
            ignore_whitespace: 是否忽略空格
            ignore_case: 是否忽略大小写
        
        Returns:
            Dict: 对比结果
        """
        try:
            # 检测文件类型
            file1_type = self._get_file_type(file1_path)
            file2_type = self._get_file_type(file2_path)
            
            # 允许文档文件与文本文件对比
            if not ((file1_type == 'document' and file2_type == 'text') or 
                    (file1_type == 'text' and file2_type == 'document') or 
                    (file1_type == file2_type)):
                return {
                    'success': False,
                    'error': '文件类型不同，无法直接对比'
                }
            
            # 根据文件类型选择对比方式
            if file1_type == 'text' and file2_type == 'document':
                # 文本文件与文档文件对比，先读取文档内容
                try:
                    import os
                    
                    # 读取文档的文本内容
                    doc_text = read_document_text(file2_path)
                    
                    # 临时保存为文本文件进行对比
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f2:
                        f2.write(doc_text)
                        temp_file2 = f2.name
                    
                    try:
                        # 使用文本对比方法对比
                        result = self.compare_text_files(file1_path, temp_file2, ignore_whitespace, ignore_case)
                        
                        # 修改结果中的文件类型
                        result['file_type'] = 'mixed'
                        return result
                    finally:
                        os.unlink(temp_file2)
                except Exception as e:
                    logger.debug(f"操作失败: {e}")
                    # 如果失败，使用二进制对比
                    result = self.compare_binary_files(file1_path, file2_path)
                    result['file_type'] = 'mixed'
                    return result
            elif file1_type == 'document' and file2_type == 'text':
                # 文档文件与文本文件对比，先读取文档内容
                try:
                    import os
                    
                    # 读取文档的文本内容
                    doc_text = read_document_text(file1_path)
                    
                    # 临时保存为文本文件进行对比
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f1:
                        f1.write(doc_text)
                        temp_file1 = f1.name
                    
                    try:
                        # 使用文本对比方法对比
                        result = self.compare_text_files(temp_file1, file2_path, ignore_whitespace, ignore_case)
                        
                        # 修改结果中的文件类型
                        result['file_type'] = 'mixed'
                        return result
                    finally:
                        os.unlink(temp_file1)
                except Exception as e:
                    logger.debug(f"操作失败: {e}")
                    # 如果失败，使用二进制对比
                    result = self.compare_binary_files(file1_path, file2_path)
                    result['file_type'] = 'mixed'
                    return result
            elif file1_type == 'text':
                return self.compare_text_files(file1_path, file2_path, ignore_whitespace, ignore_case)
            elif file1_type == 'image':
                return self.compare_image_files(file1_path, file2_path)
            elif file1_type == 'archive':
                return self.compare_archive_files(file1_path, file2_path)
            elif file1_type == 'media':
                return self.compare_media_files(file1_path, file2_path)
            elif file1_type == 'document':
                return self.compare_document_files(file1_path, file2_path)
            else:
                return self.compare_binary_files(file1_path, file2_path)
        
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def compare_text_files(self, file1_path: str, file2_path: str, ignore_whitespace: bool = False, ignore_case: bool = False) -> Dict:
        """
        对比两个文本文件
        
        Args:
            file1_path: 第一个文件路径
            file2_path: 第二个文件路径
            ignore_whitespace: 是否忽略空格
            ignore_case: 是否忽略大小写
        
        Returns:
            Dict: 对比结果，包含差异行信息
        """
        try:
            # 检查是否为临时文件（由compare_document_files创建）
            import os
            # 使用更安全的方式检查是否为临时文件
            import tempfile
            temp_dir = tempfile.gettempdir()
            is_temp_file1 = temp_dir in file1_path
            is_temp_file2 = temp_dir in file2_path
            
            # 对于临时文件，直接使用UTF-8编码
            if is_temp_file1 and is_temp_file2:
                # 读取文件内容
                with open(file1_path, 'r', encoding='utf-8', errors='replace') as f1:
                    file1_lines = f1.readlines()
                
                with open(file2_path, 'r', encoding='utf-8', errors='replace') as f2:
                    file2_lines = f2.readlines()
            else:
                # 对于普通文件，检测编码
                # 导入编码检测函数
                from core.utils import detect_file_encoding
                
                # 检测文件编码
                encoding1 = detect_file_encoding(file1_path)
                encoding2 = detect_file_encoding(file2_path)
                
                # 如果编码检测失败，使用默认编码
                if encoding1 == '未知':
                    encoding1 = 'utf-8'
                if encoding2 == '未知':
                    encoding2 = 'utf-8'
                
                # 读取文件内容
                with open(file1_path, 'r', encoding=encoding1, errors='replace') as f1:
                    file1_lines = f1.readlines()
                
                with open(file2_path, 'r', encoding=encoding2, errors='replace') as f2:
                    file2_lines = f2.readlines()
            
            # 处理忽略空格和大小写
            if ignore_whitespace or ignore_case:
                processed_file1_lines = []
                processed_file2_lines = []
                
                for line in file1_lines:
                    processed_line = line
                    if ignore_whitespace:
                        processed_line = processed_line.strip()
                    if ignore_case:
                        processed_line = processed_line.lower()
                    processed_file1_lines.append(processed_line)
                
                for line in file2_lines:
                    processed_line = line
                    if ignore_whitespace:
                        processed_line = processed_line.strip()
                    if ignore_case:
                        processed_line = processed_line.lower()
                    processed_file2_lines.append(processed_line)
            else:
                processed_file1_lines = file1_lines
                processed_file2_lines = file2_lines
            
            # 使用difflib进行对比
            differ = difflib.Differ()
            diff_result = list(differ.compare(processed_file1_lines, processed_file2_lines))
            
            # 分析差异结果
            diff_lines = []
            line_num1 = 1
            line_num2 = 1
            
            for line in diff_result:
                if line.startswith('  '):
                    # 相同行
                    diff_lines.append({
                        'type': 'equal',
                        'content': line[2:],
                        'line_num1': line_num1,
                        'line_num2': line_num2
                    })
                    line_num1 += 1
                    line_num2 += 1
                elif line.startswith('- '):
                    # 仅在文件1中存在的行
                    diff_lines.append({
                        'type': 'delete',
                        'content': line[2:],
                        'line_num1': line_num1,
                        'line_num2': None
                    })
                    line_num1 += 1
                elif line.startswith('+ '):
                    # 仅在文件2中存在的行
                    diff_lines.append({
                        'type': 'add',
                        'content': line[2:],
                        'line_num1': None,
                        'line_num2': line_num2
                    })
                    line_num2 += 1
                elif line.startswith('? '):
                    # 差异标记行，暂不处理
                    pass
            
            return {
                'success': True,
                'file1_path': file1_path,
                'file2_path': file2_path,
                'file_type': 'text',
                'diff_lines': diff_lines,
                'file1_lines': len(file1_lines),
                'file2_lines': len(file2_lines)
            }
        
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def compare_image_files(self, file1_path: str, file2_path: str) -> Dict:
        """
        对比两个图片文件
        
        Args:
            file1_path: 第一个文件路径
            file2_path: 第二个文件路径
        
        Returns:
            Dict: 对比结果
        """
        try:
            import os
            
            if not HAS_PIL:
                return {
                    'success': False,
                    'error': 'PIL库未安装，无法对比图片文件。请安装Pillow库：pip install Pillow'
                }
            
            # 获取图片信息
            with Image.open(file1_path) as img1:
                img1_info = {
                    'format': img1.format,
                    'size': img1.size,
                    'mode': img1.mode
                }
            
            with Image.open(file2_path) as img2:
                img2_info = {
                    'format': img2.format,
                    'size': img2.size,
                    'mode': img2.mode
                }
            
            # 比较图片信息
            is_same = img1_info == img2_info
            
            return {
                'success': True,
                'file1_path': file1_path,
                'file2_path': file2_path,
                'file_type': 'image',
                'file1_info': img1_info,
                'file2_info': img2_info,
                'is_same': is_same
            }
        
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def compare_archive_files(self, file1_path: str, file2_path: str) -> Dict:
        """
        对比两个压缩包文件
        
        Args:
            file1_path: 第一个文件路径
            file2_path: 第二个文件路径
        
        Returns:
            Dict: 对比结果
        """
        try:
            import zipfile
            import tarfile
            import os
            
            # 获取压缩包内文件信息
            file1_contents = self._get_archive_contents(file1_path)
            file2_contents = self._get_archive_contents(file2_path)
            
            # 比较压缩包内容
            common_files = list(set(file1_contents) & set(file2_contents))
            only_in_file1 = list(set(file1_contents) - set(file2_contents))
            only_in_file2 = list(set(file2_contents) - set(file1_contents))
            
            return {
                'success': True,
                'file1_path': file1_path,
                'file2_path': file2_path,
                'file_type': 'archive',
                'file1_contents': file1_contents,
                'file2_contents': file2_contents,
                'common_files': common_files,
                'only_in_file1': only_in_file1,
                'only_in_file2': only_in_file2,
                'is_same': len(only_in_file1) == 0 and len(only_in_file2) == 0
            }
        
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def compare_media_files(self, file1_path: str, file2_path: str) -> Dict:
        """
        对比两个音视频文件
        
        Args:
            file1_path: 第一个文件路径
            file2_path: 第二个文件路径
        
        Returns:
            Dict: 对比结果
        """
        try:
            import os
            
            # 读取音视频文件的详细信息
            def get_media_info(file_path):
                """
                读取音视频文件的详细信息
                """
                info = {
                    '大小': os.path.getsize(file_path),
                    '扩展名': os.path.splitext(file_path)[1].lower()
                }
                
                # 尝试使用mutagen库读取更多信息
                try:
                    from mutagen import File
                    
                    # 打开音视频文件
                    audio = File(file_path)
                    if audio:
                        # 基本信息
                        info['格式'] = audio.info.__class__.__name__
                        
                        # 音频信息
                        if hasattr(audio.info, 'bitrate'):
                            info['比特率'] = f"{audio.info.bitrate // 1000} kbps"
                        if hasattr(audio.info, 'length'):
                            info['时长'] = f"{audio.info.length:.2f} 秒"
                        if hasattr(audio.info, 'sample_rate'):
                            info['采样率'] = f"{audio.info.sample_rate} Hz"
                        if hasattr(audio.info, 'channels'):
                            info['声道数'] = audio.info.channels
                        if hasattr(audio.info, 'mode'):
                            info['模式'] = audio.info.mode
                        
                        # 视频信息
                        if hasattr(audio.info, 'video_codec'):
                            info['视频编码器'] = audio.info.video_codec
                        if hasattr(audio.info, 'resolution'):
                            info['分辨率'] = audio.info.resolution
                        if hasattr(audio.info, 'fps'):
                            info['帧率'] = audio.info.fps
                except ImportError:
                    # mutagen库未安装，只返回基本信息
                    pass
                except Exception as e:
                    # 读取失败，只返回基本信息
                    logger.debug(f"操作失败: {e}")
                return info
            
            # 获取文件信息
            file1_info = get_media_info(file1_path)
            file2_info = get_media_info(file2_path)
            
            # 比较文件信息
            is_same = file1_info == file2_info
            
            return {
                'success': True,
                'file1_path': file1_path,
                'file2_path': file2_path,
                'file_type': 'media',
                'file1_info': file1_info,
                'file2_info': file2_info,
                'is_same': is_same
            }
        
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def compare_document_files(self, file1_path: str, file2_path: str) -> Dict:
        """
        对比两个文档文件
        
        Args:
            file1_path: 第一个文件路径
            file2_path: 第二个文件路径
        
        Returns:
            Dict: 对比结果
        """
        try:
            import os
            
            # 读取两个文档的文本内容
            text1 = read_document_text(file1_path)
            text2 = read_document_text(file2_path)
            
            # 确保文本内容不为None
            if text1 is None:
                text1 = ''
            if text2 is None:
                text2 = ''
            
            # 临时保存为文本文件进行对比
            import tempfile
            import os
            
            # 创建临时文件
            temp_file1 = None
            temp_file2 = None
            
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f1:
                    f1.write(text1)
                    temp_file1 = f1.name
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f2:
                    f2.write(text2)
                    temp_file2 = f2.name
                
                # 确保临时文件存在
                if not temp_file1 or not os.path.exists(temp_file1):
                    raise Exception(f"临时文件创建失败: {temp_file1}")
                if not temp_file2 or not os.path.exists(temp_file2):
                    raise Exception(f"临时文件创建失败: {temp_file2}")
                
                # 使用文本对比方法对比提取的文本
                result = self.compare_text_files(temp_file1, temp_file2)
            finally:
                # 清理临时文件
                if temp_file1 and os.path.exists(temp_file1):
                    try:
                        os.unlink(temp_file1)
                    except Exception as e:
                        logger.debug(f"操作失败: {e}")
                if temp_file2 and os.path.exists(temp_file2):
                    try:
                        os.unlink(temp_file2)
                    except Exception as e:
                        logger.debug(f"操作失败: {e}")
            # 修改结果中的文件类型为document，并恢复原始文件路径
            result['file_type'] = 'document'
            result['file1_path'] = file1_path
            result['file2_path'] = file2_path
            return result
        
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            # 如果失败，使用二进制对比
            result = self.compare_binary_files(file1_path, file2_path)
            result['file_type'] = 'document'
            return result
    
    def compare_binary_files(self, file1_path: str, file2_path: str) -> Dict:
        """
        对比两个二进制文件
        
        Args:
            file1_path: 第一个文件路径
            file2_path: 第二个文件路径
        
        Returns:
            Dict: 对比结果
        """
        try:
            import os
            
            # 比较文件大小
            size1 = os.path.getsize(file1_path)
            size2 = os.path.getsize(file2_path)
            
            if size1 != size2:
                return {
                    'success': True,
                    'file1_path': file1_path,
                    'file2_path': file2_path,
                    'file_type': 'binary',
                    'file1_size': size1,
                    'file2_size': size2,
                    'is_same': False
                }
            
            # 比较文件内容（简单比较）
            with open(file1_path, 'rb') as f1, open(file2_path, 'rb') as f2:
                chunk_size = 4096
                while True:
                    chunk1 = f1.read(chunk_size)
                    chunk2 = f2.read(chunk_size)
                    if chunk1 != chunk2:
                        return {
                            'success': True,
                            'file1_path': file1_path,
                            'file2_path': file2_path,
                            'file_type': 'binary',
                            'file1_size': size1,
                            'file2_size': size2,
                            'is_same': False
                        }
                    if not chunk1:
                        break
            
            return {
                'success': True,
                'file1_path': file1_path,
                'file2_path': file2_path,
                'file_type': 'binary',
                'file1_size': size1,
                'file2_size': size2,
                'is_same': True
            }
        
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_file_type(self, file_path: str) -> str:
        """
        获取文件类型
        
        Args:
            file_path: 文件路径
        
        Returns:
            str: 文件类型
        """
        import os
        
        # 获取文件扩展名
        ext = os.path.splitext(file_path)[1].lower()
        
        # 文本文件
        text_extensions = ['.txt', '.log', '.py', '.json', '.yaml', '.yml', '.ini', '.csv', '.md',
                          '.html', '.css', '.js', '.xml', '.sql', '.java', '.c', '.cpp', '.h', '.hpp',
                          '.php', '.rb', '.go']
        
        # 图片文件
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.tiff']
        
        # 压缩包文件
        archive_extensions = ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz']
        
        # 音视频文件
        media_extensions = ['.mp3', '.wav', '.ogg', '.mp4', '.avi', '.mov', '.mkv', '.wmv']
        
        # 文档文件
        document_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.wps', '.et', '.dps']
        
        if ext in text_extensions:
            return 'text'
        elif ext in image_extensions:
            return 'image'
        elif ext in archive_extensions:
            return 'archive'
        elif ext in media_extensions:
            return 'media'
        elif ext in document_extensions:
            return 'document'
        else:
            return 'binary'
    
    def _get_archive_contents(self, archive_path: str) -> list:
        """
        获取压缩包内文件列表
        
        Args:
            archive_path: 压缩包路径
        
        Returns:
            list: 文件列表
        """
        from services.compression_service import compression_service
        
        try:
            # 使用压缩服务获取文件列表
            file_list = compression_service.get_file_list(archive_path)
            # 提取文件名列表
            return [file_info['name'] for file_info in file_list if not file_info.get('is_directory', False)]
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            # 如果压缩服务失败，使用备选方案
            import zipfile
            import tarfile
            import os
            
            contents = []
            
            # 尝试作为zip文件打开
            try:
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    for info in zf.infolist():
                        if not info.is_dir():
                            contents.append(info.filename)
                return contents
            except Exception as e:
                logger.debug(f"操作失败: {e}")
            
            # 尝试作为tar文件打开
            try:
                with tarfile.open(archive_path, 'r') as tf:
                    for member in tf.getmembers():
                        if member.isfile():
                            contents.append(member.name)
                return contents
            except Exception as e:
                logger.debug(f"操作失败: {e}")
            
            return contents
    
    def compare_folders(self, folder1_path: str, folder2_path: str) -> Dict:
        """
        对比两个文件夹
        
        Args:
            folder1_path: 第一个文件夹路径
            folder2_path: 第二个文件夹路径
        
        Returns:
            Dict: 对比结果，包含共同文件、仅左侧存在文件、仅右侧存在文件
        """
        try:
            # 获取文件夹中的所有文件
            def get_all_files(folder_path: str) -> List[str]:
                files = []
                for root, _, filenames in os.walk(folder_path):
                    for filename in filenames:
                        # 获取相对路径
                        rel_path = os.path.relpath(os.path.join(root, filename), folder_path)
                        files.append(rel_path)
                return files
            
            folder1_files = get_all_files(folder1_path)
            folder2_files = get_all_files(folder2_path)
            
            # 找出共同文件、仅左侧存在文件、仅右侧存在文件
            common_files = list(set(folder1_files) & set(folder2_files))
            only_in_folder1 = list(set(folder1_files) - set(folder2_files))
            only_in_folder2 = list(set(folder2_files) - set(folder1_files))
            
            # 对结果进行排序
            common_files.sort()
            only_in_folder1.sort()
            only_in_folder2.sort()
            
            return {
                'success': True,
                'folder1_path': folder1_path,
                'folder2_path': folder2_path,
                'common_files': common_files,
                'only_in_folder1': only_in_folder1,
                'only_in_folder2': only_in_folder2,
                'total_files': {
                    'folder1': len(folder1_files),
                    'folder2': len(folder2_files),
                    'common': len(common_files),
                    'different': len(only_in_folder1) + len(only_in_folder2)
                }
            }
        
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def export_diff_report(self, diff_result: Dict, output_path: str, report_type: str = 'txt') -> bool:
        """
        导出差异报告
        
        Args:
            diff_result: 对比结果
            output_path: 输出文件路径
            report_type: 报告类型，可选值：'txt', 'html'
        
        Returns:
            bool: 导出是否成功
        """
        try:
            if not diff_result.get('success', False):
                return False
            
            if report_type == 'txt':
                return self._export_txt_report(diff_result, output_path)
            elif report_type == 'html':
                return self._export_html_report(diff_result, output_path)
            else:
                return False
        
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return False
    
    def _export_txt_report(self, diff_result: Dict, output_path: str) -> bool:
        """
        导出TXT格式的差异报告
        
        Args:
            diff_result: 对比结果
            output_path: 输出文件路径
        
        Returns:
            bool: 导出是否成功
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                # 写入报告头部
                f.write(f"文件对比报告\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                
                if 'file1_path' in diff_result:
                    # 文本文件对比报告
                    f.write(f"文件1: {diff_result['file1_path']}\n")
                    f.write(f"文件2: {diff_result['file2_path']}\n")
                    f.write("-" * 80 + "\n\n")
                    
                    # 写入对比结果
                    for line in diff_result['diff_lines']:
                        if line['type'] == 'equal':
                            f.write(f"  {line['content']}")
                        elif line['type'] == 'delete':
                            f.write(f"- {line['content']}")
                        elif line['type'] == 'add':
                            f.write(f"+ {line['content']}")
                    
                    f.write("\n" + "-" * 80 + "\n\n")
                    
                    # 写入分析结果
                    f.write("对比分析结果:\n")
                    f.write("-" * 40 + "\n")
                    
                    # 计算分析结果
                    analysis_results = self._analyze_diff_result(diff_result)
                    for key, value in analysis_results.items():
                        f.write(f"{key}: {value}\n")
                    
                    f.write("\n" + "-" * 80 + "\n\n")
                    
                    # 写入图例说明
                    f.write("对比图例:\n")
                    f.write("-" * 40 + "\n")
                    f.write("- 红色: 删除的内容\n")
                    f.write("- 绿色: 添加的内容\n")
                    f.write("- 蓝色: 修改的内容\n")
                    f.write("- 灰色: 相同的内容\n")
                
                elif 'folder1_path' in diff_result:
                    # 文件夹对比报告
                    f.write(f"文件夹1: {diff_result['folder1_path']}\n")
                    f.write(f"文件夹2: {diff_result['folder2_path']}\n")
                    f.write("-" * 80 + "\n\n")
                    
                    f.write(f"共同文件 ({len(diff_result['common_files'])}):\n")
                    for file in diff_result['common_files']:
                        f.write(f"  {file}\n")
                    f.write("\n")
                    
                    f.write(f"仅在文件夹1中存在 ({len(diff_result['only_in_folder1'])}):\n")
                    for file in diff_result['only_in_folder1']:
                        f.write(f"  {file}\n")
                    f.write("\n")
                    
                    f.write(f"仅在文件夹2中存在 ({len(diff_result['only_in_folder2'])}):\n")
                    for file in diff_result['only_in_folder2']:
                        f.write(f"  {file}\n")
                    
                    f.write("\n" + "-" * 80 + "\n\n")
                    
                    # 写入分析结果
                    f.write("对比分析结果:\n")
                    f.write("-" * 40 + "\n")
                    
                    # 计算分析结果
                    analysis_results = self._analyze_diff_result(diff_result)
                    for key, value in analysis_results.items():
                        f.write(f"{key}: {value}\n")
            
            return True
        
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return False
    
    def _export_html_report(self, diff_result: Dict, output_path: str) -> bool:
        """
        导出HTML格式的差异报告
        
        Args:
            diff_result: 对比结果
            output_path: 输出文件路径
        
        Returns:
            bool: 导出是否成功
        """
        try:
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>文件对比报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2 {{ color: #333; }}
        .header {{ background-color: #f0f0f0; padding: 10px; margin-bottom: 20px; border-radius: 5px; }}
        .diff-container {{ border: 1px solid #ddd; border-radius: 5px; overflow: hidden; margin-bottom: 20px; }}
        .diff-header {{ background-color: #f5f5f5; padding: 10px; border-bottom: 1px solid #ddd; }}
        .diff-content {{ font-family: 'Courier New', monospace; white-space: pre-wrap; }}
        .line {{ padding: 2px 5px; }}
        .equal {{ background-color: #ffffff; }}
        .add {{ background-color: #d4edda; color: #155724; }}
        .delete {{ background-color: #f8d7da; color: #721c24; }}
        .file-list {{ list-style-type: none; padding: 0; }}
        .file-list li {{ padding: 5px; border-bottom: 1px solid #eee; }}
        .common {{ background-color: #e7f3ff; }}
        .only-folder1 {{ background-color: #fff3e0; }}
        .only-folder2 {{ background-color: #f3e5f5; }}
        .analysis-container {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .analysis-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-top: 10px; }}
        .analysis-item {{ background-color: #ffffff; padding: 10px; border-radius: 3px; border: 1px solid #ddd; }}
        .legend-container {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .legend-grid {{ display: flex; flex-wrap: wrap; gap: 20px; margin-top: 10px; }}
        .legend-item {{ display: flex; align-items: center; }}
        .legend-color {{ width: 20px; height: 20px; margin-right: 8px; border-radius: 2px; }}
        .legend-text {{ font-size: 14px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>文件对比报告</h1>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
"""
            
            if 'file1_path' in diff_result:
                # 文本文件对比报告
                html += f"""
    <h2>文本文件对比</h2>
    <div class="diff-container">
        <div class="diff-header">
            <p><strong>文件1:</strong> {diff_result['file1_path']}</p>
            <p><strong>文件2:</strong> {diff_result['file2_path']}</p>
        </div>
        <div class="diff-content">
"""
                
                for line in diff_result['diff_lines']:
                    line_class = line['type']
                    line_content = line['content'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    html += f"<div class='line {line_class}'>{line_content}</div>"
                
                html += """
        </div>
    </div>
"""
            
            elif 'folder1_path' in diff_result:
                # 文件夹对比报告
                html += f"""
    <h2>文件夹对比</h2>
    <div class="diff-container">
        <div class="diff-header">
            <p><strong>文件夹1:</strong> {diff_result['folder1_path']}</p>
            <p><strong>文件夹2:</strong> {diff_result['folder2_path']}</p>
        </div>
        <div style="padding: 10px;">
            <h3>共同文件 ({len(diff_result['common_files'])}):</h3>
            <ul class="file-list">
"""
                
                for file in diff_result['common_files']:
                    html += f"<li class='file-list-item common'>{file}</li>"
                
                html += f"""
            </ul>
            <h3>仅在文件夹1中存在 ({len(diff_result['only_in_folder1'])}):</h3>
            <ul class="file-list">
"""
                
                for file in diff_result['only_in_folder1']:
                    html += f"<li class='file-list-item only-folder1'>{file}</li>"
                
                html += f"""
            </ul>
            <h3>仅在文件夹2中存在 ({len(diff_result['only_in_folder2'])}):</h3>
            <ul class="file-list">
"""
                
                for file in diff_result['only_in_folder2']:
                    html += f"<li class='file-list-item only-folder2'>{file}</li>"
                
                html += """
            </ul>
        </div>
    </div>
"""
            
            # 添加分析结果
            html += """
    <h2>对比分析结果</h2>
    <div class="analysis-container">
        <div class="analysis-grid">
"""
            
            # 计算分析结果
            analysis_results = self._analyze_diff_result(diff_result)
            for key, value in analysis_results.items():
                html += f"<div class='analysis-item'><strong>{key}:</strong> {value}</div>"
            
            html += """
        </div>
    </div>
    
    <h2>对比图例</h2>
    <div class="legend-container">
        <div class="legend-grid">
            <div class="legend-item">
                <div class="legend-color" style="background-color: #f8d7da;"></div>
                <div class="legend-text">删除的内容</div>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #d4edda;"></div>
                <div class="legend-text">添加的内容</div>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #cce7ff;"></div>
                <div class="legend-text">修改的内容</div>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #ffffff;"></div>
                <div class="legend-text">相同的内容</div>
            </div>
        </div>
    </div>
</body>
</html>
"""
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            return True
        
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return False

    def _analyze_diff_result(self, diff_result: Dict) -> Dict:
        """
        分析对比结果，生成统计信息
        
        Args:
            diff_result: 对比结果
        
        Returns:
            dict: 分析结果字典
        """
        import os
        from datetime import datetime
        
        analysis_results = {}
        
        # 添加对比时间戳
        analysis_results['对比时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if 'diff_lines' in diff_result:
            # 文本文件对比分析
            diff_lines = diff_result['diff_lines']
            total_lines = len(diff_lines)
            
            # 统计不同类型的修改
            added_lines = 0
            deleted_lines = 0
            same_lines = 0
            total_chars = 0
            
            for line in diff_lines:
                if line['type'] == 'add':
                    added_lines += 1
                    total_chars += len(line.get('content', ''))
                elif line['type'] == 'delete':
                    deleted_lines += 1
                    total_chars += len(line.get('content', ''))
                elif line['type'] == 'equal':
                    same_lines += 1
                    total_chars += len(line.get('content', ''))
            
            # 计算相似度
            similarity = (same_lines / total_lines * 100) if total_lines > 0 else 0
            
            # 构建分析结果
            analysis_results.update({
                '文件类型': '文本文件',
                '总行数': total_lines,
                '总字符数': total_chars,
                '相同行数': same_lines,
                '添加行数': added_lines,
                '删除行数': deleted_lines,
                '相似度': f"{similarity:.2f}%",
                '修改率': f"{((added_lines + deleted_lines) / total_lines * 100):.2f}%" if total_lines > 0 else "0.00%"
            })
        elif 'folder1_path' in diff_result:
            # 文件夹对比分析
            common_files = diff_result['common_files']
            only_in_folder1 = diff_result['only_in_folder1']
            only_in_folder2 = diff_result['only_in_folder2']
            
            total_files = len(common_files) + len(only_in_folder1) + len(only_in_folder2)
            similarity = (len(common_files) / total_files * 100) if total_files > 0 else 0
            
            # 构建分析结果
            analysis_results.update({
                '文件类型': '文件夹',
                '总文件数': total_files,
                '共同文件数': len(common_files),
                '仅在左侧文件夹': len(only_in_folder1),
                '仅在右侧文件夹': len(only_in_folder2),
                '相似度': f"{similarity:.2f}%",
                '差异率': f"{((len(only_in_folder1) + len(only_in_folder2)) / total_files * 100):.2f}%" if total_files > 0 else "0.00%"
            })
        
        # 添加文件路径信息
        if 'file1_path' in diff_result:
            analysis_results['左侧文件'] = os.path.basename(diff_result['file1_path'])
        if 'file2_path' in diff_result:
            analysis_results['右侧文件'] = os.path.basename(diff_result['file2_path'])
        
        return analysis_results

# 创建文件对比服务实例
file_diff_service = FileDiffService()
