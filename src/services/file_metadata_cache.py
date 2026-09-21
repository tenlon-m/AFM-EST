#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件元数据缓存服务模块
使用SQLite缓存文件属性信息，减少重复的os.stat调用
"""

import os
import sqlite3
import threading
from typing import Dict, Any, Optional
from datetime import datetime
from core.logger import logger


class FileMetadataCache:
    """
    文件元数据缓存类
    使用SQLite数据库缓存文件属性信息，加速重复访问
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化文件元数据缓存
        
        Args:
            db_path: SQLite数据库文件路径，默认为内存数据库
        """
        self.db_path = db_path or ":memory:"
        self._conn = None
        self._lock = threading.Lock()
        self._init_db()
        logger.info(f"文件元数据缓存服务已初始化，数据库路径: {self.db_path}")
    
    def _init_db(self):
        """初始化数据库表"""
        try:
            with self._lock:
                self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
                cursor = self._conn.cursor()
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS file_metadata (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        path TEXT UNIQUE NOT NULL,
                        size INTEGER DEFAULT 0,
                        mtime REAL DEFAULT 0,
                        ctime REAL DEFAULT 0,
                        atime REAL DEFAULT 0,
                        mode INTEGER DEFAULT 0,
                        is_dir INTEGER DEFAULT 0,
                        cached_at REAL DEFAULT 0,
                        accessed_count INTEGER DEFAULT 0
                    )
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_path ON file_metadata(path)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_mtime ON file_metadata(mtime)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_is_dir ON file_metadata(is_dir)
                ''')
                
                self._conn.commit()
        except Exception as e:
            logger.error(f"初始化文件元数据缓存数据库失败: {e}")
    
    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        return self._conn
    
    def cache_metadata(self, path: str, stat_result: os.stat_result = None) -> None:
        """
        缓存文件元数据
        
        Args:
            path: 文件路径
            stat_result: os.stat结果，如不提供则自动获取
        """
        try:
            if stat_result is None:
                if not os.path.exists(path):
                    return
                stat_result = os.stat(path)
            
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                cached_at = datetime.now().timestamp()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO file_metadata 
                    (path, size, mtime, ctime, atime, mode, is_dir, cached_at, accessed_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    path,
                    stat_result.st_size,
                    stat_result.st_mtime,
                    stat_result.st_ctime,
                    stat_result.st_atime,
                    stat_result.st_mode,
                    1 if os.path.isdir(path) else 0,
                    cached_at,
                    0
                ))
                
                conn.commit()
                logger.debug(f"已缓存文件元数据: {path}")
        except Exception as e:
            logger.error(f"缓存文件元数据失败: {path}, 错误: {e}")
    
    def cache_batch_metadata(self, paths: list) -> None:
        """
        批量缓存文件元数据
        
        Args:
            paths: 文件路径列表
        """
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                cached_at = datetime.now().timestamp()
                
                for path in paths:
                    if not os.path.exists(path):
                        continue
                    try:
                        stat_result = os.stat(path)
                        cursor.execute('''
                            INSERT OR REPLACE INTO file_metadata 
                            (path, size, mtime, ctime, atime, mode, is_dir, cached_at, accessed_count)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            path,
                            stat_result.st_size,
                            stat_result.st_mtime,
                            stat_result.st_ctime,
                            stat_result.st_atime,
                            stat_result.st_mode,
                            1 if os.path.isdir(path) else 0,
                            cached_at,
                            0
                        ))
                    except Exception as e:
                        logger.debug(f"缓存单个文件失败: {path}, 错误: {e}")
                
                conn.commit()
                logger.debug(f"批量缓存完成，文件数: {len(paths)}")
        except Exception as e:
            logger.error(f"批量缓存文件元数据失败: {e}")
    
    def get_metadata(self, path: str, max_age: int = 300, refresh_on_miss: bool = True) -> Optional[Dict[str, Any]]:
        """
        获取文件元数据
        
        Args:
            path: 文件路径
            max_age: 最大缓存年龄（秒），默认5分钟
            refresh_on_miss: 缓存缺失时是否自动刷新
            
        Returns:
            文件元数据字典，如果缓存不存在或过期则返回None或刷新后的数据
        """
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM file_metadata WHERE path = ? AND cached_at > ?
                ''', (path, datetime.now().timestamp() - max_age))
                
                row = cursor.fetchone()
                if row:
                    cursor.execute('''
                        UPDATE file_metadata SET accessed_count = accessed_count + 1 WHERE path = ?
                    ''', (path,))
                    conn.commit()
                    
                    return {
                        "path": row[1],
                        "size": row[2],
                        "mtime": row[3],
                        "ctime": row[4],
                        "atime": row[5],
                        "mode": row[6],
                        "is_dir": row[7] == 1,
                        "cached_at": row[8],
                        "accessed_count": row[9] + 1
                    }
                
                if refresh_on_miss and os.path.exists(path):
                    stat_result = os.stat(path)
                    self.cache_metadata(path, stat_result)
                    cursor.execute('''
                        SELECT * FROM file_metadata WHERE path = ?
                    ''', (path,))
                    row = cursor.fetchone()
                    if row:
                        return {
                            "path": row[1],
                            "size": row[2],
                            "mtime": row[3],
                            "ctime": row[4],
                            "atime": row[5],
                            "mode": row[6],
                            "is_dir": row[7] == 1,
                            "cached_at": row[8],
                            "accessed_count": row[9]
                        }
                
                return None
        except Exception as e:
            logger.error(f"获取文件元数据失败: {path}, 错误: {e}")
            return None
    
    def get_size(self, path: str, max_age: int = 300) -> Optional[int]:
        """
        获取文件大小（从缓存）
        
        Args:
            path: 文件路径
            max_age: 最大缓存年龄（秒）
            
        Returns:
            文件大小，如果缓存不存在或过期则返回None
        """
        metadata = self.get_metadata(path, max_age)
        return metadata.get("size") if metadata else None
    
    def get_mtime(self, path: str, max_age: int = 300) -> Optional[float]:
        """
        获取文件修改时间（从缓存）
        
        Args:
            path: 文件路径
            max_age: 最大缓存年龄（秒）
            
        Returns:
            修改时间戳，如果缓存不存在或过期则返回None
        """
        metadata = self.get_metadata(path, max_age)
        return metadata.get("mtime") if metadata else None
    
    def is_directory(self, path: str, max_age: int = 300) -> Optional[bool]:
        """
        检查是否为目录（从缓存）
        
        Args:
            path: 文件路径
            max_age: 最大缓存年龄（秒）
            
        Returns:
            是否为目录，如果缓存不存在或过期则返回None
        """
        metadata = self.get_metadata(path, max_age)
        return metadata.get("is_dir") if metadata else None
    
    def is_cached(self, path: str, max_age: int = 300) -> bool:
        """
        检查文件元数据是否已缓存且未过期
        
        Args:
            path: 文件路径
            max_age: 最大缓存年龄（秒）
            
        Returns:
            是否有有效缓存
        """
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT COUNT(*) FROM file_metadata WHERE path = ? AND cached_at > ?
                ''', (path, datetime.now().timestamp() - max_age))
                
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            logger.error(f"检查缓存失败: {path}, 错误: {e}")
            return False
    
    def invalidate_cache(self, path: str) -> None:
        """
        使指定文件的缓存失效
        
        Args:
            path: 文件路径
        """
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM file_metadata WHERE path = ?', (path,))
                cursor.execute('DELETE FROM file_metadata WHERE path LIKE ?', (path + '/%',))
                
                conn.commit()
                logger.debug(f"已失效文件元数据缓存: {path}")
        except Exception as e:
            logger.error(f"失效缓存失败: {path}, 错误: {e}")
    
    def invalidate_all(self) -> None:
        """使所有缓存失效"""
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM file_metadata')
                conn.commit()
                logger.info("已清空所有文件元数据缓存")
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) FROM file_metadata')
                total_entries = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM file_metadata WHERE is_dir = 1')
                total_dirs = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM file_metadata WHERE is_dir = 0')
                total_files = cursor.fetchone()[0]
                
                cursor.execute('SELECT AVG(cached_at) FROM file_metadata')
                avg_age = cursor.fetchone()[0]
                if avg_age:
                    avg_age = int(datetime.now().timestamp() - avg_age)
                
                cursor.execute('SELECT SUM(accessed_count) FROM file_metadata')
                total_accessed = cursor.fetchone()[0] or 0
                
                return {
                    "total_entries": total_entries,
                    "total_directories": total_dirs,
                    "total_files": total_files,
                    "average_age_seconds": avg_age,
                    "total_accessed": total_accessed
                }
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {}
    
    def cleanup_old_cache(self, max_age: int = 3600) -> int:
        """
        清理过期缓存
        
        Args:
            max_age: 最大缓存年龄（秒），默认1小时
            
        Returns:
            清理的条目数
        """
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM file_metadata WHERE cached_at < ?', 
                             (datetime.now().timestamp() - max_age,))
                
                deleted = cursor.rowcount
                conn.commit()
                
                if deleted > 0:
                    logger.info(f"清理过期文件元数据缓存，删除 {deleted} 条记录")
                
                return deleted
        except Exception as e:
            logger.error(f"清理缓存失败: {e}")
            return 0
    
    def close(self):
        """关闭数据库连接"""
        try:
            with self._lock:
                if self._conn:
                    self._conn.close()
                    self._conn = None
                    logger.info("文件元数据缓存已关闭")
        except Exception as e:
            logger.error(f"关闭缓存失败: {e}")


# 全局单例实例
_file_metadata_cache_instance = None
_file_metadata_cache_lock = threading.Lock()


def get_file_metadata_cache(db_path: Optional[str] = None) -> FileMetadataCache:
    """
    获取文件元数据缓存单例
    
    Args:
        db_path: SQLite数据库文件路径
        
    Returns:
        FileMetadataCache实例
    """
    global _file_metadata_cache_instance
    with _file_metadata_cache_lock:
        if _file_metadata_cache_instance is None:
            _file_metadata_cache_instance = FileMetadataCache(db_path)
        return _file_metadata_cache_instance


def shutdown_file_metadata_cache():
    """关闭文件元数据缓存"""
    global _file_metadata_cache_instance
    with _file_metadata_cache_lock:
        if _file_metadata_cache_instance:
            _file_metadata_cache_instance.close()
            _file_metadata_cache_instance = None
