#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTP/SFTP服务模块
实现FTP、FTPS、SFTP协议的文件传输功能
"""

import os
import ftplib

try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False

import threading
import queue
from datetime import datetime
from typing import List, Dict, Optional

from core.logger import logger

class FTPConnection:
    """
    FTP连接类
    管理单个FTP/SFTP连接
    """
    
    def __init__(self, host: str, port: int, username: str, password: str, protocol: str = 'ftp', key_file: str = None):
        """
        初始化FTP连接
        
        Args:
            host: 主机地址
            port: 端口
            username: 用户名
            password: 密码
            protocol: 协议类型，可选值：'ftp', 'ftps', 'sftp'
            key_file: SFTP密钥文件路径
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.protocol = protocol
        self.key_file = key_file
        self.connected = False
        self.connection = None
        self.current_path = '/'
    
    def connect(self) -> bool:
        """
        连接到FTP服务器
        
        Returns:
            bool: 连接是否成功
        """
        try:
            if self.protocol == 'ftp':
                # 使用普通FTP连接
                self.connection = ftplib.FTP()
                self.connection.connect(self.host, self.port)
                self.connection.login(self.username, self.password)
                logger.info(f"FTP连接成功: {self.host}:{self.port}")
            elif self.protocol == 'ftps':
                # 使用FTPS连接
                self.connection = ftplib.FTP_TLS()
                self.connection.connect(self.host, self.port)
                self.connection.login(self.username, self.password)
                # 启用安全数据连接
                try:
                    if hasattr(self.connection, 'prot_p'):
                        self.connection.prot_p()
                except Exception as e:
                    logger.debug(f"启用安全数据连接失败: {e}")
                logger.info(f"FTPS连接成功: {self.host}:{self.port}")
            elif self.protocol == 'sftp':
                # 使用SFTP连接
                if not HAS_PARAMIKO:
                    raise ImportError("paramiko模块未安装，请安装paramiko以支持SFTP功能: pip install paramiko")
                self.connection = paramiko.SSHClient()
                self.connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                if self.key_file:
                    self.connection.connect(
                        self.host, 
                        port=self.port, 
                        username=self.username, 
                        key_filename=self.key_file
                    )
                else:
                    self.connection.connect(
                        self.host, 
                        port=self.port, 
                        username=self.username, 
                        password=self.password
                    )
                self._ssh_client = self.connection
                self.connection = self._ssh_client.open_sftp()
                logger.info(f"SFTP连接成功: {self.host}:{self.port}")
            else:
                raise ValueError(f"不支持的协议类型: {self.protocol}")
            
            self.connected = True
            self.current_path = '/'
            return True
        except Exception as e:
            logger.error(f"连接失败: {e}")
            self.connected = False
            self.connection = None
            return False
    
    def disconnect(self):
        try:
            if self.connected and self.connection:
                if self.protocol == 'sftp':
                    self.connection.close()
                    if hasattr(self, '_ssh_client') and self._ssh_client:
                        self._ssh_client.close()
                        self._ssh_client = None
                else:
                    self.connection.quit()
        except Exception as e:
            logger.debug(f"操作失败: {e}")
        finally:
            self.connected = False
            self.connection = None
    
    def get_current_path(self) -> str:
        """
        获取当前路径
        
        Returns:
            str: 当前路径
        """
        if not self.connected:
            return '/'
        
        try:
            if self.protocol == 'sftp':
                self.current_path = self.connection.getcwd()
            else:
                self.current_path = self.connection.pwd()
            return self.current_path
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return self.current_path
    
    def change_dir(self, path: str) -> bool:
        """
        切换目录
        
        Args:
            path: 目标路径
        
        Returns:
            bool: 切换是否成功
        """
        if not self.connected:
            return False
        
        try:
            if self.protocol == 'sftp':
                self.connection.chdir(path)
            else:
                self.connection.cwd(path)
            self.current_path = path
            return True
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return False
    
    def list_files(self, path: str = None) -> List[Dict]:
        """
        列出目录中的文件
        
        Args:
            path: 目录路径，默认为当前路径
        
        Returns:
            List[Dict]: 文件列表，每个元素包含文件信息
        """
        if not self.connected:
            return []
        
        try:
            target_path = path or self.current_path
            files = []
            
            if self.protocol == 'sftp':
                # SFTP方式列出文件
                file_attrs = self.connection.listdir_attr(target_path)
                for attr in file_attrs:
                    file_info = {
                        'name': attr.filename,
                        'size': attr.st_size,
                        'type': 'directory' if attr.st_mode & 0o040000 else 'file',
                        'modified_time': datetime.fromtimestamp(attr.st_mtime)
                    }
                    files.append(file_info)
            else:
                # FTP方式列出文件
                if path:
                    # 临时切换到目标路径
                    original_path = self.current_path
                    self.change_dir(path)
                
                # 使用MLSD命令获取详细信息
                try:
                    file_list = []
                    self.connection.retrlines('MLSD', file_list.append)
                    for line in file_list:
                        parts = line.split(';')
                        file_info = {}
                        name = None
                        for part in parts:
                            part = part.strip()
                            if not part:
                                continue
                            if '=' in part:
                                key, value = part.split('=', 1)
                                if key == 'type':
                                    file_info['type'] = value
                                elif key == 'size':
                                    file_info['size'] = int(value)
                                elif key == 'modify':
                                    # 解析修改时间
                                    try:
                                        mod_time = datetime.strptime(value, '%Y%m%d%H%M%S')
                                        file_info['modified_time'] = mod_time
                                    except Exception as e:
                                        logger.debug(f"操作失败: {e}")
                            else:
                                name = part
                        if name:
                            file_info['name'] = name
                            files.append(file_info)
                except Exception as e:
                    logger.debug(f"MLSD命令失败，使用LIST命令: {e}")
                    file_list = []
                    self.connection.retrlines('LIST', file_list.append)
                    for line in file_list:
                        # 解析LIST命令输出
                        parts = line.split()
                        if len(parts) < 9:
                            continue
                        file_type = 'directory' if parts[0].startswith('d') else 'file'
                        size = int(parts[4]) if file_type == 'file' else 0
                        # 解析日期和时间
                        date_str = ' '.join(parts[5:8])
                        try:
                            if ':' in parts[7]:
                                # 格式: month day time
                                mod_time = datetime.strptime(date_str, '%b %d %H:%M')
                                mod_time = mod_time.replace(year=datetime.now().year)
                            else:
                                # 格式: month day year
                                mod_time = datetime.strptime(date_str, '%b %d %Y')
                        except Exception as e:
                            logger.debug(f"日期解析失败: {e}")
                            mod_time = datetime.now()
                        file_info = {
                            'name': ' '.join(parts[8:]),
                            'size': size,
                            'type': file_type,
                            'modified_time': mod_time
                        }
                        files.append(file_info)
                
                if path:
                    # 切换回原始路径
                    self.change_dir(original_path)
            
            return files
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return []
    
    def download_file(self, remote_path: str, local_path: str, progress_callback: callable = None) -> bool:
        """
        下载文件
        
        Args:
            remote_path: 远程文件路径
            local_path: 本地文件路径
            progress_callback: 进度回调函数，接收当前进度和总大小
        
        Returns:
            bool: 下载是否成功
        """
        if not self.connected:
            return False
        
        try:
            # 确保本地目录存在
            local_dir = os.path.dirname(local_path)
            if not os.path.exists(local_dir):
                os.makedirs(local_dir)
            
            if self.protocol == 'sftp':
                # SFTP下载
                total_size = self.connection.stat(remote_path).st_size
                
                class FileWithProgress:
                    def __init__(self, filepath, mode, total_size, callback):
                        self.file = open(filepath, mode)
                        self.total_size = total_size
                        self.callback = callback
                        self.bytes_written = 0
                    
                    def write(self, data):
                        self.file.write(data)
                        self.bytes_written += len(data)
                        if self.callback:
                            self.callback(self.bytes_written, self.total_size)
                    
                    def close(self):
                        self.file.close()
                    
                    def __enter__(self):
                        return self
                    
                    def __exit__(self, exc_type, exc_val, exc_tb):
                        self.close()
                        return False
                
                with FileWithProgress(local_path, 'wb', total_size, progress_callback) as f:
                    self.connection.getfo(remote_path, f)
            else:
                # FTP下载
                total_size = 0
                
                try:
                    total_size = self.connection.size(remote_path)
                except Exception as e:
                    logger.debug(f"获取文件大小失败: {e}")
                
                with open(local_path, 'wb') as f:
                    bytes_received = 0
                    
                    def callback(data):
                        nonlocal bytes_received
                        bytes_received += len(data)
                        f.write(data)
                        if progress_callback and total_size > 0:
                            progress_callback(bytes_received, total_size)
                    
                    self.connection.retrbinary(f'RETR {remote_path}', callback)
            
            return True
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return False
    
    def upload_file(self, local_path: str, remote_path: str, progress_callback: callable = None) -> bool:
        """
        上传文件
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
            progress_callback: 进度回调函数，接收当前进度和总大小
        
        Returns:
            bool: 上传是否成功
        """
        if not self.connected:
            return False
        
        try:
            # 确保远程目录存在
            remote_dir = os.path.dirname(remote_path)
            if remote_dir and remote_dir != '/':
                if self.protocol == 'sftp':
                    # SFTP创建目录
                    parts = remote_dir.split('/')
                    current_dir = ''
                    for part in parts:
                        if not part:
                            continue
                        current_dir += '/' + part
                        try:
                            self.connection.stat(current_dir)
                        except Exception:
                            self.connection.mkdir(current_dir)
                else:
                    # FTP创建目录
                    parts = remote_dir.split('/')
                    current_dir = ''
                    for part in parts:
                        if not part:
                            continue
                        current_dir += '/' + part
                        try:
                            self.connection.cwd(current_dir)
                        except Exception:
                            self.connection.mkd(current_dir)
                            self.connection.cwd(current_dir)
                    # 切换回原始路径
                    self.change_dir(self.current_path)
            
            try:
                total_size = os.path.getsize(local_path)
            except (OSError, PermissionError):
                total_size = 0
            
            if self.protocol == 'sftp':
                # SFTP上传
                bytes_sent = 0
                
                class FileWithProgress:
                    def __init__(self, filepath, total_size, callback):
                        self.file = open(filepath, 'rb')
                        self.total_size = total_size
                        self.callback = callback
                        self.bytes_read = 0
                    
                    def read(self, size):
                        data = self.file.read(size)
                        self.bytes_read += len(data)
                        if self.callback:
                            self.callback(self.bytes_read, self.total_size)
                        return data
                    
                    def close(self):
                        self.file.close()
                    
                    def __enter__(self):
                        return self
                    
                    def __exit__(self, exc_type, exc_val, exc_tb):
                        self.close()
                        return False
                
                with FileWithProgress(local_path, total_size, progress_callback) as f:
                    self.connection.putfo(f, remote_path)
            else:
                # FTP上传
                bytes_sent = 0
                
                def callback(data):
                    nonlocal bytes_sent
                    bytes_sent += len(data)
                    if progress_callback:
                        progress_callback(bytes_sent, total_size)
                    return data
                
                with open(local_path, 'rb') as f:
                    self.connection.storbinary(f'STOR {remote_path}', f, callback=callback)
            
            return True
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return False
    
    def create_directory(self, path: str) -> bool:
        """
        创建目录
        
        Args:
            path: 目录路径
        
        Returns:
            bool: 创建是否成功
        """
        if not self.connected:
            return False
        
        try:
            if self.protocol == 'sftp':
                self.connection.mkdir(path)
            else:
                self.connection.mkd(path)
            return True
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return False
    
    def upload_folder(self, local_folder: str, remote_folder: str, progress_callback: callable = None) -> bool:
        """
        上传文件夹
        
        Args:
            local_folder: 本地文件夹路径
            remote_folder: 远程文件夹路径
            progress_callback: 进度回调函数，接收当前进度和总大小
        
        Returns:
            bool: 上传是否成功
        """
        if not self.connected:
            return False
        
        try:
            # 确保远程目录存在
            if not self.create_directory(remote_folder):
                return False
            
            total_files = 0
            total_size = 0
            processed_files = 0
            processed_size = 0
            
            # 统计总文件数和总大小
            for root, dirs, files in os.walk(local_folder):
                total_files += len(files)
                for file in files:
                    try:
                        total_size += os.path.getsize(os.path.join(root, file))
                    except (OSError, PermissionError):
                        pass
            
            # 递归上传文件
            for root, dirs, files in os.walk(local_folder):
                # 计算相对路径
                relative_path = os.path.relpath(root, local_folder)
                if relative_path == '.':
                    current_remote = remote_folder
                else:
                    current_remote = remote_folder + '/' + relative_path.replace('\\', '/')
                
                # 确保当前远程目录存在
                self.create_directory(current_remote)
                
                # 上传文件
                for file in files:
                    local_file = os.path.join(root, file)
                    remote_file = current_remote + '/' + file
                    
                    def file_progress(current, total):
                        nonlocal processed_size
                        processed_size += current
                        if progress_callback:
                            progress_callback(processed_size, total_size)
                    
                    success = self.upload_file(local_file, remote_file, file_progress)
                    if not success:
                        return False
                    
                    processed_files += 1
                    if progress_callback:
                        progress_callback(processed_size, total_size)
            
            return True
        except Exception as e:
            logger.error(f"上传文件夹失败: {e}")
            return False
    
    def download_folder(self, remote_folder: str, local_folder: str, progress_callback: callable = None) -> bool:
        """
        下载文件夹
        
        Args:
            remote_folder: 远程文件夹路径
            local_folder: 本地文件夹路径
            progress_callback: 进度回调函数，接收当前进度和总大小
        
        Returns:
            bool: 下载是否成功
        """
        if not self.connected:
            return False
        
        try:
            # 确保本地目录存在
            if not os.path.exists(local_folder):
                os.makedirs(local_folder)
            
            total_files = 0
            total_size = 0
            processed_files = 0
            processed_size = 0
            
            # 统计总文件数和总大小
            def count_files(path):
                nonlocal total_files, total_size
                files = self.list_files(path)
                for file_info in files:
                    if file_info['type'] == 'file':
                        total_files += 1
                        total_size += file_info['size']
                    else:
                        if file_info['name'] != '.' and file_info['name'] != '..':
                            count_files(path + '/' + file_info['name'])
            
            count_files(remote_folder)
            
            # 递归下载文件
            def download_recursive(remote_path, local_path):
                nonlocal processed_files, processed_size
                
                files = self.list_files(remote_path)
                for file_info in files:
                    remote_file = remote_path + '/' + file_info['name']
                    local_file = os.path.join(local_path, file_info['name'])
                    
                    if file_info['type'] == 'file':
                        # 下载文件
                        def file_progress(current, total):
                            nonlocal processed_size
                            processed_size += current
                            if progress_callback:
                                progress_callback(processed_size, total_size)
                        
                        success = self.download_file(remote_file, local_file, file_progress)
                        if not success:
                            return False
                        
                        processed_files += 1
                        if progress_callback:
                            progress_callback(processed_size, total_size)
                    else:
                        # 是目录，递归下载
                        if file_info['name'] != '.' and file_info['name'] != '..':
                            if not os.path.exists(local_file):
                                os.makedirs(local_file)
                            download_recursive(remote_file, local_file)
            
            download_recursive(remote_folder, local_folder)
            return True
        except Exception as e:
            logger.error(f"下载文件夹失败: {e}")
            return False
    
    def delete_file(self, path: str) -> bool:
        """
        删除文件
        
        Args:
            path: 文件路径
        
        Returns:
            bool: 删除是否成功
        """
        if not self.connected:
            return False
        
        try:
            if self.protocol == 'sftp':
                self.connection.remove(path)
            else:
                self.connection.delete(path)
            return True
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return False
    
    def delete_directory(self, path: str) -> bool:
        """
        删除目录
        
        Args:
            path: 目录路径
        
        Returns:
            bool: 删除是否成功
        """
        if not self.connected:
            return False
        
        try:
            if self.protocol == 'sftp':
                # SFTP递归删除目录
                for file_attr in self.connection.listdir_attr(path):
                    file_path = f"{path}/{file_attr.filename}"
                    if file_attr.st_mode & 0o040000:
                        # 是目录
                        self.delete_directory(file_path)
                    else:
                        # 是文件
                        self.connection.remove(file_path)
                self.connection.rmdir(path)
            else:
                # FTP删除目录（需要先清空目录）
                # 注意：FTP删除非空目录可能会失败
                self.connection.rmd(path)
            return True
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return False

