#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件锁工具模块
提供跨平台的文件锁定功能，防止并发访问导致的文件冲突
"""

import os
import time
import threading
from pathlib import Path
from core.logger import logger

try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

try:
    import msvcrt
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False


class FileLock:
    """
    文件锁类
    提供跨平台的文件锁定功能
    
    使用方式：
        with FileLock("config/whoosh_index_status.json"):
            # 执行文件操作
            with open("config/whoosh_index_status.json", 'w') as f:
                json.dump(data, f)
    """
    
    def __init__(self, file_path: str, timeout: float = 10.0, poll_interval: float = 0.1):
        """
        初始化文件锁
        
        Args:
            file_path: 要锁定的文件路径
            timeout: 最大等待时间（秒）
            poll_interval: 轮询间隔（秒）
        """
        self.file_path = str(file_path)
        self.lock_path = self.file_path + ".lock"
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._lock_file = None
        self._acquired = False
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
    
    def acquire(self) -> bool:
        """
        获取文件锁
        
        Returns:
            是否成功获取锁
        """
        start_time = time.time()
        
        while time.time() - start_time < self.timeout:
            try:
                if HAS_FCNTL:
                    self._lock_file = open(self.lock_path, 'w')
                    try:
                        fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        self._acquired = True
                        return True
                    except BlockingIOError:
                        self._lock_file.close()
                        self._lock_file = None
                elif HAS_MSVCRT:
                    self._lock_file = open(self.lock_path, 'w')
                    try:
                        msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_LOCK, 1)
                        self._acquired = True
                        return True
                    except IOError:
                        self._lock_file.close()
                        self._lock_file = None
                else:
                    try:
                        fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                        os.close(fd)
                        self._acquired = True
                        return True
                    except FileExistsError:
                        pass
                
                time.sleep(self.poll_interval)
            except Exception as e:
                logger.debug(f"获取文件锁失败: {e}")
                time.sleep(self.poll_interval)
        
        logger.warning(f"获取文件锁超时: {self.file_path}")
        return False
    
    def release(self) -> None:
        """释放文件锁"""
        if self._acquired:
            try:
                if self._lock_file:
                    if HAS_FCNTL:
                        try:
                            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
                        except Exception:
                            pass
                    elif HAS_MSVCRT:
                        try:
                            msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                        except Exception:
                            pass
                    self._lock_file.close()
                    self._lock_file = None
                
                if os.path.exists(self.lock_path):
                    try:
                        os.remove(self.lock_path)
                    except Exception:
                        pass
                
                self._acquired = False
            except Exception as e:
                logger.debug(f"释放文件锁失败: {e}")


def atomic_write_json(file_path: str, data: dict) -> bool:
    """
    原子写入JSON文件
    
    Args:
        file_path: 文件路径
        data: 要写入的数据
        
    Returns:
        是否成功写入
    """
    import json
    
    temp_path = str(file_path) + ".tmp"
    
    try:
        with FileLock(file_path):
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            if os.path.exists(file_path):
                os.remove(file_path)
            os.rename(temp_path, file_path)
            
            return True
    except Exception as e:
        logger.error(f"原子写入JSON失败: {file_path}, 错误: {e}")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return False


def atomic_read_json(file_path: str) -> dict:
    """
    原子读取JSON文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        读取的数据，如果失败返回空字典
    """
    import json
    
    try:
        with FileLock(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.debug(f"原子读取JSON失败: {file_path}, 错误: {e}")
        return {}


# 全局文件锁字典，用于同一进程内的锁定
_global_locks = {}
_global_locks_lock = threading.Lock()


def get_global_file_lock(file_path: str) -> FileLock:
    """
    获取全局文件锁（同一进程内复用）
    
    Args:
        file_path: 文件路径
        
    Returns:
        FileLock实例
    """
    global _global_locks
    
    with _global_locks_lock:
        if file_path not in _global_locks:
            _global_locks[file_path] = FileLock(file_path)
        return _global_locks[file_path]
