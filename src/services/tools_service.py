#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辅助工具服务模块
实现批量重命名、文件编码转换、图片格式转换和文件校验功能
"""

import os
import re
import hashlib
import concurrent.futures
from typing import Dict, List, Optional, Union
from core.logger import logger

_chardet_imported = False
try:
    import chardet
    _chardet_imported = True
except ImportError:
    chardet = None  # type: ignore[assignment]
HAS_CHARDET: bool = _chardet_imported

_pil_imported = False
try:
    from PIL import Image
    _pil_imported = True
    try:
        _LANCZOS = Image.Resampling.LANCZOS
    except AttributeError:
        # Pillow < 10 fallback
        _LANCZOS = Image.LANCZOS  # pyright: ignore[reportConstantRedefinition,reportAttributeAccessIssue]
except ImportError:
    Image = None  # type: ignore[assignment]
HAS_PIL: bool = _pil_imported

class BatchRenamer:
    """
    批量重命名工具类
    """
    
    def __init__(self):
        """
        初始化批量重命名工具
        """
        self.rename_patterns = {
            "prefix": self._add_prefix,
            "suffix": self._add_suffix,
            "replace": self._replace_text,
            "serial": self._add_serial_number
        }
    
    def rename_files(self, files: List[str], rename_type: str, **kwargs) -> Dict[str, str]:
        """
        批量重命名文件
        
        Args:
            files: 文件路径列表
            rename_type: 重命名类型 (prefix, suffix, replace, serial)
            **kwargs: 额外参数
        
        Returns:
            Dict[str, str]: 原路径到新路径的映射
        """
        if rename_type not in self.rename_patterns:
            raise ValueError(f"不支持的重命名类型: {rename_type}")
        
        rename_func = self.rename_patterns[rename_type]
        result = {}
        
        for i, file_path in enumerate(files):
            new_path = rename_func(file_path, i, **kwargs)
            if new_path != file_path:
                result[file_path] = new_path
        
        return result
    
    def _add_prefix(self, file_path: str, index: int, prefix: str) -> str:
        """
        添加前缀
        
        Args:
            file_path: 文件路径
            index: 文件索引
            prefix: 前缀文本
        
        Returns:
            str: 新文件路径
        """
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)
        new_filename = f"{prefix}{name}{ext}"
        return os.path.join(directory, new_filename)
    
    def _add_suffix(self, file_path: str, index: int, suffix: str) -> str:
        """
        添加后缀
        
        Args:
            file_path: 文件路径
            index: 文件索引
            suffix: 后缀文本
        
        Returns:
            str: 新文件路径
        """
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)
        new_filename = f"{name}{suffix}{ext}"
        return os.path.join(directory, new_filename)
    
    def _replace_text(self, file_path: str, index: int, old_text: str, new_text: str) -> str:
        """
        替换文本
        
        Args:
            file_path: 文件路径
            index: 文件索引
            old_text: 旧文本
            new_text: 新文本
        
        Returns:
            str: 新文件路径
        """
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        new_filename = filename.replace(old_text, new_text)
        return os.path.join(directory, new_filename)
    
    def _add_serial_number(self, file_path: str, index: int, start: int = 1, padding: int = 3, separator: str = "_") -> str:
        """
        添加序号
        
        Args:
            file_path: 文件路径
            index: 文件索引
            start: 起始序号
            padding: 序号填充长度
            separator: 分隔符
        
        Returns:
            str: 新文件路径
        """
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)
        serial_number = str(start + index).zfill(padding)
        new_filename = f"{name}{separator}{serial_number}{ext}"
        return os.path.join(directory, new_filename)
    
    def preview_rename(self, files: List[str], rename_type: str, **kwargs) -> Dict[str, str]:
        """
        预览重命名结果
        
        Args:
            files: 文件路径列表
            rename_type: 重命名类型
            **kwargs: 额外参数
        
        Returns:
            Dict[str, str]: 原路径到新路径的映射
        """
        return self.rename_files(files, rename_type, **kwargs)
    
    def execute_rename(self, rename_map: Dict[str, str]) -> List[str]:
        """
        执行重命名操作
        
        Args:
            rename_map: 原路径到新路径的映射
        
        Returns:
            List[str]: 重命名失败的文件路径
        """
        failed = []
        
        for old_path, new_path in rename_map.items():
            try:
                # 检查新路径是否已存在
                if os.path.exists(new_path):
                    failed.append(old_path)
                    continue
                
                os.rename(old_path, new_path)
            except Exception as e:
                logger.debug(f"重命名失败: {old_path} -> {e}")
                failed.append(old_path)
        
        return failed

class EncodingConverter:
    """
    文件编码转换工具类
    """
    
    def __init__(self):
        """
        初始化编码转换工具
        """
        pass
    
    def detect_encoding(self, file_path: str) -> str:
        """
        检测文件编码
        
        Args:
            file_path: 文件路径
        
        Returns:
            str: 检测到的编码
        """
        with open(file_path, 'rb') as f:
            raw_data = f.read(1024 * 1024)  # 读取前1MB数据
            if HAS_CHARDET and chardet is not None:
                result = chardet.detect(raw_data)
                if result and result.get('encoding'):
                    return str(result['encoding'])
                return 'utf-8'
            else:
                for enc in ['utf-8', 'gbk', 'latin-1']:
                    try:
                        raw_data.decode(enc)
                        return enc
                    except (UnicodeDecodeError, LookupError):
                        continue
                return 'utf-8'
    
    def convert_encoding(self, files: List[str], target_encoding: str, backup: bool = False) -> Dict[str, str]:
        """
        批量转换文件编码
        
        Args:
            files: 文件路径列表
            target_encoding: 目标编码
            backup: 是否备份原文件
        
        Returns:
            Dict[str, str]: 转换结果，键为文件路径，值为状态
        """
        result = {}
        
        for file_path in files:
            try:
                # 检测原编码
                source_encoding = self.detect_encoding(file_path)
                
                # 读取文件内容
                with open(file_path, 'r', encoding=source_encoding, errors='replace') as f:
                    content = f.read()
                
                # 备份原文件
                if backup:
                    backup_path = f"{file_path}.bak"
                    with open(backup_path, 'w', encoding=source_encoding) as f:
                        f.write(content)
                
                # 写入新编码
                with open(file_path, 'w', encoding=target_encoding) as f:
                    f.write(content)
                
                result[file_path] = f"成功: {source_encoding} → {target_encoding}"
            except Exception as e:
                result[file_path] = f"失败: {str(e)}"
        
        return result
    
    def preview_conversion(self, file_path: str, target_encoding: str) -> str:
        """
        预览编码转换结果
        
        Args:
            file_path: 文件路径
            target_encoding: 目标编码
        
        Returns:
            str: 预览结果
        """
        try:
            source_encoding = self.detect_encoding(file_path)
            with open(file_path, 'r', encoding=source_encoding, errors='replace') as f:
                content = f.read(1000)  # 读取前1000个字符
            
            # 尝试转换
            converted = content.encode(target_encoding, errors='replace').decode(target_encoding)
            return f"原编码: {source_encoding}\n目标编码: {target_encoding}\n\n转换预览:\n{converted}"
        except Exception as e:
            logger.debug(f"编码转换预览失败: {e}")
            return f"预览失败: {str(e)}"

class ImageConverter:
    """
    图片格式转换工具类
    """
    
    def __init__(self):
        """
        初始化图片转换工具
        """
        self.supported_formats = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
    
    def convert_format(self, files: List[str], target_format: str, quality: int = 85, 
                      resize: Optional[tuple[int, int]] = None, overwrite: bool = False) -> Dict[str, str]:
        """
        批量转换图片格式
        
        Args:
            files: 图片文件路径列表
            target_format: 目标格式
            quality: 图片质量 (1-100)
            resize: 调整大小 (width, height)
            overwrite: 是否覆盖原文件
        
        Returns:
            Dict[str, str]: 转换结果
        """
        target_format = target_format.lower()
        if target_format not in self.supported_formats:
            raise ValueError(f"不支持的图片格式: {target_format}")
        
        result = {}
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {}
            
            for file_path in files:
                future = executor.submit(
                    self._convert_single_image,
                    file_path, target_format, quality, resize, overwrite
                )
                futures[future] = file_path
            
            for future in concurrent.futures.as_completed(futures):
                file_path = futures[future]
                try:
                    status, output_path = future.result()
                    result[file_path] = status
                except Exception as e:
                    result[file_path] = f"失败: {str(e)}"
        
        return result
    
    def _convert_single_image(self, file_path: str, target_format: str, quality: int, 
                             resize: Optional[tuple[int, int]], overwrite: bool) -> tuple[str, str]:
        """
        转换单个图片
        
        Args:
            file_path: 图片路径
            target_format: 目标格式
            quality: 图片质量
            resize: 调整大小
            overwrite: 是否覆盖
        
        Returns:
            tuple: (状态, 输出路径)
        """
        if not HAS_PIL or Image is None:
            raise ImportError("Pillow模块未安装，请安装Pillow以支持图片转换功能: pip install Pillow")
        
        try:
            # 打开图片
            with Image.open(file_path) as img:
                
                # 调整大小
                if resize:
                    img = img.resize(resize, _LANCZOS)
                
                # 确定输出路径
                if overwrite:
                    output_path = os.path.splitext(file_path)[0] + f".{target_format}"
                else:
                    directory = os.path.dirname(file_path)
                    filename = os.path.basename(file_path)
                    name, _ = os.path.splitext(filename)
                    output_path = os.path.join(directory, f"{name}_converted.{target_format}")
                
                # 保存图片
                if target_format == 'jpg' or target_format == 'jpeg':
                    img = img.convert('RGB')
                    img.save(output_path, quality=quality, optimize=True)
                else:
                    img.save(output_path, quality=quality, optimize=True)
                
                return f"成功: {output_path}", output_path
        except Exception as e:
            raise e
    
    def get_image_info(self, file_path: str) -> Dict[str, str]:
        """
        获取图片信息
        
        Args:
            file_path: 图片路径
        
        Returns:
            Dict[str, str]: 图片信息
        """
        if not HAS_PIL or Image is None:
            return {'错误': 'Pillow模块未安装，请安装Pillow以支持图片信息功能: pip install Pillow'}
        
        try:
            with Image.open(file_path) as img:
                return {
                    '格式': img.format,
                    '尺寸': f"{img.width}x{img.height}",
                    '模式': img.mode,
                    '大小': f"{os.path.getsize(file_path) / 1024:.2f} KB",

                }
        except Exception as e:
            logger.debug(f"获取图片信息失败: {e}")
            return {'错误': str(e)}

class FileVerifier:
    """
    文件校验工具类
    """
    
    def __init__(self):
        """
        初始化文件校验工具
        """
        self.hash_algorithms = {
            'md5': hashlib.md5,
            'sha1': hashlib.sha1,
            'sha256': hashlib.sha256
        }
    
    def calculate_hash(self, files: List[str], algorithm: str) -> Dict[str, str]:
        """
        批量计算文件哈希值
        
        Args:
            files: 文件路径列表
            algorithm: 哈希算法 (md5, sha1, sha256)
        
        Returns:
            Dict[str, str]: 文件路径到哈希值的映射
        """
        if algorithm not in self.hash_algorithms:
            raise ValueError(f"不支持的哈希算法: {algorithm}")
        
        hash_func = self.hash_algorithms[algorithm]
        result = {}
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {}
            
            for file_path in files:
                future = executor.submit(self._calculate_single_hash, file_path, hash_func)
                futures[future] = file_path
            
            for future in concurrent.futures.as_completed(futures):
                file_path = futures[future]
                try:
                    hash_value = future.result()
                    result[file_path] = hash_value
                except Exception as e:
                    result[file_path] = f"错误: {str(e)}"
        
        return result
    
    def _calculate_single_hash(self, file_path: str, hash_func) -> str:
        """
        计算单个文件的哈希值
        
        Args:
            file_path: 文件路径
            hash_func: 哈希函数
        
        Returns:
            str: 哈希值
        """
        hash_obj = hash_func()
        block_size = 8192
        
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(block_size)
                if not data:
                    break
                hash_obj.update(data)
        
        return hash_obj.hexdigest()
    
    def verify_hash(self, file_path: str, expected_hash: str, algorithm: str) -> bool:
        """
        验证文件哈希值
        
        Args:
            file_path: 文件路径
            expected_hash: 期望的哈希值
            algorithm: 哈希算法
        
        Returns:
            bool: 是否匹配
        """
        calculated_hash = self.calculate_hash([file_path], algorithm).get(file_path)
        return calculated_hash == expected_hash
    
    def generate_verification_report(self, files: List[str], algorithm: str) -> str:
        """
        生成校验报告
        
        Args:
            files: 文件路径列表
            algorithm: 哈希算法
        
        Returns:
            str: 校验报告
        """
        hashes = self.calculate_hash(files, algorithm)
        report = f"文件校验报告\n算法: {algorithm}\n\n"
        
        for file_path, hash_value in hashes.items():
            filename = os.path.basename(file_path)
            report += f"{filename}: {hash_value}\n"
        
        return report

class FileMerger:
    """
    文件合并器
    
    将多个文本/同类型文件按自然顺序合并为一个文档。
    """
    
    @staticmethod
    def natural_sort_key(name: str) -> List[Union[str, int]]:
        """
        生成自然排序 key，使数字按数值大小排序（ch01 < ch02 < ch10）
        """
        return [int(part) if part.isdigit() else part.lower()
                for part in re.split(r'(\d+)', os.path.basename(name)) if part != '']
    
    def merge_files(self, files: List[str], output_path: str,
                    insert_title: bool = False, insert_blank: bool = False,
                    progress_callback=None) -> Dict[str, object]:
        """
        将多个文件按自然顺序合并写入 output_path
        
        Args:
            files: 待合并文件路径列表
            output_path: 输出文件路径
            insert_title: 每个文件内容前是否插入文件名分隔标题
            insert_blank: 文件之间是否插入空行分隔
            progress_callback: 进度回调函数 callback(current, total, filename)
        
        Returns:
            Dict: 包含 success / output_path / count / total_size / message 的状态字典
        """
        if not files:
            return {"success": False, "message": "未选择任何文件"}
        
        unique_files = []
        seen = set()
        for f in files:
            if f not in seen:
                seen.add(f)
                unique_files.append(f)
        
        sorted_files = sorted(unique_files, key=self.natural_sort_key)
        
        if os.path.exists(output_path):
            return {"success": False, "message": f"输出文件已存在，请更换文件名或删除已存在的文件：\n{output_path}"}
        
        try:
            total_size = 0
            merged_count = 0
            with open(output_path, 'w', encoding='utf-8', newline='') as out:
                for idx, src in enumerate(sorted_files):
                    if not os.path.isfile(src):
                        continue
                    if progress_callback:
                        progress_callback(idx + 1, len(sorted_files), os.path.basename(src))
                    if insert_title:
                        out.write(f"# {os.path.basename(src)}\n\n")
                    try:
                        encoding = self._detect_src_encoding(src)
                        with open(src, 'r', encoding=encoding, errors='replace', newline='') as fin:
                            content = fin.read()
                    except Exception:
                        with open(src, 'rb') as fb:
                            content = fb.read().decode('utf-8', errors='replace')
                    out.write(content)
                    if not content.endswith('\n'):
                        out.write('\n')
                    if insert_blank and idx < len(sorted_files) - 1:
                        out.write('\n')
                    total_size += os.path.getsize(src)
                    merged_count += 1
            return {
                "success": True,
                "output_path": output_path,
                "count": merged_count,
                "total_size": total_size,
                "message": f"已合并 {merged_count} 个文件 -> {output_path}"
            }
        except Exception as e:
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
            except Exception:
                pass
            return {"success": False, "message": f"合并失败：{str(e)}"}
    
    def _detect_src_encoding(self, file_path: str) -> str:
        """
        检测源文件编码（尽量复用外部检测能力，失败返回 utf-8）
        """
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(1024 * 1024)
            if HAS_CHARDET and chardet is not None:
                result = chardet.detect(raw_data)
                if result and result.get('encoding'):
                    return str(result['encoding'])
                return 'utf-8'
            else:
                for enc in ['utf-8', 'gbk', 'latin-1']:
                    try:
                        raw_data.decode(enc)
                        return enc
                    except (UnicodeDecodeError, LookupError):
                        continue
                return 'utf-8'
        except Exception:
            return 'utf-8'

class ToolsService:
    """
    辅助工具服务类
    """
    
    def __init__(self):
        """
        初始化工具服务
        """
        self.batch_renamer = BatchRenamer()
        self.encoding_converter = EncodingConverter()
        self.image_converter = ImageConverter()
        self.file_verifier = FileVerifier()
        self.file_merger = FileMerger()
    
    # 批量重命名相关方法
    def batch_rename(self, files: List[str], rename_type: str, **kwargs) -> Dict[str, str]:
        """
        批量重命名文件
        """
        return self.batch_renamer.rename_files(files, rename_type, **kwargs)
    
    def preview_rename(self, files: List[str], rename_type: str, **kwargs) -> Dict[str, str]:
        """
        预览重命名结果
        """
        return self.batch_renamer.preview_rename(files, rename_type, **kwargs)
    
    def execute_rename(self, rename_map: Dict[str, str]) -> List[str]:
        """
        执行重命名操作
        """
        return self.batch_renamer.execute_rename(rename_map)
    
    # 编码转换相关方法
    def detect_encoding(self, file_path: str) -> str:
        """
        检测文件编码
        """
        return self.encoding_converter.detect_encoding(file_path)
    
    def convert_encoding(self, files: List[str], target_encoding: str, backup: bool = False) -> Dict[str, str]:
        """
        批量转换文件编码
        """
        return self.encoding_converter.convert_encoding(files, target_encoding, backup)
    
    def preview_conversion(self, file_path: str, target_encoding: str) -> str:
        """
        预览编码转换结果
        """
        return self.encoding_converter.preview_conversion(file_path, target_encoding)
    
    # 图片转换相关方法
    def convert_image_format(self, files: List[str], target_format: str, quality: int = 85, 
                           resize: Optional[tuple[int, int]] = None, overwrite: bool = False) -> Dict[str, str]:
        """
        批量转换图片格式
        """
        return self.image_converter.convert_format(files, target_format, quality, resize, overwrite)
    
    def get_image_info(self, file_path: str) -> Dict[str, str]:
        """
        获取图片信息
        """
        return self.image_converter.get_image_info(file_path)
    
    # 文件校验相关方法
    def calculate_file_hash(self, files: List[str], algorithm: str) -> Dict[str, str]:
        """
        批量计算文件哈希值
        """
        return self.file_verifier.calculate_hash(files, algorithm)
    
    def verify_file_hash(self, file_path: str, expected_hash: str, algorithm: str) -> bool:
        """
        验证文件哈希值
        """
        return self.file_verifier.verify_hash(file_path, expected_hash, algorithm)
    
    def generate_verification_report(self, files: List[str], algorithm: str) -> str:
        """
        生成校验报告
        """
        return self.file_verifier.generate_verification_report(files, algorithm)
    
    # 文件合并相关方法
    def merge_files(self, files: List[str], output_path: str,
                    insert_title: bool = False, insert_blank: bool = False,
                    progress_callback=None) -> Dict[str, object]:
        """
        合并多个文件为一个文档
        """
        return self.file_merger.merge_files(files, output_path, insert_title, insert_blank, progress_callback)

# 创建工具服务实例
tools_service = ToolsService()