class FTPTransferTask:
    """
    FTP传输任务类
    管理单个文件传输任务
    """
    
    def __init__(self, task_id: str, operation: str, local_path: str, remote_path: str, connection: FTPConnection):
        """
        初始化传输任务
        
        Args:
            task_id: 任务ID
            operation: 操作类型，可选值：'upload', 'download'
            local_path: 本地文件路径
            remote_path: 远程文件路径
            connection: FTP连接对象
        """
        self.task_id = task_id
        self.operation = operation
        self.local_path = local_path
        self.remote_path = remote_path
        self.connection = connection
        self.status = 'pending'  # pending, running, completed, failed, cancelled
        self.progress = 0
        self.total_size = 0
        self.speed = 0
        self.start_time = None
        self.end_time = None
        self.error_message = ''
        self.cancelled = False  # 取消标志
        self.is_folder = False  # 是否为文件夹
    
    def start(self):
        """
        开始传输任务
        """
        self.status = 'running'
        self.start_time = datetime.now()
        self.speed = 0
        
        try:
            def progress_callback(current, total):
                # 检查是否被取消
                if self.cancelled:
                    raise Exception("任务已取消")
                self.progress = current
                self.total_size = total
                # 计算速度
                elapsed = (datetime.now() - self.start_time).total_seconds()
                if elapsed > 0:
                    self.speed = current / elapsed / 1024  # KB/s
            
            # 判断是文件还是文件夹
            if self.operation == 'upload':
                self.is_folder = os.path.isdir(self.local_path)
                if self.is_folder:
                    success = self.connection.upload_folder(self.local_path, self.remote_path, progress_callback)
                else:
                    success = self.connection.upload_file(self.local_path, self.remote_path, progress_callback)
            else:
                # 下载时，先尝试判断远程路径是文件还是文件夹
                try:
                    remote_files = self.connection.list_files(self.remote_path)
                    # 如果能列出文件，说明是文件夹
                    self.is_folder = True
                    success = self.connection.download_folder(self.remote_path, self.local_path, progress_callback)
                except Exception:
                    # 列出文件失败，可能是文件
                    self.is_folder = False
                    success = self.connection.download_file(self.remote_path, self.local_path, progress_callback)
            
            if self.cancelled:
                self.status = 'cancelled'
                self.error_message = '任务已取消'
            elif success:
                self.status = 'completed'
                self.progress = self.total_size
            else:
                self.status = 'failed'
                self.error_message = '传输失败'
        except Exception as e:
            if self.cancelled:
                self.status = 'cancelled'
                self.error_message = '任务已取消'
            else:
                self.status = 'failed'
                self.error_message = str(e)
        finally:
            self.end_time = datetime.now()

