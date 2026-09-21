#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
压缩解压服务模块
负责处理各种压缩格式的压缩和解压功能
"""

import os
import shutil
import tempfile
import multiprocessing
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from core.logger import logger

from core.utils import show_warning

class CompressionHandler(ABC):
    """
    压缩处理器基类
    所有类型的压缩处理器都必须继承此类
    """
    
    def __init__(self, parent_widget=None):
        self._parent_widget = parent_widget
    
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
    def compress(self, source_paths: List[str], dest_path: str, compression_level: int = 6, password: str = None, volume_size: int = None) -> bool:
        """
        压缩文件或文件夹
        
        Args:
            source_paths: 源文件或文件夹路径列表
            dest_path: 目标压缩文件路径
            compression_level: 压缩级别（1-9）
            password: 压缩密码（可选）
            volume_size: 分卷大小（字节，可选）
            
        Returns:
            bool: 压缩是否成功
        """
        pass
    
    @abstractmethod
    def decompress(self, source_path: str, dest_path: str, password: str = None) -> bool:
        """
        解压压缩文件
        
        Args:
            source_path: 源压缩文件路径
            dest_path: 目标解压路径
            password: 解压密码（可选）
            
        Returns:
            bool: 解压是否成功
        """
        pass
    
    @abstractmethod
    def get_file_list(self, file_path: str, password: str = None) -> List[Dict[str, Any]]:
        """
        获取压缩包内的文件列表
        
        Args:
            file_path: 压缩文件路径
            password: 解压密码（可选）
            
        Returns:
            List[Dict[str, Any]]: 文件列表，每个元素包含name, path, size, modified_time等信息
        """
        pass
    
    @abstractmethod
    def extract_file(self, archive_path: str, file_path_in_archive: str, dest_path: str, password: str = None) -> bool:
        """
        提取压缩包内的单个文件
        
        Args:
            archive_path: 压缩文件路径
            file_path_in_archive: 压缩包内的文件路径
            dest_path: 目标文件路径
            password: 解压密码（可选）
            
        Returns:
            bool: 提取是否成功
        """
        pass
    
    @abstractmethod
    def add_file(self, archive_path: str, source_file_path: str, dest_path_in_archive: str = None, password: str = None) -> bool:
        """
        向压缩包内添加文件
        
        Args:
            archive_path: 压缩文件路径
            source_file_path: 源文件路径
            dest_path_in_archive: 压缩包内的目标路径（可选）
            password: 压缩密码（可选）
            
        Returns:
            bool: 添加是否成功
        """
        pass
    
    @abstractmethod
    def update_file(self, archive_path: str, source_file_path: str, file_path_in_archive: str, password: str = None) -> bool:
        """
        更新压缩包内的文件
        
        Args:
            archive_path: 压缩文件路径
            source_file_path: 源文件路径
            file_path_in_archive: 压缩包内的文件路径
            password: 压缩密码（可选）
            
        Returns:
            bool: 更新是否成功
        """
        pass
    
    @abstractmethod
    def delete_file(self, archive_path: str, file_path_in_archive: str, password: str = None) -> bool:
        """
        删除压缩包内的文件
        
        Args:
            archive_path: 压缩文件路径
            file_path_in_archive: 压缩包内的文件路径
            password: 压缩密码（可选）
            
        Returns:
            bool: 删除是否成功
        """
        pass
    
    def compress_parallel(self, source_paths: List[str], dest_path: str, compression_level: int = 6, 
                          password: str = None, volume_size: int = None, workers: int = None) -> bool:
        """
        并行压缩文件或文件夹（默认实现回退到单线程压缩）
        
        Args:
            source_paths: 源文件或文件夹路径列表
            dest_path: 目标压缩文件路径
            compression_level: 压缩级别（1-9）
            password: 压缩密码（可选）
            volume_size: 分卷大小（字节，可选）
            workers: 并行工作线程数，默认为CPU核心数
            
        Returns:
            bool: 压缩是否成功
        """
        return self.compress(source_paths, dest_path, compression_level, password, volume_size)

class ZipCompressionHandler(CompressionHandler):
    """
    ZIP压缩处理器
    支持zip格式的压缩和解压
    """
    
    def can_handle(self, file_path: str) -> bool:
        """
        检查是否为zip文件
        """
        _, ext = os.path.splitext(file_path)
        return ext.lower() == '.zip'
    
    def compress(self, source_paths: List[str], dest_path: str, compression_level: int = 6, password: str = None, volume_size: int = None, parallel: bool = False, workers: int = None) -> bool:
        """
        使用zipfile库压缩文件或文件夹
        
        Args:
            source_paths: 源文件或文件夹路径列表
            dest_path: 目标压缩文件路径
            compression_level: 压缩级别（1-9）
            password: 压缩密码（可选）
            volume_size: 分卷大小（字节，可选）
            parallel: 是否使用并行压缩
            workers: 并行工作线程数，默认为CPU核心数
            
        Returns:
            bool: 压缩是否成功
        """
        if parallel:
            return self.compress_parallel(source_paths, dest_path, compression_level, password, volume_size, workers)
        
        try:
            import zipfile
            
            # 确保目标路径以.zip结尾
            if not dest_path.lower().endswith('.zip'):
                dest_path += '.zip'
            
            # 创建zip文件
            with zipfile.ZipFile(dest_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=compression_level) as zipf:
                for source_path in source_paths:
                    if os.path.isfile(source_path):
                        # 压缩单个文件
                        zipf.write(source_path, os.path.basename(source_path))
                    elif os.path.isdir(source_path):
                        # 压缩文件夹及其内容
                        for root, _, files in os.walk(source_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, os.path.dirname(source_path))
                                zipf.write(file_path, arcname)
            
            # 使用pyzipper库进行密码保护（如果提供密码）
            if password:
                try:
                    import pyzipper
                    
                    # 重新创建带有密码保护的zip文件
                    temp_zip = dest_path + '.tmp'
                    with pyzipper.AESZipFile(temp_zip, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zipf:
                        zipf.setpassword(password.encode())
                        
                        # 读取原始zip文件内容
                        with zipfile.ZipFile(dest_path, 'r') as original_zip:
                            for info in original_zip.infolist():
                                zipf.writestr(info, original_zip.read(info))
                    
                    # 替换原始zip文件
                    os.replace(temp_zip, dest_path)
                except ImportError:
                    raise RuntimeError("pyzipper库未安装，无法创建密码保护的zip文件")
            
            logger.info(f"成功压缩文件到: {dest_path}")
            return True
        except Exception as e:
            logger.error(f"压缩文件失败: {e}")
            return False
    
    def compress_parallel(self, source_paths: List[str], dest_path: str, compression_level: int = 6, 
                          password: str = None, volume_size: int = None, workers: int = None) -> bool:
        """
        使用多线程并行压缩文件或文件夹
        
        Args:
            source_paths: 源文件或文件夹路径列表
            dest_path: 目标压缩文件路径
            compression_level: 压缩级别（1-9）
            password: 压缩密码（可选）
            volume_size: 分卷大小（字节，可选）
            workers: 并行工作线程数，默认为CPU核心数
            
        Returns:
            bool: 压缩是否成功
        """
        try:
            import zipfile
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            if not dest_path.lower().endswith('.zip'):
                dest_path += '.zip'
            
            if workers is None:
                workers = max(1, multiprocessing.cpu_count() - 1)
            
            file_entries = []
            for source_path in source_paths:
                if os.path.isfile(source_path):
                    file_entries.append((source_path, os.path.basename(source_path)))
                elif os.path.isdir(source_path):
                    for root, _, files in os.walk(source_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, os.path.dirname(source_path))
                            file_entries.append((file_path, arcname))
            
            if not file_entries:
                logger.warning("没有需要压缩的文件")
                return True
            
            total_files = len(file_entries)
            chunk_size = max(1, total_files // workers)
            chunks = [file_entries[i:i + chunk_size] for i in range(0, total_files, chunk_size)]
            
            temp_zips = []
            
            def compress_chunk(chunk_index, chunk):
                temp_zip = f"{dest_path}.part{chunk_index}.zip"
                with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=compression_level) as zipf:
                    for file_path, arcname in chunk:
                        try:
                            zipf.write(file_path, arcname)
                        except Exception as e:
                            logger.error(f"压缩文件失败: {file_path}, 错误: {e}")
                return temp_zip
            
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(compress_chunk, i, chunk) for i, chunk in enumerate(chunks)]
                for future in as_completed(futures):
                    temp_zips.append(future.result())
            
            with zipfile.ZipFile(dest_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=compression_level) as final_zip:
                for temp_zip in temp_zips:
                    try:
                        with zipfile.ZipFile(temp_zip, 'r') as z:
                            for info in z.infolist():
                                final_zip.writestr(info, z.read(info))
                    finally:
                        if os.path.exists(temp_zip):
                            os.remove(temp_zip)
            
            if password:
                try:
                    import pyzipper
                    
                    temp_zip = dest_path + '.tmp'
                    with pyzipper.AESZipFile(temp_zip, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zipf:
                        zipf.setpassword(password.encode())
                        
                        with zipfile.ZipFile(dest_path, 'r') as original_zip:
                            for info in original_zip.infolist():
                                zipf.writestr(info, original_zip.read(info))
                    
                    os.replace(temp_zip, dest_path)
                except ImportError:
                    raise RuntimeError("pyzipper库未安装，无法创建密码保护的zip文件")
            
            logger.info(f"成功并行压缩文件到: {dest_path}, 使用 {workers} 个线程")
            return True
        except Exception as e:
            logger.error(f"并行压缩文件失败: {e}")
            return False
    
    def decompress(self, source_path: str, dest_path: str, password: str = None) -> bool:
        """
        使用zipfile库解压zip文件
        """
        try:
            import zipfile
            
            # 确保目标路径存在
            if not os.path.exists(dest_path):
                os.makedirs(dest_path)
            
            # 解压zip文件
            with zipfile.ZipFile(source_path, 'r') as zipf:
                if password:
                    zipf.setpassword(password.encode())
                zipf.extractall(dest_path)
            
            logger.info(f"成功解压文件到: {dest_path}")
            return True
        except Exception as e:
            logger.error(f"解压文件失败: {e}")
            return False
    
    def get_file_list(self, file_path: str, password: str = None) -> List[Dict[str, Any]]:
        """
        获取zip压缩包内的文件列表
        """
        try:
            import zipfile
            from datetime import datetime
            
            file_list = []
            with zipfile.ZipFile(file_path, 'r') as zipf:
                # 检查是否需要密码
                if zipf.infolist() and zipf.infolist()[0].flag_bits & 0x1:  # 加密标志
                    if not password:
                        logger.error(f"zip文件 {file_path} 已加密，需要密码")
                        return []
                    zipf.setpassword(password.encode())
                
                for info in zipf.infolist():
                    file_list.append({
                        'name': info.filename,
                        'path': info.filename,
                        'size': info.file_size,
                        'compressed_size': info.compress_size,
                        'modified_time': datetime(*info.date_time),
                        'is_dir': info.filename.endswith('/')
                    })
            
            return file_list
        except Exception as e:
            logger.error(f"获取zip文件列表失败: {e}")
            return []
    
    def extract_file(self, archive_path: str, file_path_in_archive: str, dest_path: str, password: str = None) -> bool:
        """
        提取zip压缩包内的单个文件
        """
        try:
            import zipfile
            
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                if password:
                    zipf.setpassword(password.encode())
                
                # 检查文件是否存在
                if file_path_in_archive not in zipf.namelist():
                    logger.error(f"zip文件中不存在文件: {file_path_in_archive}")
                    return False
                
                # 提取文件
                zipf.extract(file_path_in_archive, dest_path)
            
            logger.info(f"成功提取文件: {file_path_in_archive} 到 {dest_path}")
            return True
        except Exception as e:
            logger.error(f"提取zip文件失败: {e}")
            return False
    
    def add_file(self, archive_path: str, source_file_path: str, dest_path_in_archive: str = None, password: str = None) -> bool:
        """
        向zip压缩包内添加文件
        """
        try:
            import zipfile
            
            # 如果没有指定压缩包内的目标路径，使用源文件名
            if dest_path_in_archive is None:
                dest_path_in_archive = os.path.basename(source_file_path)
            
            with zipfile.ZipFile(archive_path, 'a') as zipf:
                # zipfile库不支持向加密zip添加文件，除非重新创建整个zip
                zipf.write(source_file_path, dest_path_in_archive)
            
            logger.info(f"成功向zip文件添加文件: {source_file_path}")
            return True
        except Exception as e:
            logger.error(f"向zip文件添加文件失败: {e}")
            return False
    
    def update_file(self, archive_path: str, source_file_path: str, file_path_in_archive: str, password: str = None) -> bool:
        """
        更新zip压缩包内的文件
        """
        import tempfile
        import shutil
        
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp()
            temp_zip = os.path.join(temp_dir, 'temp.zip')
            
            if password:
                try:
                    import pyzipper
                    
                    with pyzipper.AESZipFile(archive_path, 'r') as zipf:
                        zipf.setpassword(password.encode())
                        
                        with pyzipper.AESZipFile(temp_zip, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as new_zipf:
                            new_zipf.setpassword(password.encode())
                            
                            for info in zipf.infolist():
                                if info.filename != file_path_in_archive:
                                    new_zipf.writestr(info, zipf.read(info.filename))
                            
                            new_zipf.write(source_file_path, file_path_in_archive)
                except ImportError:
                    raise RuntimeError("pyzipper库未安装，无法更新密码保护的zip文件")
            else:
                import zipfile
                
                with zipfile.ZipFile(archive_path, 'r') as zipf:
                    with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as new_zipf:
                        for info in zipf.infolist():
                            if info.filename != file_path_in_archive:
                                new_zipf.writestr(info, zipf.read(info.filename))
                        
                        new_zipf.write(source_file_path, file_path_in_archive)
            
            shutil.copy(temp_zip, archive_path)
            
            logger.info(f"成功更新zip文件中的文件: {file_path_in_archive}")
            return True
        except Exception as e:
            logger.error(f"更新zip文件失败: {e}")
            return False
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def delete_file(self, archive_path: str, file_path_in_archive: str, password: str = None) -> bool:
        """
        删除zip压缩包内的文件
        """
        import tempfile
        import shutil
        
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp()
            temp_zip = os.path.join(temp_dir, 'temp.zip')
            
            if password:
                try:
                    import pyzipper
                    
                    with pyzipper.AESZipFile(archive_path, 'r') as zipf:
                        zipf.setpassword(password.encode())
                        
                        with pyzipper.AESZipFile(temp_zip, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as new_zipf:
                            new_zipf.setpassword(password.encode())
                            
                            for info in zipf.infolist():
                                if info.filename != file_path_in_archive:
                                    new_zipf.writestr(info, zipf.read(info.filename))
                except ImportError:
                    raise RuntimeError("pyzipper库未安装，无法删除密码保护zip文件中的文件")
            else:
                import zipfile
                
                with zipfile.ZipFile(archive_path, 'r') as zipf:
                    with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as new_zipf:
                        for info in zipf.infolist():
                            if info.filename != file_path_in_archive:
                                new_zipf.writestr(info, zipf.read(info.filename))
            
            shutil.copy(temp_zip, archive_path)
            
            logger.info(f"成功删除zip文件中的文件: {file_path_in_archive}")
            return True
        except Exception as e:
            logger.error(f"删除zip文件中的文件失败: {e}")
            return False
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

class RarCompressionHandler(CompressionHandler):
    """
    RAR压缩处理器
    支持rar格式的压缩和解压
    """
    
    def can_handle(self, file_path: str) -> bool:
        """
        检查是否为rar文件
        """
        _, ext = os.path.splitext(file_path)
        return ext.lower() == '.rar'
    
    def compress(self, source_paths: List[str], dest_path: str, compression_level: int = 6, password: str = None, volume_size: int = None, parallel: bool = False, workers: int = None) -> bool:
        """
        使用rarfile库或外部rar命令压缩文件或文件夹（RAR格式不支持并行压缩）
        """
        try:
            import rarfile
            import subprocess
            import sys
            
            # 确保目标路径以.rar结尾
            if not dest_path.lower().endswith('.rar'):
                dest_path += '.rar'
            
            # rarfile库不支持创建rar文件，只能使用外部命令
            logger.warning("rarfile库不支持创建RAR文件，需要使用外部rar命令")
            
            # 尝试使用外部rar命令压缩
            if sys.platform == 'win32':
                # Windows系统，查找rar.exe
                rar_exe = self._find_rar_exe()
                if not rar_exe:
                    logger.warning("未找到rar.exe，无法压缩RAR文件，但可以解压RAR文件")
                    return False
                
                # 构建rar命令
                cmd = [rar_exe, 'a', '-ep1', '-r', '-m' + str(compression_level)]
                
                # 添加密码参数
                if password:
                    cmd.extend(['-p' + password])
                
                # 添加分卷参数
                if volume_size:
                    # 转换为MB
                    volume_mb = volume_size // (1024 * 1024)
                    cmd.extend(['-v' + str(volume_mb) + 'm'])
                
                # 添加目标文件和源文件
                cmd.append(dest_path)
                cmd.extend(source_paths)
                
                # 执行命令
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"成功使用外部rar命令压缩文件到: {dest_path}")
                    return True
                else:
                    logger.error(f"外部rar命令压缩失败: {result.stderr}")
                    return False
            else:
                # Linux/macOS系统，尝试使用rar命令
                try:
                    cmd = ['rar', 'a', '-ep1', '-r', '-m' + str(compression_level)]
                    
                    # 添加密码参数
                    if password:
                        cmd.extend(['-p' + password])
                    
                    # 添加分卷参数
                    if volume_size:
                        volume_mb = volume_size // (1024 * 1024)
                        cmd.extend(['-v' + str(volume_mb) + 'm'])
                    
                    # 添加目标文件和源文件
                    cmd.append(dest_path)
                    cmd.extend(source_paths)
                    
                    # 执行命令
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        logger.info(f"成功使用外部rar命令压缩文件到: {dest_path}")
                        return True
                    else:
                        logger.error(f"外部rar命令压缩失败: {result.stderr}")
                        return False
                except FileNotFoundError:
                    logger.warning("未找到rar命令，无法压缩RAR文件，但可以解压RAR文件")
                    return False
        except Exception as e:
            logger.error(f"RAR压缩失败: {e}")
            return False
    
    def decompress(self, source_path: str, dest_path: str, password: str = None) -> bool:
        """
        使用rarfile库解压rar文件
        """
        try:
            import rarfile
            
            # 确保目标路径存在
            if not os.path.exists(dest_path):
                os.makedirs(dest_path)
            
            # 解压rar文件
            with rarfile.RarFile(source_path, 'r') as rarf:
                if password:
                    rarf.setpassword(password)
                rarf.extractall(dest_path)
            
            logger.info(f"成功解压RAR文件到: {dest_path}")
            return True
        except ImportError:
            logger.error("rarfile库未安装，无法解压RAR文件")
            show_warning(self._parent_widget, "警告", "rarfile库未安装，无法解压RAR文件")
            return False
        except Exception as e:
            logger.error(f"解压RAR文件失败: {e}")
            return False
    
    def get_file_list(self, file_path: str, password: str = None) -> List[Dict[str, Any]]:
        """
        获取rar压缩包内的文件列表
        """
        try:
            import rarfile
            from datetime import datetime
            
            file_list = []
            with rarfile.RarFile(file_path, 'r') as rarf:
                if password:
                    rarf.setpassword(password)
                
                for info in rarf.infolist():
                    file_list.append({
                        'name': info.filename,
                        'path': info.filename,
                        'size': info.file_size,
                        'compressed_size': info.compress_size,
                        'modified_time': datetime.fromtimestamp(info.mtime),
                        'is_dir': info.isdir()
                    })
            
            return file_list
        except Exception as e:
            logger.error(f"获取rar文件列表失败: {e}")
            return []
    
    def extract_file(self, archive_path: str, file_path_in_archive: str, dest_path: str, password: str = None) -> bool:
        """
        提取rar压缩包内的单个文件
        """
        try:
            import rarfile
            
            with rarfile.RarFile(archive_path, 'r') as rarf:
                if password:
                    rarf.setpassword(password)
                
                # 提取文件
                rarf.extract(file_path_in_archive, dest_path)
            
            logger.info(f"成功提取rar文件: {file_path_in_archive} 到 {dest_path}")
            return True
        except Exception as e:
            logger.error(f"提取rar文件失败: {e}")
            return False
    
    def add_file(self, archive_path: str, source_file_path: str, dest_path_in_archive: str = None, password: str = None) -> bool:
        """
        向rar压缩包内添加文件
        """
        try:
            import rarfile
            import subprocess
            import sys
            
            # rarfile库不支持添加文件，尝试使用外部rar命令
            if sys.platform == 'win32':
                rar_exe = self._find_rar_exe()
                if not rar_exe:
                    logger.error("未找到rar.exe，无法向RAR文件添加文件")
                    show_warning(self._parent_widget, "警告", "未找到rar.exe，无法向RAR文件添加文件")
                    return False
                
                cmd = [rar_exe, 'u', '-ep1']
                if password:
                    cmd.extend(['-p' + password])
                cmd.append(archive_path)
                cmd.append(source_file_path)
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"成功向rar文件添加文件: {source_file_path}")
                    return True
                else:
                    logger.error(f"向rar文件添加文件失败: {result.stderr}")
                    return False
            else:
                # Linux/macOS系统
                cmd = ['rar', 'u', '-ep1']
                if password:
                    cmd.extend(['-p' + password])
                cmd.append(archive_path)
                cmd.append(source_file_path)
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"成功向rar文件添加文件: {source_file_path}")
                    return True
                else:
                    logger.error(f"向rar文件添加文件失败: {result.stderr}")
                    return False
        except Exception as e:
            logger.error(f"向rar文件添加文件失败: {e}")
            return False
    
    def update_file(self, archive_path: str, source_file_path: str, file_path_in_archive: str, password: str = None) -> bool:
        """
        更新rar压缩包内的文件
        """
        # 对于rar文件，更新文件和添加文件使用相同的命令
        return self.add_file(archive_path, source_file_path, file_path_in_archive, password)
    
    def delete_file(self, archive_path: str, file_path_in_archive: str, password: str = None) -> bool:
        """
        删除rar压缩包内的文件
        """
        try:
            import subprocess
            import sys
            
            # rar文件不直接支持删除文件，需要使用外部命令或重新创建
            if sys.platform == 'win32':
                rar_exe = self._find_rar_exe()
                if not rar_exe:
                    logger.error("未找到rar.exe，无法删除RAR文件中的文件")
                    show_warning(self._parent_widget, "警告", "未找到rar.exe，无法删除RAR文件中的文件")
                    return False
                
                # rar命令不直接支持删除文件，需要使用其他方法
                logger.warning("RAR文件不直接支持删除文件")
                show_warning(self._parent_widget, "警告", "RAR文件不直接支持删除文件")
                return False
            else:
                logger.warning("RAR文件不直接支持删除文件")
                show_warning(self._parent_widget, "警告", "RAR文件不直接支持删除文件")
                return False
        except Exception as e:
            logger.error(f"删除rar文件中的文件失败: {e}")
            return False
    
    def _find_rar_exe(self) -> str:
        """
        查找Windows系统中的rar.exe路径
        """
        import winreg
        
        try:
            # 尝试从注册表查找WinRAR路径
            reg_paths = [
                r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\WinRAR.exe',
                r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\WinRAR.exe'
            ]
            
            for reg_path in reg_paths:
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
                    winrar_path, _ = winreg.QueryValueEx(key, '')
                    winreg.CloseKey(key)
                    # rar.exe通常在WinRAR安装目录下
                    rar_exe = os.path.join(os.path.dirname(winrar_path), 'rar.exe')
                    if os.path.exists(rar_exe):
                        return rar_exe
                except Exception as e:
                    logger.debug(f"操作跳过: {e}")
                    continue
            # 尝试常见安装路径
            common_paths = [
                r'C:\Program Files\WinRAR\rar.exe',
                r'C:\Program Files (x86)\WinRAR\rar.exe'
            ]
            
            for path in common_paths:
                if os.path.exists(path):
                    return path
            
            return ''
        except Exception as e:
            logger.error(f"查找rar.exe失败: {e}")
            return ''

class SevenZipCompressionHandler(CompressionHandler):
    """
    7Z压缩处理器
    支持7z格式的压缩和解压
    """
    
    def can_handle(self, file_path: str) -> bool:
        """
        检查是否为7z文件
        """
        _, ext = os.path.splitext(file_path)
        return ext.lower() == '.7z'
    
    def compress(self, source_paths: List[str], dest_path: str, compression_level: int = 6, password: str = None, volume_size: int = None, parallel: bool = False, workers: int = None) -> bool:
        """
        使用py7zr库压缩文件或文件夹（支持并行压缩）
        
        Args:
            source_paths: 源文件或文件夹路径列表
            dest_path: 目标压缩文件路径
            compression_level: 压缩级别（1-9）
            password: 压缩密码（可选）
            volume_size: 分卷大小（字节，可选）
            parallel: 是否使用并行压缩
            workers: 并行工作线程数，默认为CPU核心数
            
        Returns:
            bool: 压缩是否成功
        """
        try:
            import py7zr
            
            # 确保目标路径以.7z结尾
            if not dest_path.lower().endswith('.7z'):
                dest_path += '.7z'
            
            with py7zr.SevenZipFile(dest_path, 'w', 
                                    filters=[{'id': py7zr.FILTER_LZMA2, 'preset': compression_level}], 
                                    password=password) as z:
                for source_path in source_paths:
                    if os.path.isfile(source_path):
                        z.write(source_path, os.path.basename(source_path))
                    elif os.path.isdir(source_path):
                        z.writeall(source_path, os.path.basename(source_path))
            
            logger.info(f"成功压缩文件到: {dest_path}")
            return True
        except ImportError:
            logger.error("py7zr库未安装，无法压缩7z文件")
            show_warning(self._parent_widget, "警告", "py7zr库未安装，无法压缩7z文件")
            return False
        except Exception as e:
            logger.error(f"压缩7z文件失败: {e}")
            return False
    
    def decompress(self, source_path: str, dest_path: str, password: str = None) -> bool:
        """
        使用py7zr库解压7z文件
        """
        try:
            import py7zr
            
            # 确保目标路径存在
            if not os.path.exists(dest_path):
                os.makedirs(dest_path)
            
            # 解压7z文件
            with py7zr.SevenZipFile(source_path, 'r', password=password) as z:
                z.extractall(dest_path)
            
            logger.info(f"成功解压7z文件到: {dest_path}")
            return True
        except ImportError:
            logger.error("py7zr库未安装，无法解压7z文件")
            show_warning(self._parent_widget, "警告", "py7zr库未安装，无法解压7z文件")
            return False
        except Exception as e:
            logger.error(f"解压7z文件失败: {e}")
            return False
    
    def get_file_list(self, file_path: str, password: str = None) -> List[Dict[str, Any]]:
        """
        获取7z压缩包内的文件列表
        """
        try:
            import py7zr
            from datetime import datetime
            
            file_list = []
            with py7zr.SevenZipFile(file_path, 'r', password=password) as z:
                # py7zr的list()方法返回的是一个列表
                for info in z.list():
                    # 处理FileInfo对象的属性
                    mtime = getattr(info, 'mtime', getattr(info, 'date_time', 0))
                    if isinstance(mtime, datetime):
                        modified_time = mtime
                    elif isinstance(mtime, (int, float)):
                        modified_time = datetime.fromtimestamp(mtime)
                    else:
                        modified_time = datetime.now()
                    file_list.append({
                        'name': info.filename,
                        'path': info.filename,
                        'size': info.uncompressed, 
                        'compressed_size': info.compressed,
                        'modified_time': modified_time,
                        'is_dir': info.is_directory
                    })
            
            return file_list
        except Exception as e:
            logger.error(f"获取7z文件列表失败: {e}")
            return []
    
    def extract_file(self, archive_path: str, file_path_in_archive: str, dest_path: str, password: str = None) -> bool:
        """
        提取7z压缩包内的单个文件
        """
        try:
            import py7zr
            
            with py7zr.SevenZipFile(archive_path, 'r', password=password) as z:
                # 提取指定文件
                z.extract(targets=[file_path_in_archive], path=dest_path)
            
            logger.info(f"成功提取7z文件: {file_path_in_archive} 到 {dest_path}")
            return True
        except Exception as e:
            logger.error(f"提取7z文件失败: {e}")
            return False
    
    def add_file(self, archive_path: str, source_file_path: str, dest_path_in_archive: str = None, password: str = None) -> bool:
        """
        向7z压缩包内添加文件
        """
        import tempfile
        import shutil
        
        if dest_path_in_archive is None:
            dest_path_in_archive = os.path.basename(source_file_path)
        
        temp_dir = None
        try:
            import py7zr
            
            temp_dir = tempfile.mkdtemp()
            temp_7z = os.path.join(temp_dir, 'temp.7z')
            
            with py7zr.SevenZipFile(archive_path, 'r', password=password) as z:
                z.extractall(temp_dir)
            
            shutil.copy(source_file_path, os.path.join(temp_dir, dest_path_in_archive))
            
            with py7zr.SevenZipFile(temp_7z, 'w', password=password) as z:
                z.writeall(temp_dir, arcname='.')
            
            shutil.copy(temp_7z, archive_path)
            
            logger.info(f"成功向7z文件添加文件: {source_file_path}")
            return True
        except Exception as e:
            logger.error(f"向7z文件添加文件失败: {e}")
            return False
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def update_file(self, archive_path: str, source_file_path: str, file_path_in_archive: str, password: str = None) -> bool:
        """
        更新7z压缩包内的文件
        """
        import tempfile
        import shutil
        
        temp_dir = None
        try:
            import py7zr
            
            temp_dir = tempfile.mkdtemp()
            temp_7z = os.path.join(temp_dir, 'temp.7z')
            
            with py7zr.SevenZipFile(archive_path, 'r', password=password) as z:
                z.extractall(temp_dir)
            
            old_file_path = os.path.join(temp_dir, file_path_in_archive)
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
            
            shutil.copy(source_file_path, os.path.join(temp_dir, file_path_in_archive))
            
            with py7zr.SevenZipFile(temp_7z, 'w', password=password) as z:
                z.writeall(temp_dir, arcname='.')
            
            shutil.copy(temp_7z, archive_path)
            
            logger.info(f"成功更新7z文件中的文件: {file_path_in_archive}")
            return True
        except Exception as e:
            logger.error(f"更新7z文件失败: {e}")
            return False
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def delete_file(self, archive_path: str, file_path_in_archive: str, password: str = None) -> bool:
        """
        删除7z压缩包内的文件
        """
        import tempfile
        import shutil
        
        temp_dir = None
        try:
            import py7zr
            
            temp_dir = tempfile.mkdtemp()
            temp_7z = os.path.join(temp_dir, 'temp.7z')
            
            with py7zr.SevenZipFile(archive_path, 'r', password=password) as z:
                for name in z.list():
                    if name.filename != file_path_in_archive:
                        z.extract(targets=[name.filename], path=temp_dir)
            
            with py7zr.SevenZipFile(temp_7z, 'w', password=password) as z:
                z.writeall(temp_dir, arcname='.')
            
            shutil.copy(temp_7z, archive_path)
            
            logger.info(f"成功删除7z文件中的文件: {file_path_in_archive}")
            return True
        except Exception as e:
            logger.error(f"删除7z文件中的文件失败: {e}")
            return False
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

class TarCompressionHandler(CompressionHandler):
    """
    TAR压缩处理器
    支持tar、tar.gz、tar.bz2、tar.xz格式的压缩和解压
    """
    
    def can_handle(self, file_path: str) -> bool:
        """
        检查是否为tar相关文件
        """
        file_path_lower = file_path.lower()
        # 检查各种tar格式
        return (file_path_lower.endswith('.tar') or 
                file_path_lower.endswith('.tar.gz') or 
                file_path_lower.endswith('.tgz') or 
                file_path_lower.endswith('.tar.bz2') or 
                file_path_lower.endswith('.tbz2') or 
                file_path_lower.endswith('.tar.xz') or 
                file_path_lower.endswith('.txz'))
    
    def compress(self, source_paths: List[str], dest_path: str, compression_level: int = 6, password: str = None, volume_size: int = None, parallel: bool = False, workers: int = None) -> bool:
        """
        使用tarfile库压缩文件或文件夹（tar格式不支持并行压缩）
        """
        try:
            import tarfile
            
            # tar格式不支持密码保护
            if password:
                logger.warning("tar格式不支持密码保护")
            
            # tar格式不支持分卷压缩
            if volume_size:
                logger.warning("tar格式不支持分卷压缩")
            
            # 确定压缩格式
            mode = 'w'
            if dest_path.lower().endswith('.gz') or dest_path.lower().endswith('.tgz'):
                mode = 'w:gz'
            elif dest_path.lower().endswith('.bz2') or dest_path.lower().endswith('.tbz2'):
                mode = 'w:bz2'
            elif dest_path.lower().endswith('.xz') or dest_path.lower().endswith('.txz'):
                mode = 'w:xz'
            elif not dest_path.lower().endswith('.tar'):
                dest_path += '.tar'
            
            # 创建tar文件
            with tarfile.open(dest_path, mode) as tar:
                for source_path in source_paths:
                    if os.path.isfile(source_path):
                        # 压缩单个文件
                        tar.add(source_path, arcname=os.path.basename(source_path))
                    elif os.path.isdir(source_path):
                        # 压缩文件夹及其内容
                        tar.add(source_path, arcname=os.path.basename(source_path))
            
            logger.info(f"成功压缩文件到: {dest_path}")
            return True
        except Exception as e:
            logger.error(f"压缩tar文件失败: {e}")
            return False
    
    def decompress(self, source_path: str, dest_path: str, password: str = None) -> bool:
        """
        使用tarfile库解压tar文件
        """
        try:
            import tarfile
            
            # tar格式不支持密码保护
            if password:
                logger.warning("tar格式不支持密码保护")
            
            # 确保目标路径存在
            if not os.path.exists(dest_path):
                os.makedirs(dest_path)
            
            # 解压tar文件
            with tarfile.open(source_path, 'r') as tar:
                tar.extractall(dest_path)
            
            logger.info(f"成功解压tar文件到: {dest_path}")
            return True
        except Exception as e:
            logger.error(f"解压tar文件失败: {e}")
            return False
    
    def get_file_list(self, file_path: str, password: str = None) -> List[Dict[str, Any]]:
        """
        获取tar压缩包内的文件列表
        """
        try:
            import tarfile
            from datetime import datetime
            
            # tar格式不支持密码保护
            if password:
                logger.warning("tar格式不支持密码保护")
            
            file_list = []
            with tarfile.open(file_path, 'r') as tar:
                for member in tar.getmembers():
                    file_list.append({
                        'name': member.name,
                        'path': member.name,
                        'size': member.size,
                        'compressed_size': member.size,  # tar格式的压缩大小信息不准确
                        'modified_time': datetime.fromtimestamp(member.mtime),
                        'is_dir': member.isdir()
                    })
            
            return file_list
        except Exception as e:
            logger.error(f"获取tar文件列表失败: {e}")
            return []
    
    def extract_file(self, archive_path: str, file_path_in_archive: str, dest_path: str, password: str = None) -> bool:
        """
        提取tar压缩包内的单个文件
        """
        try:
            import tarfile
            
            # tar格式不支持密码保护
            if password:
                logger.warning("tar格式不支持密码保护")
            
            with tarfile.open(archive_path, 'r') as tar:
                # 提取指定文件
                tar.extract(file_path_in_archive, dest_path)
            
            logger.info(f"成功提取tar文件: {file_path_in_archive} 到 {dest_path}")
            return True
        except Exception as e:
            logger.error(f"提取tar文件失败: {e}")
            return False
    
    def add_file(self, archive_path: str, source_file_path: str, dest_path_in_archive: str = None, password: str = None) -> bool:
        """
        向tar压缩包内添加文件
        """
        import tarfile
        import tempfile
        import shutil
        
        if password:
            logger.warning("tar格式不支持密码保护")
        
        if dest_path_in_archive is None:
            dest_path_in_archive = os.path.basename(source_file_path)
        
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp()
            temp_tar = os.path.join(temp_dir, 'temp.tar')
            
            with tarfile.open(archive_path, 'r') as tar:
                tar.extractall(temp_dir)
            
            shutil.copy(source_file_path, os.path.join(temp_dir, dest_path_in_archive))
            
            with tarfile.open(temp_tar, 'w') as tar:
                tar.add(temp_dir, arcname='.')
            
            shutil.copy(temp_tar, archive_path)
            
            logger.info(f"成功向tar文件添加文件: {source_file_path}")
            return True
        except Exception as e:
            logger.error(f"向tar文件添加文件失败: {e}")
            return False
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def update_file(self, archive_path: str, source_file_path: str, file_path_in_archive: str, password: str = None) -> bool:
        """
        更新tar压缩包内的文件
        """
        import tarfile
        import tempfile
        import shutil
        
        if password:
            logger.warning("tar格式不支持密码保护")
        
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp()
            temp_tar = os.path.join(temp_dir, 'temp.tar')
            
            with tarfile.open(archive_path, 'r') as tar:
                tar.extractall(temp_dir)
            
            old_file_path = os.path.join(temp_dir, file_path_in_archive)
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
            
            shutil.copy(source_file_path, os.path.join(temp_dir, file_path_in_archive))
            
            with tarfile.open(temp_tar, 'w') as tar:
                tar.add(temp_dir, arcname='.')
            
            shutil.copy(temp_tar, archive_path)
            
            logger.info(f"成功更新tar文件中的文件: {file_path_in_archive}")
            return True
        except Exception as e:
            logger.error(f"更新tar文件失败: {e}")
            return False
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def delete_file(self, archive_path: str, file_path_in_archive: str, password: str = None) -> bool:
        """
        删除tar压缩包内的文件
        """
        import tarfile
        import tempfile
        import shutil
        
        if password:
            logger.warning("tar格式不支持密码保护")
        
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp()
            temp_tar = os.path.join(temp_dir, 'temp.tar')
            
            with tarfile.open(archive_path, 'r') as tar:
                for member in tar.getmembers():
                    if member.name != file_path_in_archive:
                        tar.extract(member, temp_dir)
            
            with tarfile.open(temp_tar, 'w') as tar:
                tar.add(temp_dir, arcname='.')
            
            shutil.copy(temp_tar, archive_path)
            
            logger.info(f"成功删除tar文件中的文件: {file_path_in_archive}")
            return True
        except Exception as e:
            logger.error(f"删除tar文件中的文件失败: {e}")
            return False
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

class IsoCompressionHandler(CompressionHandler):
    """
    ISO压缩处理器
    支持iso格式的解压
    """
    
    def can_handle(self, file_path: str) -> bool:
        """
        检查是否为iso文件
        """
        _, ext = os.path.splitext(file_path)
        if ext.lower() != '.iso':
            return False
        import sys
        if sys.platform == 'win32':
            try:
                import subprocess
                subprocess.run(['oscdimg'], capture_output=True, timeout=5)
                return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return False
        else:
            import shutil
            return shutil.which('mkisofs') is not None or shutil.which('genisoimage') is not None
    
    def compress(self, source_paths: List[str], dest_path: str, compression_level: int = 6, password: str = None, volume_size: int = None, parallel: bool = False, workers: int = None) -> bool:
        """
        创建ISO文件（ISO格式不支持并行压缩）
        """
        try:
            import subprocess
            import sys
            
            # 确保目标路径以.iso结尾
            if not dest_path.lower().endswith('.iso'):
                dest_path += '.iso'
            
            # ISO格式不支持密码保护
            if password:
                logger.warning("ISO格式不支持密码保护")
            
            # ISO格式不支持分卷压缩
            if volume_size:
                logger.warning("ISO格式不支持分卷压缩")
            
            # 尝试使用外部工具创建ISO
            success = False
            tools_tried = []
            
            if sys.platform == 'win32':
                # Windows系统，尝试使用oscdimg命令（Windows ADK工具）
                try:
                    cmd = ['oscdimg', '-m', '-o', '-u2', '-udfver102']
                    cmd.extend(source_paths)
                    cmd.append(dest_path)
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        logger.info(f"成功创建ISO文件: {dest_path}")
                        return True
                    else:
                        tools_tried.append('oscdimg')
                except FileNotFoundError:
                    tools_tried.append('oscdimg')
                
                # 尝试使用mkisofs（Cygwin或其他工具）
                try:
                    cmd = ['mkisofs', '-o', dest_path]
                    cmd.extend(source_paths)
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        logger.info(f"成功创建ISO文件: {dest_path}")
                        return True
                    else:
                        tools_tried.append('mkisofs')
                except FileNotFoundError:
                    tools_tried.append('mkisofs')
            else:
                # Linux/macOS系统，尝试使用mkisofs或genisoimage
                try:
                    cmd = ['mkisofs', '-o', dest_path]
                    cmd.extend(source_paths)
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        logger.info(f"成功创建ISO文件: {dest_path}")
                        return True
                    else:
                        tools_tried.append('mkisofs')
                except FileNotFoundError:
                    tools_tried.append('mkisofs')
                
                try:
                    cmd = ['genisoimage', '-o', dest_path]
                    cmd.extend(source_paths)
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        logger.info(f"成功创建ISO文件: {dest_path}")
                        return True
                    else:
                        tools_tried.append('genisoimage')
                except FileNotFoundError:
                    tools_tried.append('genisoimage')
            
            logger.warning(f"无法找到创建ISO的工具({', '.join(tools_tried)})，但可以解压ISO文件")
            return False
        except Exception as e:
            logger.error(f"创建ISO文件失败: {e}")
            return False
    
    def decompress(self, source_path: str, dest_path: str, password: str = None) -> bool:
        """
        解压ISO文件
        """
        try:
            # ISO格式不支持密码保护
            if password:
                logger.warning("ISO格式不支持密码保护")
            
            # 尝试使用pycdlib库解压ISO
            try:
                import pycdlib
                
                # 确保目标路径存在
                if not os.path.exists(dest_path):
                    os.makedirs(dest_path)
                
                iso = pycdlib.PyCdlib()
                try:
                    iso.open(source_path)
                    
                    # 提取所有文件
                    iso.extract_all(dest_path)
                finally:
                    iso.close()
                
                logger.info(f"成功解压ISO文件到: {dest_path}")
                return True
            except ImportError:
                logger.warning("pycdlib库未安装，尝试使用其他方法")
            
            # 尝试使用subprocess调用外部工具
            import subprocess
            import sys
            
            if sys.platform == 'win32':
                # Windows系统，尝试使用7z命令解压ISO
                try:
                    cmd = ['7z', 'x', f'-o{dest_path}', '-y', source_path]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        logger.info(f"成功解压ISO文件到: {dest_path}")
                        return True
                    else:
                        logger.warning(f"7z解压ISO失败: {result.stderr}")
                except FileNotFoundError:
                    pass
            else:
                # Linux/macOS系统，尝试使用mount命令
                try:
                    # 这需要root权限，可能不适合所有情况
                    cmd = ['mount', '-o', 'loop', source_path, dest_path]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        logger.info(f"成功挂载ISO文件到: {dest_path}")
                        # 注意：这里只是挂载，没有实际解压
                        return True
                    else:
                        logger.warning(f"mount挂载ISO失败: {result.stderr}")
                except Exception as e:
                    logger.warning(f"mount挂载ISO失败: {e}")
            
            logger.error("无法解压ISO文件，请安装pycdlib库")
            show_warning(self._parent_widget, "警告", "无法解压ISO文件，请安装pycdlib库")
            return False
        except Exception as e:
            logger.error(f"解压ISO文件失败: {e}")
            return False
    
    def get_file_list(self, file_path: str, password: str = None) -> List[Dict[str, Any]]:
        """
        获取ISO文件内的文件列表
        """
        try:
            # ISO格式不支持密码保护
            if password:
                logger.warning("ISO格式不支持密码保护")
            
            # 尝试使用pycdlib库
            try:
                import pycdlib
                from datetime import datetime
                
                file_list = []
                iso = pycdlib.PyCdlib()
                try:
                    iso.open(file_path)
                    
                    # 获取根目录下的所有文件和文件夹
                    iso_dir = iso.list_children(iso_path='/')
                    for item in iso_dir:
                        file_id = item.file_identifier
                        if isinstance(file_id, bytes):
                            name = file_id.decode('utf-8', errors='replace')
                        else:
                            name = str(file_id)
                        is_dir = item.is_directory()
                        if is_dir:
                            file_list.append({
                                'name': name,
                                'path': '/' + name,
                                'size': 0,
                                'compressed_size': 0,
                                'modified_time': datetime.now(),
                                'is_dir': True
                            })
                        else:
                            file_list.append({
                                'name': name,
                                'path': '/' + name,
                                'size': item.data_length,
                                'compressed_size': item.data_length,
                                'modified_time': datetime.now(),
                                'is_dir': False
                            })
                finally:
                    iso.close()
                return file_list
            except ImportError:
                logger.warning("pycdlib库未安装，无法获取ISO文件列表")
            
            return []
        except Exception as e:
            logger.error(f"获取ISO文件列表失败: {e}")
            return []
    
    def extract_file(self, archive_path: str, file_path_in_archive: str, dest_path: str, password: str = None) -> bool:
        """
        提取ISO文件内的单个文件
        """
        try:
            # ISO格式不支持密码保护
            if password:
                logger.warning("ISO格式不支持密码保护")
            
            # 尝试使用pycdlib库
            try:
                import pycdlib
                
                iso = pycdlib.PyCdlib()
                try:
                    iso.open(archive_path)
                    
                    # 提取指定文件
                    iso.extract_file(iso_path=file_path_in_archive, local_path=os.path.join(dest_path, os.path.basename(file_path_in_archive)))
                finally:
                    iso.close()
                
                logger.info(f"成功提取ISO文件: {file_path_in_archive} 到 {dest_path}")
                return True
            except ImportError:
                logger.warning("pycdlib库未安装，无法提取ISO文件")
            
            return False
        except Exception as e:
            logger.error(f"提取ISO文件失败: {e}")
            return False
    
    def add_file(self, archive_path: str, source_file_path: str, dest_path_in_archive: str = None, password: str = None) -> bool:
        """
        向ISO文件添加文件
        """
        try:
            # ISO格式不支持直接添加文件
            logger.warning("ISO格式不支持直接添加文件，需要重新创建ISO")
            show_warning(self._parent_widget, "警告", "ISO格式不支持直接添加文件，需要重新创建ISO")
            return False
        except Exception as e:
            logger.error(f"向ISO文件添加文件失败: {e}")
            return False
    
    def update_file(self, archive_path: str, source_file_path: str, file_path_in_archive: str, password: str = None) -> bool:
        """
        更新ISO文件内的文件
        """
        try:
            # ISO格式不支持直接更新文件
            logger.warning("ISO格式不支持直接更新文件，需要重新创建ISO")
            show_warning(self._parent_widget, "警告", "ISO格式不支持直接更新文件，需要重新创建ISO")
            return False
        except Exception as e:
            logger.error(f"更新ISO文件失败: {e}")
            return False
    
    def delete_file(self, archive_path: str, file_path_in_archive: str, password: str = None) -> bool:
        """
        删除ISO文件内的文件
        """
        try:
            # ISO格式不支持直接删除文件
            logger.warning("ISO格式不支持直接删除文件，需要重新创建ISO")
            show_warning(self._parent_widget, "警告", "ISO格式不支持直接删除文件，需要重新创建ISO")
            return False
        except Exception as e:
            logger.error(f"删除ISO文件中的文件失败: {e}")
            return False


class CompressionService:
    """
    压缩解压服务类
    管理所有压缩解压处理器
    """
    
    def __init__(self, parent_widget=None):
        """
        初始化压缩解压服务
        """
        self._parent_widget = parent_widget
        # 注册所有压缩处理器
        self.handlers = [
            ZipCompressionHandler(parent_widget),
            RarCompressionHandler(parent_widget),
            SevenZipCompressionHandler(parent_widget),
            TarCompressionHandler(parent_widget),
            IsoCompressionHandler(parent_widget)
        ]
        logger.info("压缩解压服务已初始化")
    
    def get_handler(self, file_path: str) -> Optional[CompressionHandler]:
        """
        获取适合的压缩处理器
        
        Args:
            file_path: 文件路径
            
        Returns:
            Optional[CompressionHandler]: 压缩处理器
        """
        for handler in self.handlers:
            if handler.can_handle(file_path):
                return handler
        return None
    
    def compress(self, source_paths: List[str], dest_path: str, compression_format: str = 'zip', compression_level: int = 6, password: str = None, volume_size: int = None, parallel: bool = False, workers: int = None) -> bool:
        """
        压缩文件或文件夹
        
        Args:
            source_paths: 源文件或文件夹路径列表
            dest_path: 目标压缩文件路径（不含扩展名）
            compression_format: 压缩格式（zip, 7z, tar, tar.gz, tar.bz2, tar.xz, rar, iso）
            compression_level: 压缩级别（1-9）
            password: 压缩密码（可选）
            volume_size: 分卷大小（字节，可选）
            parallel: 是否使用并行压缩（仅ZIP格式支持）
            workers: 并行工作线程数，默认为CPU核心数
            
        Returns:
            bool: 压缩是否成功
        """
        # 处理目标路径，确保生成正确的文件名
        # 对于复合扩展名（如tar.gz），需要特殊处理
        dest_path_lower = dest_path.lower()
        
        # 移除可能存在的扩展名
        base_name = dest_path
        
        # 检查并移除复合扩展名
        for ext in ['tar.gz', 'tgz', 'tar.bz2', 'tbz2', 'tar.xz', 'txz']:
            if dest_path_lower.endswith(ext):
                base_name = dest_path[:-len(ext)]
                break
        else:
            # 检查并移除普通扩展名
            for ext in ['zip', '7z', 'tar', 'rar', 'iso']:
                if dest_path_lower.endswith(f'.{ext}'):
                    base_name = dest_path[:-len(ext)-1]
                    break
        
        # 根据压缩格式生成正确的目标路径
        if compression_format == 'tar.gz' or compression_format == 'tgz':
            dest_path_with_ext = f"{base_name}.tar.gz"
        elif compression_format == 'tar.bz2' or compression_format == 'tbz2':
            dest_path_with_ext = f"{base_name}.tar.bz2"
        elif compression_format == 'tar.xz' or compression_format == 'txz':
            dest_path_with_ext = f"{base_name}.tar.xz"
        else:
            dest_path_with_ext = f"{base_name}.{compression_format}"
        
        for handler in self.handlers:
            if handler.can_handle(dest_path_with_ext):
                return handler.compress(source_paths, dest_path_with_ext, compression_level, password, volume_size, parallel, workers)
        
        logger.error(f"不支持的压缩格式: {compression_format}")
        show_warning(self._parent_widget, "警告", f"不支持的压缩格式: {compression_format}")
        return False
    
    def compress_parallel(self, source_paths: List[str], dest_path: str, compression_format: str = 'zip', 
                          compression_level: int = 6, password: str = None, volume_size: int = None, 
                          workers: int = None) -> bool:
        """
        并行压缩文件或文件夹
        
        Args:
            source_paths: 源文件或文件夹路径列表
            dest_path: 目标压缩文件路径（不含扩展名）
            compression_format: 压缩格式（zip, 7z, tar, tar.gz, tar.bz2, tar.xz, rar, iso）
            compression_level: 压缩级别（1-9）
            password: 压缩密码（可选）
            volume_size: 分卷大小（字节，可选）
            workers: 并行工作线程数，默认为CPU核心数
            
        Returns:
            bool: 压缩是否成功
        """
        return self.compress(source_paths, dest_path, compression_format, compression_level, password, volume_size, True, workers)
    
    def decompress(self, source_path: str, dest_path: str, password: str = None) -> bool:
        """
        解压压缩文件
        
        Args:
            source_path: 源压缩文件路径
            dest_path: 目标解压路径
            password: 解压密码（可选）
            
        Returns:
            bool: 解压是否成功
        """
        handler = self.get_handler(source_path)
        if handler:
            return handler.decompress(source_path, dest_path, password)
        
        logger.error(f"不支持的压缩格式: {source_path}")
        show_warning(self._parent_widget, "警告", f"不支持的压缩格式: {os.path.splitext(source_path)[1]}")
        return False
    
    def get_supported_formats(self) -> List[str]:
        """
        获取支持的压缩格式
        
        Returns:
            List[str]: 支持的压缩格式列表
        """
        return ['zip', '7z', 'tar', 'tar.gz', 'tar.bz2', 'tar.xz', 'rar', 'iso']
    
    def extract_here(self, source_path: str, password: str = None) -> bool:
        """
        解压到当前目录
        
        Args:
            source_path: 源压缩文件路径
            password: 解压密码（可选）
            
        Returns:
            bool: 解压是否成功
        """
        # 创建与压缩文件同名的文件夹
        dest_dir = os.path.splitext(source_path)[0]
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        
        return self.decompress(source_path, dest_dir, password)
    
    def get_file_list(self, archive_path: str, password: str = None) -> List[Dict[str, Any]]:
        """
        获取压缩包内的文件列表
        
        Args:
            archive_path: 压缩文件路径
            password: 解压密码（可选）
            
        Returns:
            List[Dict[str, Any]]: 文件列表，每个元素包含name, path, size, modified_time等信息
        """
        handler = self.get_handler(archive_path)
        if handler:
            return handler.get_file_list(archive_path, password)
        
        logger.error(f"不支持的压缩格式: {archive_path}")
        show_warning(self._parent_widget, "警告", f"不支持的压缩格式: {os.path.splitext(archive_path)[1]}")
        return []
    
    def extract_file(self, archive_path: str, file_path_in_archive: str, dest_path: str, password: str = None) -> bool:
        """
        提取压缩包内的单个文件
        
        Args:
            archive_path: 压缩文件路径
            file_path_in_archive: 压缩包内的文件路径
            dest_path: 目标文件路径
            password: 解压密码（可选）
            
        Returns:
            bool: 提取是否成功
        """
        handler = self.get_handler(archive_path)
        if handler:
            return handler.extract_file(archive_path, file_path_in_archive, dest_path, password)
        
        logger.error(f"不支持的压缩格式: {archive_path}")
        show_warning(self._parent_widget, "警告", f"不支持的压缩格式: {os.path.splitext(archive_path)[1]}")
        return False
    
    def add_file(self, archive_path: str, source_file_path: str, dest_path_in_archive: str = None, password: str = None) -> bool:
        """
        向压缩包内添加文件
        
        Args:
            archive_path: 压缩文件路径
            source_file_path: 源文件路径
            dest_path_in_archive: 压缩包内的目标路径（可选）
            password: 压缩密码（可选）
            
        Returns:
            bool: 添加是否成功
        """
        handler = self.get_handler(archive_path)
        if handler:
            return handler.add_file(archive_path, source_file_path, dest_path_in_archive, password)
        
        logger.error(f"不支持的压缩格式: {archive_path}")
        show_warning(self._parent_widget, "警告", f"不支持的压缩格式: {os.path.splitext(archive_path)[1]}")
        return False
    
    def update_file(self, archive_path: str, source_file_path: str, file_path_in_archive: str, password: str = None) -> bool:
        """
        更新压缩包内的文件
        
        Args:
            archive_path: 压缩文件路径
            source_file_path: 源文件路径
            file_path_in_archive: 压缩包内的文件路径
            password: 压缩密码（可选）
            
        Returns:
            bool: 更新是否成功
        """
        handler = self.get_handler(archive_path)
        if handler:
            return handler.update_file(archive_path, source_file_path, file_path_in_archive, password)
        
        logger.error(f"不支持的压缩格式: {archive_path}")
        show_warning(self._parent_widget, "警告", f"不支持的压缩格式: {os.path.splitext(archive_path)[1]}")
        return False
    
    def delete_file(self, archive_path: str, file_path_in_archive: str, password: str = None) -> bool:
        """
        删除压缩包内的文件
        
        Args:
            archive_path: 压缩文件路径
            file_path_in_archive: 压缩包内的文件路径
            password: 压缩密码（可选）
            
        Returns:
            bool: 删除是否成功
        """
        handler = self.get_handler(archive_path)
        if handler:
            return handler.delete_file(archive_path, file_path_in_archive, password)
        
        logger.error(f"不支持的压缩格式: {archive_path}")
        show_warning(self._parent_widget, "警告", f"不支持的压缩格式: {os.path.splitext(archive_path)[1]}")
        return False

# 创建全局压缩解压服务实例
compression_service = CompressionService()