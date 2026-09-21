#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于Whoosh的全文搜索服务
提供文件内容索引和全文搜索功能

技术原理：
1. Whoosh搜索引擎：纯Python实现的全文检索引擎
2. 分词处理：使用jieba中文分词
3. 多线程并行：提高索引构建速度
4. 批量写入：减少IO开销
5. 索引优化：合并段文件提高搜索性能

注意：首次使用需要构建索引，耗时取决于文件数量
"""

import os
import sys
import time
import json
import threading
import shutil
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from core.file_lock import FileLock, atomic_read_json, atomic_write_json
    HAS_FILE_LOCK = True
except ImportError:
    HAS_FILE_LOCK = False

try:
    from whoosh.index import create_in, open_dir
    from whoosh.fields import Schema, TEXT, ID, STORED, NUMERIC
    from whoosh.qparser import MultifieldParser
    from whoosh.analysis import SimpleAnalyzer
    HAS_WHOOSH = True
except ImportError:
    HAS_WHOOSH = False

try:
    import jieba
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False

from core.logger import logger

try:
    from services.index_location_manager import IndexLocationManager
    HAS_INDEX_MANAGER = True
except ImportError:
    HAS_INDEX_MANAGER = False

def _get_default_index_dir() -> str:
    if HAS_INDEX_MANAGER:
        try:
            manager = IndexLocationManager()
            return manager.get_default_location()
        except Exception as e:
            logger.debug(f"获取默认索引目录失败，使用回退目录: {e}")
    return "whoosh_index"

INDEX_DIR = _get_default_index_dir()
MAX_FILE_SIZE = 50 * 1024 * 1024
DEFAULT_INDEX_SIZE_THRESHOLD = 500 * 1024 * 1024

TEXT_EXTENSIONS = {
    '.txt', '.md', '.py', '.java', '.cpp', '.h', '.c', '.js', '.html', '.css',
    '.xml', '.json', '.yaml', '.yml', '.csv', '.log', '.rst', '.markdown',
    '.sql', '.php', '.go', '.rs', '.ts', '.jsx', '.tsx', '.vue', '.sh', '.bat',
    '.properties', '.ini', '.cfg', '.conf', '.toml', '.ini', '.mdx',
    '.docx', '.xlsx', '.pptx', '.doc', '.xls', '.ppt', '.pdf',
}

BINARY_EXTENSIONS = {
    '.exe', '.dll', '.sys', '.bin', '.dat', '.db', '.mdb', '.sqlite', '.dbf',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.ico', '.svg', '.webp',
    '.mp3', '.wav', '.ogg', '.flac', '.aac', '.wma',
    '.mp4', '.avi', '.mkv', '.flv', '.mov', '.wmv', '.rmvb',
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
    '.iso', '.img', '.msi', '.cab', '.apk', '.ipa',
    '.swf', '.obj', '.stl', '.fbx', '.blend', '.unity',
    '.mui', '.rll', '.tlb', '.sig', '.pak', '.bdic', '.propdesc',
    '.msix', '.msixbundle', '.sccd', '.wprp', '.preloaded_data', '.pb',
    '.pri', '.data', '.dat.data', '.msix.data', '.msixbundle.data',
    '.sparse.dev.msixbundle.data', '.sparse.internal.msixbundle.data',
    '.sparse.stable.msixbundle.data', '.sparse.beta.msix.data',
    '.sparse.canary.msix.data', '.sparse.dev.msix.data',
    '.sparse.internal.msix.data', '.sparse.stable.msix.data',
    '.ins', '.dar0', '.dar1', '.sig.data', '.pak.data',
    '.bin.data', '.icudtl.dat.data', '.v8_context_snapshot.bin.data',
    '.msixbundle', '.msi', '.cab', '.scc', '.pdb', '.ilk', '.obj', '.lib',
    '.exp', '.res', '.tlb', '.ocx', '.ax', '.scr', '.cpl', '.drv', '.vxd',
    '.efi', '.rom', '.bin', '.hex', '.mot', '.s19', '.elf', '.mach-o',
    '.class', '.jar', '.war', '.ear', '.apk', '.dex', '.so', '.a', '.ko',
    '.deb', '.rpm', '.pkg', '.dmg', '.iso', '.img', '.vmdk', '.vdi', '.qcow2',
}

SKIP_DIRS = frozenset({
    'node_modules', '.git', '.svn', '__pycache__', 'venv', '.venv',
    'System Volume Information', '$Recycle.Bin', 'Program Files',
    'Program Files (x86)', 'Windows', 'WinSxS', 'ProgramData',
    'AppData', '.codeartsdoer', 'Thunder Network',
})


class ChineseTokenizer:
    """中文分词器（实现Whoosh的Tokenizer协议）"""
    
    def __init__(self):
        self.jieba_available = HAS_JIEBA
    
    def __call__(self, value, positions=False, chars=False, keeporiginal=False,
                 removestops=True, start_pos=0, start_char=0, mode='index', **kwargs):
        from whoosh.analysis import Token
        
        if not self.jieba_available:
            words = value.split()
        else:
            import jieba
            words = list(jieba.cut(value))
        
        pos = start_pos
        char_pos = start_char
        
        for word in words:
            if not word or word.strip() == '':
                continue
            
            tok = Token()
            tok.text = word
            tok.boost = 1.0
            
            if positions:
                tok.pos = pos
            if chars:
                tok.startchar = char_pos
                tok.endchar = char_pos + len(word)
            
            if keeporiginal:
                tok.original = word
            if mode == 'query':
                tok.mode = 'query'
            else:
                tok.mode = 'index'
            
            yield tok
            
            pos += 1
            char_pos += len(word)


class ChineseAnalyzer:
    """中文分词器（兼容Whoosh的Analyzer接口）"""
    
    def __init__(self):
        self.tokenizer = ChineseTokenizer()
    
    def __call__(self, text, mode='index', **kwargs):
        return self.tokenizer(text, mode=mode, **kwargs)


class WhooshSearchService:
    """
    Whoosh全文搜索服务
    负责文件内容索引和全文搜索
    """
    
    def __init__(self, index_dir: str = None):
        self.index_dir = index_dir if index_dir else INDEX_DIR
        self.schema = self._create_schema() if HAS_WHOOSH else None
        self.ix = None
        self.index_built = False
        self.is_indexing = False
        self.build_thread = None
        self.build_event = threading.Event()
        self._max_workers = max(2, os.cpu_count() // 2)
        
        if HAS_WHOOSH:
            self._startup_cleanup()
            self._check_index_status()
        else:
            logger.warning("Whoosh不可用，跳过索引初始化")
        
        logger.info("全文搜索服务已初始化")
        logger.debug(f"线程池大小: {self._max_workers}")
    
    def _create_schema(self):
        """创建索引schema"""
        if HAS_JIEBA:
            analyzer = ChineseAnalyzer()
        else:
            analyzer = SimpleAnalyzer()
        
        return Schema(
            path=ID(stored=True, unique=True),
            filename=TEXT(stored=True, analyzer=analyzer),
            content=TEXT(analyzer=analyzer),
            size=NUMERIC(stored=True),
            mtime=NUMERIC(stored=True),
            directory=STORED(),
        )
    
    def _check_index_status(self) -> None:
        """检查索引状态（验证实际索引文件是否存在）"""
        try:
            config_path = Path("config/whoosh_index_status.json")
            if config_path.exists():
                if HAS_FILE_LOCK:
                    data = atomic_read_json(config_path)
                else:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                
                config_index_built = data.get('index_built', False)
                
                if config_index_built:
                    indexed_paths = data.get('indexed_paths', [])
                    last_build_time = data.get('last_build_time', '')
                    logger.info(f"配置文件检测到已有索引: {len(indexed_paths)}个路径, 构建时间: {last_build_time}")
                    
                    if self._verify_index_integrity():
                        self.index_built = True
                        logger.info("索引文件验证通过")
                        self._check_periodic_rebuild(data)
                    else:
                        self.index_built = False
                        logger.warning("索引文件不存在或不完整，需要重新构建")
                        self._cleanup_corrupt_index()
            else:
                self.index_built = False
        except Exception as e:
            logger.error(f"检查索引状态失败: {e}")
            self.index_built = False
    
    def _cleanup_corrupt_index(self) -> None:
        """清理损坏的索引配置和索引目录"""
        try:
            config_path = Path("config/whoosh_index_status.json")
            if config_path.exists():
                if HAS_FILE_LOCK:
                    with FileLock(str(config_path)):
                        if config_path.exists():
                            config_path.unlink()
                else:
                    config_path.unlink()
                logger.info("已清理损坏的索引配置文件")
            
            self.ix = None
            import gc
            gc.collect()
            
            import shutil
            if os.path.exists(self.index_dir):
                shutil.rmtree(self.index_dir)
                logger.info(f"已清理损坏的索引目录: {self.index_dir}")
        except Exception as e:
            logger.error(f"清理损坏索引失败: {e}")
    
    def _startup_cleanup(self) -> None:
        """启动时执行清理操作"""
        self._cleanup_temp_files()
        self._check_index_size()
    
    def _cleanup_temp_files(self) -> None:
        """清理临时文件（MAIN.tmp目录和孤立的.run文件）"""
        try:
            index_path = Path(self.index_dir)
            
            if not index_path.exists():
                return
            
            tmp_dir = index_path / "MAIN.tmp"
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)
                logger.debug(f"清理临时目录: {tmp_dir}")
            
            for run_file in index_path.glob("*.run"):
                run_file.unlink(missing_ok=True)
                logger.debug(f"清理孤立的.run文件: {run_file}")
                
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")
    
    def _check_index_size(self) -> None:
        """检查索引大小，超过阈值时发出警告"""
        try:
            index_path = Path(self.index_dir)
            
            if not index_path.exists():
                return
            
            total_size = 0
            for file in index_path.rglob('*'):
                if file.is_file():
                    total_size += file.stat().st_size
            
            threshold = DEFAULT_INDEX_SIZE_THRESHOLD
            if total_size > threshold:
                logger.warning(f"索引大小 {total_size / (1024 * 1024):.2f}MB 超过阈值 {threshold / (1024 * 1024):.2f}MB")
            
            logger.info(f"当前索引大小: {total_size / (1024 * 1024):.2f}MB")
            
        except Exception as e:
            logger.error(f"检查索引大小失败: {e}")
    
    def _check_periodic_rebuild(self, status_data: Dict) -> None:
        """检查是否需要定期重建索引"""
        try:
            config_path = Path("config/config.json")
            auto_rebuild_days = 0
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    auto_rebuild_days = config.get('search', {}).get('auto_rebuild_days', 0)
            
            if auto_rebuild_days <= 0:
                return
            
            last_build_time_str = status_data.get('last_build_time', '')
            if not last_build_time_str:
                return
            
            last_build_time = datetime.fromisoformat(last_build_time_str)
            elapsed_days = (datetime.now() - last_build_time).days
            
            if elapsed_days >= auto_rebuild_days:
                logger.info(f"索引已过期({elapsed_days}天), 自动触发重建")
                
                indexed_paths = status_data.get('indexed_paths', [])
                if indexed_paths:
                    self.rebuild_index(indexed_paths)
            
        except Exception as e:
            logger.error(f"检查定期重建失败: {e}")
    
    def verify_index(self, sample_count: int = 50) -> Tuple[bool, int]:
        """
        抽样验证索引有效性
        
        Args:
            sample_count: 抽样数量
            
        Returns:
            (是否有效, 无效文件数)
        """
        if not self.index_built or not self.ix:
            return False, 0
        
        try:
            with self.ix.searcher() as searcher:
                doc_count = searcher.doc_count()
                if doc_count == 0:
                    return True, 0
                
                sample_size = min(sample_count, doc_count)
                invalid_count = 0
                
                for i in range(sample_size):
                    try:
                        doc = searcher.stored_fields(i)
                        filepath = doc.get('path', '')
                        
                        if filepath and not os.path.exists(filepath):
                            invalid_count += 1
                    except Exception as e:
                        logger.debug(f"操作跳过: {e}")
                        continue
                if invalid_count > sample_size * 0.5:
                    logger.error(f"索引验证失败: {invalid_count}/{sample_size} 抽样文件不存在")
                    return False, invalid_count
                
                logger.info(f"索引验证完成: {invalid_count}/{sample_size} 抽样文件不存在")
                return True, invalid_count
                
        except Exception as e:
            logger.error(f"索引验证失败: {e}")
            return False, 0
    
    def validate_and_cleanup(self, callback=None) -> int:
        """
        完整验证并清理无效索引条目
        
        Args:
            callback: 进度回调函数
            
        Returns:
            清理的无效条目数
        """
        if not self.index_built or not self.ix:
            return 0
        
        try:
            with self.ix.searcher() as searcher:
                doc_count = searcher.doc_count()
                if doc_count == 0:
                    return 0
                
                deleted_count = 0
                last_callback_time = time.time()
                
                writer = self.ix.writer()
                
                for i in range(doc_count):
                    try:
                        doc = searcher.stored_fields(i)
                        filepath = doc.get('path', '')
                        
                        if filepath and not os.path.exists(filepath):
                            writer.delete_by_term('path', filepath)
                            deleted_count += 1
                    except Exception as e:
                        logger.debug(f"操作跳过: {e}")
                        continue
                    if callback and (time.time() - last_callback_time) >= 0.5:
                        progress = (i / doc_count) * 100
                        callback(progress, deleted_count, doc_count)
                        last_callback_time = time.time()
                
                if deleted_count > 0:
                    writer.commit()
                    self.ix = open_dir(self.index_dir)
                    logger.info(f"清理完成: 删除 {deleted_count} 个无效索引条目")
                else:
                    writer.cancel()
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"验证清理失败: {e}")
            return 0
    
    def _save_index_status(self, indexed_paths: List[str], file_metadata: Dict = None) -> None:
        """保存索引状态"""
        try:
            config_path = Path("config/whoosh_index_status.json")
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'index_built': self.index_built,
                'indexed_paths': indexed_paths,
                'last_build_time': datetime.now().isoformat(),
                'file_metadata': file_metadata if file_metadata else {},
            }
            
            if HAS_FILE_LOCK:
                atomic_write_json(str(config_path), data)
            else:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存索引状态失败: {e}")
    
    def incremental_update(self, search_paths: List[str] = None, callback=None):
        """
        增量更新索引（只更新新增/修改的文件）
        
        Args:
            search_paths: 搜索路径列表
            callback: 进度回调函数
        """
        if not self.index_built:
            logger.info("[WhooshSearch] 索引未构建，执行完整索引构建")

            self.build_index_async(search_paths, callback)
            return
        
        if search_paths is None:
            search_paths = []
        
        if not search_paths:
            search_paths = [os.path.expanduser("~")]
        
        logger.info(f"[WhooshSearch] 开始增量更新索引，路径: {search_paths}")
        
        try:
            old_metadata = self._load_index_metadata()
            
            if not self.ix:
                self.ix = open_dir(self.index_dir)
            
            writer = self.ix.writer()
            
            new_metadata = {}
            new_count = 0
            modified_count = 0
            deleted_count = 0
            skipped_count = 0
            batch_count = 0
            
            for filepath, filename, size, mtime in self._scan_files_for_indexing(search_paths):
                key = filepath
                
                old_info = old_metadata.get(key)
                current_info = {'size': size, 'mtime': mtime}
                
                if old_info is None:
                    try:
                        content = self._read_file_content(filepath)
                        if content:
                            writer.add_document(
                                path=filepath,
                                filename=filename,
                                content=content,
                                size=size,
                                mtime=mtime,
                                directory=os.path.dirname(filepath),
                            )
                            new_count += 1
                            batch_count += 1
                    except Exception as e:
                        logger.warning(f"[WhooshSearch] 添加新文件失败: {filepath}, 错误: {e}")
                elif old_info['size'] != size or old_info['mtime'] != mtime:
                    try:
                        content = self._read_file_content(filepath)
                        if content:
                            writer.update_document(
                                path=filepath,
                                filename=filename,
                                content=content,
                                size=size,
                                mtime=mtime,
                                directory=os.path.dirname(filepath),
                            )
                            modified_count += 1
                            batch_count += 1
                    except Exception as e:
                        logger.warning(f"[WhooshSearch] 更新文件失败: {filepath}, 错误: {e}")
                else:
                    skipped_count += 1
                
                new_metadata[key] = current_info
                
                if batch_count >= 1000:
                    writer.commit(optimize=False)
                    writer = self.ix.writer()
                    batch_count = 0
                
                if callback and (new_count + modified_count) % 100 == 0:
                    callback(50, new_count + modified_count, new_count + modified_count + skipped_count)
            
            old_files = set(old_metadata.keys())
            current_files = set(new_metadata.keys())
            deleted_files = old_files - current_files
            
            for deleted_file in deleted_files:
                try:
                    writer.delete_by_term('path', deleted_file)
                    deleted_count += 1
                    batch_count += 1
                    
                    if batch_count >= 1000:
                        writer.commit(optimize=False)
                        writer = self.ix.writer()
                        batch_count = 0
                except Exception as e:
                    logger.warning(f"[WhooshSearch] 删除文件失败: {deleted_file}, 错误: {e}")
            
            if batch_count > 0:
                writer.commit(optimize=False)
            
            if not self._verify_index_integrity():
                raise RuntimeError("增量更新后索引文件不完整")
            
            self._save_index_status(search_paths, new_metadata)
            
            logger.info(f"[WhooshSearch] 增量更新完成: 新增 {new_count}, 修改 {modified_count}, 删除 {deleted_count}, 跳过 {skipped_count}")
            
            if callback:
                callback(100, new_count + modified_count, new_count + modified_count + skipped_count)
            
        except Exception as e:
            logger.error(f"[WhooshSearch] 增量更新失败: {e}", exc_info=True)
            
            if callback:
                try:
                    callback(-1, 0, 0)
                except Exception as e:
                    logger.debug(f"操作失败: {e}")
    def _load_index_metadata(self) -> Dict:
        """加载索引元数据"""
        try:
            config_path = Path("config/whoosh_index_status.json")
            if config_path.exists():
                if HAS_FILE_LOCK:
                    data = atomic_read_json(config_path)
                else:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                return data.get('file_metadata', {})
        except Exception as e:
            logger.error(f"[WhooshSearch] 加载索引元数据失败: {e}")
        
        return {}
    
    def _is_text_file(self, filepath: str) -> bool:
        """判断是否为文本文件"""
        ext = os.path.splitext(filepath)[1].lower()
        
        if ext in BINARY_EXTENSIONS:
            return False
        
        if ext in TEXT_EXTENSIONS:
            return True
        
        return False
    
    def _read_file_content(self, filepath: str, max_size: int = 1024 * 1024) -> str:
        """
        读取文件内容
        
        Args:
            filepath: 文件路径
            max_size: 最大读取大小
            
        Returns:
            文件内容字符串
        """
        content = ""
        
        try:
            with open(filepath, 'rb') as f:
                header = f.read(1024)
                
                null_byte_count = header.count(b'\x00')
                if null_byte_count > len(header) * 0.01:
                    return ""
                
                raw = header + f.read(max_size - 1024)
            
            for codec in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
                try:
                    content = raw.decode(codec)
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            
            if not content:
                content = raw.decode('latin-1', errors='ignore')
            
            content = content.replace('\x00', '')
            
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            content = ""
        
        return content
    
    def _scan_files_for_indexing(self, search_paths: List[str]):
        total_count = 0
        
        try:
            for search_path in search_paths:
                if not os.path.exists(search_path):
                    logger.info(f"[WhooshSearch] 路径不存在: {search_path}")
                    continue
                
                logger.info(f"[WhooshSearch] 开始扫描路径: {search_path}")
                
                for root, dirs, filenames in os.walk(search_path):
                    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                    
                    for filename in filenames:
                        filepath = os.path.join(root, filename)
                        
                        if not self._is_text_file(filepath):
                            continue
                        
                        try:
                            stat = os.stat(filepath)
                            if stat.st_size > MAX_FILE_SIZE:
                                continue
                            
                            yield (filepath, filename, stat.st_size, stat.st_mtime)
                            total_count += 1
                        except (PermissionError, OSError):
                            continue
                        except Exception as e:
                            logger.warning(f"[WhooshSearch] 获取文件信息失败: {filepath}, 错误: {e}")
        except Exception as e:
            logger.error(f"[WhooshSearch] 扫描文件失败: {e}", exc_info=True)
        
        logger.info(f"[WhooshSearch] 扫描完成，共找到 {total_count} 个文件")
    
    def build_index_async(self, search_paths: List[str] = None, callback=None):
        """
        异步构建索引
        
        Args:
            search_paths: 搜索路径列表
            callback: 进度回调函数
        """
        if self.build_thread and self.build_thread.is_alive():
            logger.warning("索引正在构建中")
            return
        
        if search_paths is None:
            search_paths = [os.path.expanduser("~")]
        
        self.build_thread = threading.Thread(
            target=self._build_index,
            args=(search_paths, callback),
            daemon=True
        )
        self.build_thread.start()
    
    def _build_index(self, search_paths: List[str], callback=None):
        start_time = time.time()
        processed_count = 0
        total_files = 0
        committed_batches = 0
        self.is_indexing = True
        
        logger.info(f"[WhooshSearch] 开始构建全文索引，路径: {search_paths}")
        
        try:
            logger.info("[WhooshSearch] 清理旧索引目录...")
            
            self.ix = None
            import gc
            gc.collect()
            
            if os.path.exists(self.index_dir):
                shutil.rmtree(self.index_dir)
            
            os.makedirs(self.index_dir, exist_ok=True)
            
            logger.info(f"[WhooshSearch] 创建索引实例: {self.index_dir}")
            
            self.ix = create_in(self.index_dir, self.schema)
            
            batch_size = 1000
            commit_interval = 5000
            last_callback_time = time.time()
            index_size_exceeded = False
            file_metadata = {}
            estimated_total = 0
            
            try:
                import psutil
                for sp in search_paths:
                    try:
                        usage = psutil.disk_usage(sp)
                        used_bytes = usage.used
                        estimated_total += int(used_bytes / (500 * 1024))
                    except Exception as e:
                        logger.debug(f"操作失败: {e}")
            except Exception as e:
                logger.debug(f"操作失败: {e}")
            if estimated_total < 10000:
                estimated_total = 200000
            
            logger.info(f"[WhooshSearch] 估算文件总数: {estimated_total}")
            
            last_reported_progress = 0.0
            last_logged_percent = -1
            
            logger.info("[WhooshSearch] 开始扫描和处理文件...")
            
            writer = self.ix.writer()
            files_processed_in_batch = 0
            
            for filepath, filename, size, mtime in self._scan_files_for_indexing(search_paths):
                total_files += 1
                
                if total_files % 5000 == 0:
                    logger.info(f"[WhooshSearch] 已扫描 {total_files} 个文件")
                
                try:
                    content = self._read_file_content(filepath)
                    if content:
                        writer.update_document(
                            path=filepath,
                            filename=filename,
                            content=content,
                            size=size,
                            mtime=mtime,
                            directory=os.path.dirname(filepath),
                        )
                        files_processed_in_batch += 1
                        processed_count += 1
                        file_metadata[filepath] = {'size': size, 'mtime': mtime}
                except (PermissionError, OSError):
                    continue
                except Exception as e:
                    logger.warning(f"[WhooshSearch] 读取文件失败: {filepath}, 错误: {e}")
                    continue
                
                current_time = time.time()
                if callback and (current_time - last_callback_time) >= 1.0:
                    if total_files <= 0:
                        raw_progress = 0
                    else:
                        ratio = min(total_files / max(estimated_total, 1), 1.0)
                        raw_progress = ratio * 90
                    
                    elapsed = current_time - start_time
                    min_progress = min(elapsed / 300 * 90, 90)
                    raw_progress = max(raw_progress, min_progress)
                    
                    progress = max(raw_progress, last_reported_progress)
                    progress = min(progress, 90)
                    last_reported_progress = progress
                    
                    current_percent = int(progress / 5) * 5
                    if current_percent > last_logged_percent and current_percent > 0:
                        logger.info(f"[WhooshSearch] 全文索引进度: {current_percent}% (已扫描 {total_files}, 已索引 {processed_count}, 估算总数 {estimated_total})")
                        last_logged_percent = current_percent
                    
                    callback(progress, processed_count, total_files)
                    last_callback_time = current_time
                
                if files_processed_in_batch >= batch_size:
                    writer.commit(optimize=False)
                    committed_batches += 1
                    files_processed_in_batch = 0
                    writer = self.ix.writer()
                    
                    logger.info(f"[WhooshSearch] 提交批次完成，已提交: {processed_count}")
                    
                    if committed_batches % (commit_interval // batch_size) == 0:
                        self._check_index_size_warning()
                
                if total_files % commit_interval == 0 and self._check_index_size_limit():
                    logger.warning("[WhooshSearch] 索引大小已超过阈值，停止添加新文件")
                    index_size_exceeded = True
                    break
            
            if files_processed_in_batch > 0:
                writer.commit(optimize=False)
            
            if callback:
                callback(96, processed_count, total_files)
            
            self.index_built = True
            self._save_index_status(search_paths, file_metadata)
            
            elapsed = time.time() - start_time
            
            logger.info(f"[WhooshSearch] 索引构建完成! 耗时: {elapsed:.2f}秒, 索引文件数: {processed_count}")
            if index_size_exceeded:
                logger.warning(f"[WhooshSearch] 注意: 索引大小超过阈值，部分文件未被索引")
            
            if callback:
                callback(98, processed_count, total_files)
            
            logger.info("[WhooshSearch] 开始优化索引...")
            
            try:
                if callback:
                    callback(99, processed_count, total_files)
                
                w = self.ix.writer()
                w.commit(optimize=True)
                
                logger.info("[WhooshSearch] 索引优化完成")
            except Exception as e:
                logger.warning(f"[WhooshSearch] 索引优化失败（不影响搜索功能）: {e}")
            
            if callback:
                callback(100, processed_count, total_files)
            
        except Exception as e:
            self.index_built = False
            
            self.ix = None
            import gc
            gc.collect()
            
            if os.path.exists(self.index_dir):
                try:
                    shutil.rmtree(self.index_dir)
                    logger.info("[WhooshSearch] 已清理损坏的索引")
                except Exception as e:
                    logger.debug(f"操作失败: {e}")
            logger.error(f"[WhooshSearch] 索引构建失败: {e}", exc_info=True)
            
            if callback:
                try:
                    callback(-1, processed_count, total_files)
                except Exception as e:
                    logger.debug(f"操作失败: {e}")
        finally:
            self.is_indexing = False
            self.build_event.set()
    

    
    def _check_index_size_warning(self) -> None:
        """检查索引大小并发出警告"""
        try:
            index_path = Path(self.index_dir)
            if not index_path.exists():
                return
            
            total_size = 0
            for file in index_path.rglob('*'):
                if file.is_file():
                    total_size += file.stat().st_size
            
            threshold = DEFAULT_INDEX_SIZE_THRESHOLD
            if total_size > threshold:
                logger.warning(f"[WhooshSearch] 警告: 索引大小 {total_size / (1024 * 1024):.2f}MB 超过阈值 {threshold / (1024 * 1024):.2f}MB")
            
        except Exception as e:
            logger.error(f"[WhooshSearch] 检查索引大小失败: {e}")
    
    def _check_index_size_limit(self) -> bool:
        """检查索引大小是否超过上限"""
        try:
            index_path = Path(self.index_dir)
            if not index_path.exists():
                return False
            
            total_size = 0
            for file in index_path.rglob('*'):
                if file.is_file():
                    total_size += file.stat().st_size
            
            max_size = DEFAULT_INDEX_SIZE_THRESHOLD * 2
            return total_size > max_size
            
        except Exception as e:
            logger.error(f"[WhooshSearch] 检查索引大小上限失败: {e}")
            return False
    
    def _verify_index_integrity(self) -> bool:
        try:
            index_path = Path(self.index_dir)
            
            if not index_path.exists():
                logger.error("[WhooshSearch] 索引目录不存在")
                return False
            
            write_lock = index_path / "MAIN_WRITELOCK"
            if write_lock.exists():
                logger.warning("[WhooshSearch] 发现写入锁文件，尝试清理")
                try:
                    write_lock.unlink()
                    logger.info("[WhooshSearch] 已删除残留的写入锁文件")
                except Exception as e:
                    logger.warning(f"[WhooshSearch] 删除写入锁文件失败: {e}")
            
            seg_files = list(index_path.glob("*.seg"))
            if not seg_files:
                logger.error("[WhooshSearch] 索引段文件(.seg)不存在")
                return False
            
            try:
                from whoosh.index import open_dir
                ix = open_dir(self.index_dir)
                doc_count = ix.doc_count()
                if doc_count == 0:
                    logger.error(f"[WhooshSearch] 索引文档数为0，索引不完整")
                    return False
                
                logger.info(f"[WhooshSearch] 索引验证通过，段文件数: {len(seg_files)}, 文档数: {doc_count}")
                logger.info(f"索引验证通过，段文件数: {len(seg_files)}, 文档数: {doc_count}")
            except Exception as e:
                logger.error(f"[WhooshSearch] 无法打开索引检查文档数: {e}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"[WhooshSearch] 索引验证失败: {e}")
            return False
    
    def search(self, keyword: str, max_results: int = 100) -> List[Dict]:
        """
        搜索文件内容
        
        Args:
            keyword: 搜索关键字
            max_results: 最大返回结果数
            
        Returns:
            搜索结果列表
        """
        if not HAS_WHOOSH:
            logger.warning("[WhooshSearch] Whoosh未安装")
            return []
        
        if not self.index_built:
            logger.warning("[WhooshSearch] 索引尚未构建")
            return []
        
        if self.ix is None:
            try:
                self.ix = open_dir(self.index_dir)
            except Exception as e:
                logger.error(f"[WhooshSearch] 打开索引失败: {e}")
                return []
        
        results = []
        
        try:
            start_time = time.time()
            
            with self.ix.searcher() as searcher:
                parser = MultifieldParser(['filename', 'content'], self.ix.schema)
                query = parser.parse(keyword)
                
                whoosh_results = searcher.search(query, limit=max_results)
                
                for hit in whoosh_results:
                    results.append({
                        "path": hit['path'],
                        "name": hit['filename'],
                        "is_dir": False,
                        "size": hit['size'],
                        "mtime": hit['mtime'],
                        "score": hit.score,
                        "directory": hit.get('directory', ''),
                    })
                
                elapsed = time.time() - start_time
                logger.debug(f"搜索 '{keyword}' 找到 {len(results)} 个结果，耗时 {elapsed*1000:.2f}ms")
                
        except Exception as e:
            logger.error(f"[WhooshSearch] 搜索失败: {e}", exc_info=True)
        
        return results
    
    def rebuild_index(self, search_paths: List[str] = None, callback=None):
        """
        重建索引
        
        Args:
            search_paths: 搜索路径列表
            callback: 进度回调函数
        """
        self.index_built = False
        self.build_index_async(search_paths, callback)
    
    def get_index_stats(self) -> Dict:
        """获取索引统计信息"""
        stats = {
            "document_count": 0,
            "index_built": False,
            "index_size_mb": 0,
            "last_build_time": "",
            "index_path": self.index_dir,
        }
        
        if not self.index_built:
            return stats
        
        try:
            index_path = Path(self.index_dir)
            if index_path.exists():
                total_size = 0
                for file in index_path.rglob('*'):
                    if file.is_file():
                        total_size += file.stat().st_size
                stats["index_size_mb"] = total_size / (1024 * 1024)
        except Exception as e:
            logger.debug(f"操作失败: {e}")
        try:
            config_path = Path("config/whoosh_index_status.json")
            if config_path.exists():
                if HAS_FILE_LOCK:
                    data = atomic_read_json(config_path)
                else:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                stats["last_build_time"] = data.get('last_build_time', '')
        except Exception as e:
            logger.debug(f"操作失败: {e}")
        try:
            with self.ix.searcher() as searcher:
                stats["document_count"] = searcher.doc_count()
                stats["index_built"] = True
        except Exception as e:
            logger.debug(f"操作失败: {e}")
        return stats


# 全局实例
whoosh_search_service = WhooshSearchService()