class FTPTransferManager:
    """
    FTP传输管理器类
    管理多个FTP传输任务
    """
    
    def __init__(self):
        """
        初始化传输管理器
        """
        self.tasks = {}
        self.task_queue = queue.Queue()
        self.worker_thread = None
        self.running = False
        self.lock = threading.Lock()
    
    def start(self):
        """
        启动传输管理器
        """
        self.running = True
        self.worker_thread = threading.Thread(target=self._process_tasks)
        self.worker_thread.daemon = True
        self.worker_thread.start()
    
    def stop(self):
        """
        停止传输管理器
        """
        self.running = False
        if self.worker_thread:
            self.worker_thread.join()
    
    def add_task(self, task: FTPTransferTask):
        """
        添加传输任务
        
        Args:
            task: 传输任务对象
        """
        with self.lock:
            self.tasks[task.task_id] = task
        self.task_queue.put(task)
    
    def get_task(self, task_id: str) -> Optional[FTPTransferTask]:
        """
        获取传输任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            Optional[FTPTransferTask]: 传输任务对象
        """
        with self.lock:
            return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[FTPTransferTask]:
        """
        获取所有传输任务
        
        Returns:
            List[FTPTransferTask]: 传输任务列表
        """
        with self.lock:
            return list(self.tasks.values())
    
    def cancel_task(self, task_id: str):
        """
        取消传输任务
        
        Args:
            task_id: 任务ID
        """
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                # 设置取消标志，任务执行时会检查此标志
                task.cancelled = True
                if task.status == 'pending':
                    task.status = 'cancelled'
    
    def clear_tasks(self):
        """
        清除所有已完成、失败或已取消的任务
        """
        with self.lock:
            tasks_to_remove = []
            for task_id, task in self.tasks.items():
                if task.status in ['completed', 'failed', 'cancelled']:
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
    
    def _process_tasks(self):
        """
        处理传输任务队列
        """
        max_retries = 3
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)
                if task.status != 'cancelled':
                    task.start()
                    if task.status == 'failed':
                        retry_count = getattr(task, '_retry_count', 0)
                        if retry_count < max_retries:
                            task._retry_count = retry_count + 1
                            task.status = 'pending'
                            task.error_message = ''
                            self.task_queue.put(task)
                self.task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.debug(f"操作跳过: {e}")
                continue
