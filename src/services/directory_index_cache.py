#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
目录索引缓存服务模块
使用SQLite加速重复目录访问
"""

import os
import sqlite3
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime
from core.logger import logger

class DirectoryIndexCache:
    """
    目录索引缓存类
    使用SQLite数据库缓存目录结构，加速重复访问
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化目录索引缓存
        
        Args:
            db_path: SQLite数据库文件路径，默认为内存数据库
        """
        self.db_path = db_path or ":memory:"
        self._conn = None
        self._lock = threading.Lock()
        self._init_db()
        logger.info(f"目录索引缓存服务已初始化，数据库路径: {self.db_path}")
    
    def _init_db(self):
        """初始化数据库表"""
        try:
            with self._lock:
                self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
                cursor = self._conn.cursor()
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS directory_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        path TEXT UNIQUE NOT NULL,
                        parent_path TEXT,
                        name TEXT NOT NULL,
                        is_dir INTEGER NOT NULL DEFAULT 0,
                        size INTEGER DEFAULT 0,
                        mtime REAL DEFAULT 0,
                        ctime REAL DEFAULT 0,
                        atime REAL DEFAULT 0,
                        mode INTEGER DEFAULT 0,
                        cached_at REAL DEFAULT 0,
                        scan_depth INTEGER DEFAULT 0
                    )
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_path ON directory_cache(path)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_parent_path ON directory_cache(parent_path)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_mtime ON directory_cache(mtime)
                ''')
                
                self._conn.commit()
        except Exception as e:
            logger.error(f"初始化目录索引缓存数据库失败: {e}")
    
    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接（延迟初始化）"""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        return self._conn
    
    def cache_directory(self, path: str, files: List[Dict[str, Any]], scan_depth: int = 0) -> None:
        """
        缓存目录结构
        
        Args:
            path: 目录路径
            files: 文件列表
            scan_depth: 扫描深度
        """
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                cached_at = datetime.now().timestamp()
                
                for file_info in files:
                    parent_path = path
                    name = file_info.get("name", "")
                    file_path = file_info.get("path", os.path.join(path, name))
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO directory_cache 
                        (path, parent_path, name, is_dir, size, mtime, ctime, atime, mode, cached_at, scan_depth)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        file_path,
                        parent_path,
                        name,
                        1 if file_info.get("is_dir", False) else 0,
                        file_info.get("size", 0),
                        file_info.get("mtime", 0),
                        file_info.get("ctime", 0),
                        file_info.get("atime", 0),
                        file_info.get("mode", 0),
                        cached_at,
                        scan_depth
                    ))
                
                conn.commit()
                logger.debug(f"已缓存目录: {path}, 文件数: {len(files)}")
        except Exception as e:
            logger.error(f"缓存目录失败: {path}, 错误: {e}")
    
    def get_cached_directory(self, path: str, max_age: int = 300) -> Optional[List[Dict[str, Any]]]:
        """
        获取缓存的目录结构
        
        Args:
            path: 目录路径
            max_age: 最大缓存年龄（秒），默认5分钟
            
        Returns:
            文件列表，如果缓存不存在或过期则返回None
        """
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM directory_cache 
                    WHERE parent_path = ? AND cached_at > ?
                    ORDER BY is_dir DESC, name ASC
                ''', (path, datetime.now().timestamp() - max_age))
                
                rows = cursor.fetchall()
                if not rows:
                    return None
                
                files = []
                for row in rows:
                    files.append({
                        "name": row[3],
                        "path": row[1],
                        "is_dir": row[4] == 1,
                        "type": "文件夹" if row[4] == 1 else "文件",
                        "size": row[5],
                        "mtime": row[6],
                        "ctime": row[7],
                        "atime": row[8],
                        "mode": row[9]
                    })
                
                logger.debug(f"从缓存读取目录: {path}, 文件数: {len(files)}")
                return files
        except Exception as e:
            logger.error(f"获取缓存目录失败: {path}, 错误: {e}")
            return None
    
    def is_cached(self, path: str, max_age: int = 300) -> bool:
        """
        检查目录是否已缓存且未过期
        
        Args:
            path: 目录路径
            max_age: 最大缓存年龄（秒）
            
        Returns:
            是否有有效缓存
        """
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT COUNT(*) FROM directory_cache 
                    WHERE parent_path = ? AND cached_at > ?
                ''', (path, datetime.now().timestamp() - max_age))
                
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            logger.error(f"检查缓存失败: {path}, 错误: {e}")
            return False
    
    def invalidate_cache(self, path: str) -> None:
        """
        使指定目录的缓存失效
        
        Args:
            path: 目录路径
        """
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM directory_cache WHERE parent_path = ?', (path,))
                cursor.execute('DELETE FROM directory_cache WHERE path LIKE ?', (path + '/%',))
                
                conn.commit()
                logger.debug(f"已失效缓存: {path}")
        except Exception as e:
            logger.error(f"失效缓存失败: {path}, 错误: {e}")
    
    def invalidate_all(self) -> None:
        """使所有缓存失效"""
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM directory_cache')
                conn.commit()
                logger.info("已清空所有目录缓存")
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) FROM directory_cache')
                total_entries = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(DISTINCT parent_path) FROM directory_cache')
                total_dirs = cursor.fetchone()[0]
                
                cursor.execute('SELECT AVG(cached_at) FROM directory_cache')
                avg_age = cursor.fetchone()[0]
                if avg_age:
                    avg_age = int(datetime.now().timestamp() - avg_age)
                
                return {
                    "total_entries": total_entries,
                    "total_directories": total_dirs,
                    "average_age_seconds": avg_age
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
                
                cursor.execute('DELETE FROM directory_cache WHERE cached_at < ?', 
                             (datetime.now().timestamp() - max_age,))
                
                deleted = cursor.rowcount
                conn.commit()
                
                if deleted > 0:
                    logger.info(f"已清理 {deleted} 条过期缓存")
                
                return deleted
        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")
            return 0
    
    def close(self) -> None:
        """关闭数据库连接"""
        try:
            if self._conn:
                self._conn.close()
                self._conn = None
                logger.info("目录索引缓存已关闭")
        except Exception as e:
            logger.error(f"关闭缓存失败: {e}")

# 创建全局目录索引缓存实例
directory_index_cache = DirectoryIndexCache()

def cleanup_on_exit():
    """程序退出时清理缓存"""
    logger.info("程序退出，清理目录索引缓存")
    directory_index_cache.close()

import atexit
atexit.register(cleanup_on_exit)