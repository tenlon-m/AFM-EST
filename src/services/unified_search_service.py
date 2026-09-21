#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一搜索服务
整合NTFS快速搜索（文件名）和Whoosh全文搜索（文件内容）
提供统一的搜索接口

优化改进：
1. 并行构建：NTFS文件名索引和Whoosh全文索引同时构建
2. 索引持久化：重启后自动加载已有索引，无需重建
3. 增量更新：支持USN Journal增量同步文件变更
4. 取消超时限制：避免大磁盘索引构建失败
"""

import os
import sys
import time
import threading
from typing import List, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.logger import logger

from .fast_search_service import fast_search_service
from .whoosh_search_service import whoosh_search_service


class UnifiedSearchService:
    """
    统一搜索服务
    整合多种搜索方式，提供最佳搜索体验
    """
    
    def __init__(self):
        """初始化统一搜索服务"""
        self.fast_search = fast_search_service
        self.fulltext_search = whoosh_search_service
        self.build_event = threading.Event()
        self._load_existing_indexes()
        
        logger.info("统一搜索服务已初始化")
    
    def _load_existing_indexes(self):
        """加载已有的索引数据（持久化支持）"""
        logger.info("尝试加载已有的索引...")
        
        ntfs_loaded = self.fast_search._load_index_data()
        
        whoosh_stats = self.fulltext_search.get_index_stats()
        whoosh_loaded = whoosh_stats.get('index_built', False)
        
        if ntfs_loaded:
            self.fast_search.index_built = True
            logger.info("NTFS文件名索引已从磁盘加载")
        
        if whoosh_loaded:
            logger.info(f"Whoosh全文索引已存在，文档数: {whoosh_stats.get('document_count', 0)}")
        
        logger.info(f"索引加载完成 - NTFS: {self.fast_search.index_built}, Whoosh: {whoosh_loaded}")
    
    def search(self, keyword: str, search_type: str = "auto", 
               max_results: int = 100, directory: str = None) -> List[Dict]:
        if search_type == "auto":
            if ' ' in keyword or len(keyword) > 20:
                search_type = "both"
            else:
                search_type = "filename"
        
        if search_type == "filename":
            return self._search_filename(keyword, max_results, directory)
        elif search_type == "content":
            return self._search_content(keyword, max_results, directory)
        elif search_type == "both":
            return self._search_both(keyword, max_results, directory)
        else:
            return self._search_filename(keyword, max_results, directory)
    
    def _search_filename(self, keyword: str, max_results: int, directory: str = None) -> List[Dict]:
        results = self.fast_search.search(keyword, max_results, directory=directory)
        
        if directory:
            norm_dir = os.path.normpath(directory).lower()
            results = [r for r in results if os.path.normpath(r.get('path', '')).lower().startswith(norm_dir)]
            results = results[:max_results]
        
        for result in results:
            result["search_type"] = "filename"
            result["source"] = "NTFS MFT"
        
        return results
    
    def _search_content(self, keyword: str, max_results: int, directory: str = None) -> List[Dict]:
        results = self.fulltext_search.search(keyword, max_results)
        
        if directory:
            norm_dir = os.path.normpath(directory).lower()
            results = [r for r in results if os.path.normpath(r.get('path', '')).lower().startswith(norm_dir)]
        
        for result in results:
            result["search_type"] = "content"
            result["source"] = "Whoosh Index"
        
        return results
    
    def _search_both(self, keyword: str, max_results: int, directory: str = None) -> List[Dict]:
        filename_results = self.fast_search.search(keyword, max_results)
        content_results = self.fulltext_search.search(keyword, max_results)
        
        for result in filename_results:
            result["search_type"] = "filename"
            result["source"] = "NTFS MFT"
        
        for result in content_results:
            result["search_type"] = "content"
            result["source"] = "Whoosh Index"
        
        combined = filename_results + content_results
        seen_paths = set()
        unique_results = []
        
        for result in combined:
            if result["path"] not in seen_paths:
                seen_paths.add(result["path"])
                if directory:
                    norm_dir = os.path.normpath(directory).lower()
                    if not os.path.normpath(result.get('path', '')).lower().startswith(norm_dir):
                        continue
                unique_results.append(result)
        
        return unique_results[:max_results]
    
    def build_all_indexes(self, drives: List[str] = None, callback=None):
        """
        构建所有索引（并行构建）
        
        Args:
            drives: 要索引的盘符列表（None时自动检测所有可索引磁盘）
            callback: 进度回调函数，签名 callback(progress_type, *args)
                      progress_type: "ntfs" 或 "whoosh"
        """
        logger.info("[UnifiedSearch] 开始构建所有索引...")

        
        if drives is None:
            drives = self._detect_indexable_drives()
            logger.info(f"[UnifiedSearch] 自动检测到可索引磁盘: {drives}")

        
        if not drives:
            logger.warning("[UnifiedSearch] 未检测到可索引磁盘")

            return
        
        self.build_event.clear()
        
        ntfs_finished = threading.Event()
        whoosh_finished = threading.Event()
        
        def build_ntfs():
            try:
                logger.info("[UnifiedSearch] 开始构建NTFS文件名索引...")

                
                def ntfs_callback(drive, progress, indexed, total):
                    if callback:
                        callback("ntfs", drive, progress, indexed, total)
                
                self.fast_search.build_index_async(drives, ntfs_callback)
                
                self.fast_search.build_event.wait()
                
                logger.info("[UnifiedSearch] NTFS文件名索引构建完成")

            finally:
                ntfs_finished.set()
        
        def build_whoosh():
            try:
                logger.info("[UnifiedSearch] 开始构建Whoosh全文索引...")

                
                search_paths = [f"{drive}:\\" for drive in drives]
                
                def whoosh_callback(progress, indexed, total):
                    if callback:
                        callback("whoosh", "ALL", progress, indexed, total)
                
                self.fulltext_search.build_index_async(search_paths, whoosh_callback)
                
                self.fulltext_search.build_event.wait()
                
                if self.fulltext_search.index_built:
                    logger.info("[UnifiedSearch] Whoosh全文索引构建完成")

                else:
                    logger.error("[UnifiedSearch] Whoosh全文索引构建失败")

            finally:
                whoosh_finished.set()
        
        ntfs_thread = threading.Thread(target=build_ntfs, daemon=True)
        whoosh_thread = threading.Thread(target=build_whoosh, daemon=True)
        
        ntfs_thread.start()
        whoosh_thread.start()
        
        def wait_and_notify():
            ntfs_finished.wait()
            whoosh_finished.wait()
            
            logger.info("[UnifiedSearch] 所有索引构建完成!")

            
            self.build_event.set()
        
        threading.Thread(target=wait_and_notify, daemon=True).start()
    
    def build_indexes_incremental(self):
        """增量更新索引（使用USN Journal）"""
        logger.info("[UnifiedSearch] 开始增量更新索引...")

        
        self.fast_search.update_index_from_usn()
        
        logger.info("[UnifiedSearch] 增量更新完成")

    
    def _detect_indexable_drives(self) -> List[str]:
        """
        自动检测所有可索引的磁盘
        
        Returns:
            可索引磁盘的盘符列表
        """
        try:
            import psutil
            drives = []
            
            for partition in psutil.disk_partitions(all=False):
                mountpoint = partition.mountpoint
                
                if len(mountpoint) == 3 and mountpoint[1] == ':':
                    drive_letter = mountpoint[0]
                else:
                    continue
                
                opts = partition.opts.lower()
                
                if 'cdrom' in opts:
                    continue
                if 'network' in opts:
                    continue
                if 'ram' in opts:
                    continue
                
                try:
                    usage = psutil.disk_usage(mountpoint)
                    if usage.total > 0:
                        drives.append(drive_letter)
                except (PermissionError, OSError):
                    continue
            
            return drives
        
        except Exception as e:
            logger.error(f"[UnifiedSearch] 检测磁盘失败: {e}")
            return ['C']
    
    def get_stats(self) -> Dict:
        """获取所有索引的统计信息"""
        return {
            "fast_search": self.fast_search.get_index_stats(),
            "fulltext_search": self.fulltext_search.get_index_stats()
        }
    
    def is_index_built(self) -> bool:
        """
        检查索引是否已构建（快速搜索或全文搜索任一已构建）
        
        Returns:
            bool: 索引是否已构建
        """
        return self.fast_search.index_built or self.fulltext_search.index_built
    
    def is_fulltext_index_built(self) -> bool:
        """
        检查全文索引是否已构建
        
        Returns:
            bool: 全文索引是否已构建
        """
        return self.fulltext_search.index_built
    
    def clear_all_indexes(self):
        """清空所有索引"""
        import shutil
        import gc
        
        from .index_location_manager import IndexLocationManager
        
        location_manager = IndexLocationManager()
        index_dir = location_manager.get_default_location()
        config_dir = os.path.join(os.path.dirname(index_dir), 'config')
        
        self.fulltext_search.index_built = False
        self.fast_search.index_built = False
        
        if self.fulltext_search.ix is not None:
            self.fulltext_search.ix = None
        
        gc.collect()
        
        if os.path.exists(index_dir):
            shutil.rmtree(index_dir)
            logger.info(f"[UnifiedSearch] 已清空索引目录: {index_dir}")
        
        if os.path.exists("whoosh_index"):
            shutil.rmtree("whoosh_index")
            logger.info("[UnifiedSearch] 已清空旧的 whoosh_index 目录")
        
        for config_file in ["index_data.json", "index_status.json", "whoosh_index_status.json"]:
            full_path = os.path.join(config_dir, config_file)
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"[UnifiedSearch] 已删除配置文件: {full_path}")
        
        db_path = os.path.join(config_dir, "index_data.db")
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info(f"[UnifiedSearch] 已删除快速搜索索引数据库: {db_path}")
        
        for old_config_file in ["config/index_data.json", "config/index_status.json", "config/whoosh_index_status.json", "config/index_data.db"]:
            if os.path.exists(old_config_file):
                os.remove(old_config_file)
                logger.info(f"[UnifiedSearch] 已删除旧配置文件: {old_config_file}")
        
        logger.info("[UnifiedSearch] 所有索引已清空")

    
    def _clear_alternate_index_locations(self):
        """清空其他可能的索引存储位置（兼容旧版本和不同配置）"""
        from .index_location_manager import IndexLocationManager
        
        location_manager = IndexLocationManager()
        index_dir = location_manager.get_default_location()
        
        if os.path.exists(index_dir):
            success, msg = location_manager.clear_index(index_dir)
            if success:
                logger.info(f"[UnifiedSearch] 已清空备用索引目录: {index_dir}")



# 全局实例
unified_search_service = UnifiedSearchService()