class FTPService:
    """
    FTP服务类
    管理FTP连接和传输任务
    """
    
    def __init__(self):
        """
        初始化FTP服务
        """
        self.connections = {}
        self.transfer_manager = FTPTransferManager()
        self.transfer_manager.start()
    
    def cleanup(self):
        """清理资源，停止后台线程"""
        if hasattr(self, 'transfer_manager') and self.transfer_manager:
            self.transfer_manager.stop()
        for conn_id, conn in list(self.connections.items()):
            try:
                conn.disconnect()
            except Exception as e:
                logger.debug(f"操作失败: {e}")
        self.connections.clear()
    
    def create_connection(self, host: str, port: int, username: str, password: str, protocol: str = 'ftp', key_file: str = None) -> str:
        """
        创建FTP连接
        
        Args:
            host: 主机地址
            port: 端口
            username: 用户名
            password: 密码
            protocol: 协议类型
            key_file: SFTP密钥文件路径
        
        Returns:
            str: 连接ID
        """
        connection_id = f"{host}:{port}:{username}"
        connection = FTPConnection(host, port, username, password, protocol, key_file)
        self.connections[connection_id] = connection
        return connection_id
    
    def connect(self, connection_id: str) -> bool:
        """
        连接到FTP服务器
        
        Args:
            connection_id: 连接ID
        
        Returns:
            bool: 连接是否成功
        """
        if connection_id in self.connections:
            return self.connections[connection_id].connect()
        return False
    
    def disconnect(self, connection_id: str):
        """
        断开FTP连接
        
        Args:
            connection_id: 连接ID
        """
        if connection_id in self.connections:
            self.connections[connection_id].disconnect()
            del self.connections[connection_id]
    
    def get_connection(self, connection_id: str) -> Optional[FTPConnection]:
        """
        获取FTP连接
        
        Args:
            connection_id: 连接ID
        
        Returns:
            Optional[FTPConnection]: FTP连接对象
        """
        return self.connections.get(connection_id)
    
    def start_transfer(self, operation: str, local_path: str, remote_path: str, connection: FTPConnection) -> str:
        """
        开始文件传输
        
        Args:
            operation: 操作类型
            local_path: 本地文件路径
            remote_path: 远程文件路径
            connection: FTP连接对象
        
        Returns:
            str: 任务ID
        """
        task_id = f"{operation}:{datetime.now().timestamp()}"
        task = FTPTransferTask(task_id, operation, local_path, remote_path, connection)
        self.transfer_manager.add_task(task)
        return task_id
    
    def get_transfer_task(self, task_id: str) -> Optional[FTPTransferTask]:
        """
        获取传输任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            Optional[FTPTransferTask]: 传输任务对象
        """
        return self.transfer_manager.get_task(task_id)
    
    def get_all_transfer_tasks(self) -> List[FTPTransferTask]:
        """
        获取所有传输任务
        
        Returns:
            List[FTPTransferTask]: 传输任务列表
        """
        return self.transfer_manager.get_all_tasks()
    
    def cancel_transfer(self, task_id: str):
        """
        取消传输任务
        
        Args:
            task_id: 任务ID
        """
        self.transfer_manager.cancel_task(task_id)
    
    def clear_tasks(self):
        """
        清除所有已完成、失败或已取消的任务
        """
        self.transfer_manager.clear_tasks()

# 创建FTP服务实例
ftp_service = FTPService()
