#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
传输管理模块
实现传输历史记录、队列优化和网络状态监控功能
"""

import os
import sqlite3
import json
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from collections import deque

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from core.logger import logger


class TransferTask:
    """
    传输任务基类
    """
    
    def __init__(self, task_id: str, operation: str, source_path: str, target_path: str):
        """
        初始化传输任务
        
        Args:
            task_id: 任务ID
            operation: 操作类型 (upload, download, p2p_send, p2p_receive)
            source_path: 源路径
            target_path: 目标路径
        """
        self.task_id = task_id
        self.operation = operation
        self.source_path = source_path
        self.target_path = target_path
        self.status = "pending"  # pending, running, completed, failed, cancelled
        self.progress = 0
        self.total_size = 0
        self.speed = 0
        self.start_time = None
        self.end_time = None
        self.error_message = ""
        self.priority = 0
        self.retry_count = 0
        self.max_retries = 3
    
    def to_dict(self) -> Dict:
        """
        转换为字典
        
        Returns:
            Dict: 任务信息字典
        """
        return {
            "task_id": self.task_id,
            "operation": self.operation,
            "source_path": self.source_path,
            "target_path": self.target_path,
            "status": self.status,
            "progress": self.progress,
            "total_size": self.total_size,
            "speed": self.speed,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "error_message": self.error_message,
            "priority": self.priority,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }

class TransferHistory:
    """
    传输历史记录类
    """
    
    def __init__(self, db_path: str = "transfer_history.db"):
        """
        初始化传输历史
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """
        初始化数据库
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建历史记录表
            cursor.execute("""
        CREATE TABLE IF NOT EXISTS transfer_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE,
            operation TEXT,
            source_path TEXT,
            target_path TEXT,
            status TEXT,
            progress INTEGER,
            total_size INTEGER,
            speed REAL,
            start_time TEXT,
            end_time TEXT,
            error_message TEXT,
            created_at TEXT
        )
        """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_id ON transfer_history (task_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON transfer_history (status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON transfer_history (created_at)")
            
            conn.commit()
        finally:
            if conn:
                conn.close()
    
    def add_record(self, task: TransferTask):
        """
        添加传输记录
        
        Args:
            task: 传输任务对象
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            task_info = task.to_dict()
            cursor.execute("""
        INSERT OR REPLACE INTO transfer_history (
            task_id, operation, source_path, target_path, status, 
            progress, total_size, speed, start_time, end_time, 
            error_message, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
                task_info["task_id"],
                task_info["operation"],
                task_info["source_path"],
                task_info["target_path"],
                task_info["status"],
                task_info["progress"],
                task_info["total_size"],
                task_info["speed"],
                task_info["start_time"],
                task_info["end_time"],
                task_info["error_message"],
                datetime.now().isoformat()
            ))
            
            conn.commit()
        finally:
            if conn:
                conn.close()
    
    def get_records(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        获取传输记录
        
        Args:
            limit: 限制数量
            offset: 偏移量
        
        Returns:
            List[Dict]: 传输记录列表
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
        SELECT task_id, operation, source_path, target_path, status, 
               progress, total_size, speed, start_time, end_time, 
               error_message, created_at
        FROM transfer_history
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """, (limit, offset))
            
            records = []
            for row in cursor.fetchall():
                records.append({
                    "task_id": row[0],
                    "operation": row[1],
                    "source_path": row[2],
                    "target_path": row[3],
                    "status": row[4],
                    "progress": row[5],
                    "total_size": row[6],
                    "speed": row[7],
                    "start_time": row[8],
                    "end_time": row[9],
                    "error_message": row[10],
                    "created_at": row[11]
                })
            
            return records
        finally:
            if conn:
                conn.close()
    
    def get_failed_records(self) -> List[Dict]:
        """
        获取失败的传输记录
        
        Returns:
            List[Dict]: 失败记录列表
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
        SELECT task_id, operation, source_path, target_path, status, 
               progress, total_size, speed, start_time, end_time, 
               error_message, created_at
        FROM transfer_history
        WHERE status = 'failed'
        ORDER BY created_at DESC
        """)
            
            records = []
            for row in cursor.fetchall():
                records.append({
                    "task_id": row[0],
                    "operation": row[1],
                    "source_path": row[2],
                    "target_path": row[3],
                    "status": row[4],
                    "progress": row[5],
                    "total_size": row[6],
                    "speed": row[7],
                    "start_time": row[8],
                    "end_time": row[9],
                    "error_message": row[10],
                    "created_at": row[11]
                })
            
            return records
        finally:
            if conn:
                conn.close()
    
    def delete_record(self, task_id: str):
        """
        删除传输记录
        
        Args:
            task_id: 任务ID
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM transfer_history WHERE task_id = ?", (task_id,))
            conn.commit()
        finally:
            if conn:
                conn.close()
    
    def clear_records(self, days: int = 30):
        """
        清理旧记录
        
        Args:
            days: 保留天数
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            cursor.execute("DELETE FROM transfer_history WHERE created_at < ?", (cutoff_date,))
            
            conn.commit()
        finally:
            if conn:
                conn.close()
    
    def export_records(self, format: str = "csv", output_path: str = "transfer_history") -> str:
        """
        导出传输记录
        
        Args:
            format: 导出格式 (csv, json)
            output_path: 输出路径
        
        Returns:
            str: 导出文件路径
        """
        records = self.get_records(limit=10000)
        
        if format == "json":
            output_file = f"{output_path}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
        
        elif format == "csv":
            output_file = f"{output_path}.csv"
            import csv
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                if records:
                    fieldnames = records[0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(records)
        
        else:
            raise ValueError(f"不支持的导出格式: {format}")
        
        return output_file

class TransferQueue:
    """
    传输队列类
    """
    
    def __init__(self, max_concurrent: int = 4):
        """
        初始化传输队列
        
        Args:
            max_concurrent: 最大并发任务数
        """
        self.queue = deque()
        self.running_tasks = set()
        self.max_concurrent = max_concurrent
        self.lock = threading.RLock()
        self.task_history = {}
    
    def add_task(self, task: TransferTask):
        """
        添加任务到队列
        
        Args:
            task: 传输任务
        """
        with self.lock:
            self.queue.append(task)
            self.task_history[task.task_id] = task
    
    def get_next_task(self) -> Optional[TransferTask]:
        """
        获取下一个任务
        
        Returns:
            Optional[TransferTask]: 传输任务
        """
        with self.lock:
            if len(self.running_tasks) < self.max_concurrent and self.queue:
                task = self.queue.popleft()
                self.running_tasks.add(task.task_id)
                return task
            return None
    
    def task_completed(self, task_id: str):
        """
        任务完成
        
        Args:
            task_id: 任务ID
        """
        with self.lock:
            if task_id in self.running_tasks:
                self.running_tasks.remove(task_id)
    
    def cancel_task(self, task_id: str):
        """
        取消任务
        
        Args:
            task_id: 任务ID
        """
        with self.lock:
            # 从队列中移除
            new_queue = deque()
            for task in self.queue:
                if task.task_id != task_id:
                    new_queue.append(task)
            self.queue = new_queue
            
            # 从运行中移除
            if task_id in self.running_tasks:
                self.running_tasks.remove(task_id)
            
            # 更新任务状态
            if task_id in self.task_history:
                self.task_history[task_id].status = "cancelled"
                self.task_history[task_id].end_time = datetime.now()
    
    def get_task(self, task_id: str) -> Optional[TransferTask]:
        """
        获取任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            Optional[TransferTask]: 传输任务
        """
        with self.lock:
            return self.task_history.get(task_id)
    
    def get_all_tasks(self) -> List[TransferTask]:
        """
        获取所有任务
        
        Returns:
            List[TransferTask]: 任务列表
        """
        with self.lock:
            return list(self.task_history.values())
    
    def get_pending_tasks(self) -> List[TransferTask]:
        """
        获取待处理任务
        
        Returns:
            List[TransferTask]: 待处理任务列表
        """
        with self.lock:
            return [task for task in self.queue]
    
    def get_running_tasks(self) -> List[TransferTask]:
        """
        获取运行中任务
        
        Returns:
            List[TransferTask]: 运行中任务列表
        """
        with self.lock:
            return [self.task_history[task_id] for task_id in self.running_tasks if task_id in self.task_history]
    
    def reorder_tasks(self, task_ids: List[str]):
        """
        重新排序任务
        
        Args:
            task_ids: 任务ID列表，按优先级排序
        """
        with self.lock:
            # 重建队列
            new_queue = deque()
            remaining_tasks = set(task.task_id for task in self.queue)
            
            # 按指定顺序添加任务
            for task_id in task_ids:
                if task_id in remaining_tasks:
                    for task in self.queue:
                        if task.task_id == task_id:
                            new_queue.append(task)
                            remaining_tasks.remove(task_id)
                            break
            
            # 添加剩余任务
            for task in self.queue:
                if task.task_id in remaining_tasks:
                    new_queue.append(task)
            
            self.queue = new_queue

class NetworkMonitor:
    """
    网络状态监控类
    """
    
    def __init__(self):
        """
        初始化网络监控
        """
        self.network_stats = {}
        self.last_io = None
        self.last_time = time.time()
        self.speed_history = deque(maxlen=60)
        self.lock = threading.Lock()
        
        if not HAS_PSUTIL:
            return
        
        self.last_io = psutil.net_io_counters()
    
    def get_network_speed(self) -> Dict[str, float]:
        """
        获取网络速度
        
        Returns:
            Dict[str, float]: 上传和下载速度 (KB/s)
        """
        if not HAS_PSUTIL:
            return {"upload": 0, "download": 0}
        
        with self.lock:
            current_io = psutil.net_io_counters()
            current_time = time.time()
            
            # 计算时间差
            time_diff = current_time - self.last_time
            if time_diff < 0.1:
                return {"upload": 0, "download": 0}
            
            # 检查计数器是否重置
            if current_io.bytes_sent < self.last_io.bytes_sent or current_io.bytes_recv < self.last_io.bytes_recv:
                self.last_io = current_io
                self.last_time = current_time
                return {"upload": 0, "download": 0}
            
            # 计算数据差
            upload_diff = current_io.bytes_sent - self.last_io.bytes_sent
            download_diff = current_io.bytes_recv - self.last_io.bytes_recv
            
            # 计算速度 (KB/s)
            upload_speed = upload_diff / time_diff / 1024
            download_speed = download_diff / time_diff / 1024
            
            # 更新历史数据
            self.last_io = current_io
            self.last_time = current_time
            
            # 保存速度历史
            self.speed_history.append((upload_speed, download_speed))
            
            return {"upload": upload_speed, "download": download_speed}
    
    def get_average_speed(self, seconds: int = 10) -> Dict[str, float]:
        """
        获取平均网络速度
        
        Args:
            seconds: 统计秒数
        
        Returns:
            Dict[str, float]: 平均上传和下载速度
        """
        with self.lock:
            if not self.speed_history:
                return {"upload": 0, "download": 0}
            
            sample_size = min(seconds, len(self.speed_history))
            samples = list(self.speed_history)[-sample_size:]
            
            avg_upload = sum(s[0] for s in samples) / sample_size
            avg_download = sum(s[1] for s in samples) / sample_size
            
            return {"upload": avg_upload, "download": avg_download}
    
    def get_network_status(self) -> Dict:
        """
        获取网络状态
        
        Returns:
            Dict: 网络状态信息
        """
        speed = self.get_network_speed()
        avg_speed = self.get_average_speed()
        
        interfaces = {}
        for interface, addrs in psutil.net_if_addrs().items():
            ip_addresses = []
            for addr in addrs:
                if addr.family == 2:  # AF_INET
                    ip_addresses.append(addr.address)
            if ip_addresses:
                interfaces[interface] = ip_addresses
        
        return {
            "speed": speed,
            "average_speed": avg_speed,
            "interfaces": interfaces,
            "timestamp": time.time()
        }
    
    def is_network_available(self) -> bool:
        """
        检查网络是否可用
        
        Returns:
            bool: 网络是否可用
        """
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return False


class TransferManager:
    """传输管理器类"""
    
    def __init__(self, history_db: str = 'transfer_history.db'):
        """初始化传输管理器
        
        Args:
            history_db: 历史记录数据库路径
        """
        self.transfer_queue = TransferQueue()
        self.transfer_history = TransferHistory(history_db)
        self.network_monitor = NetworkMonitor()
        self.task_workers = []
        self.running = False
        self.max_workers = 4
        self.retry_interval = 5
        
        # 速度限制
        self.speed_limit_enabled = False
        self.max_speed_bps = 0
        self.current_speed_bps = 0
        self._speed_adjust_timer = None
        
        # 连接池
        self._connection_pool = {}
        self._pool_lock = threading.Lock()
    
    def set_speed_limit(self, enabled: bool, max_speed_mbps: float = 0):
        """设置速度限制
        
        Args:
            enabled: 是否启用速度限制
            max_speed_mbps: 最大速度（MB/s），0表示不限制
        """
        self.speed_limit_enabled = enabled
        self.max_speed_bps = max_speed_mbps * 1024 * 1024 if max_speed_mbps > 0 else 0
        status = '启用' if enabled else '禁用'
        logger.info(f'速度限制: {status}, 最大速度: {max_speed_mbps} MB/s')
    
    def get_connection(self, host: str, port: int):
        """从连接池获取连接
        
        Args:
            host: 主机地址
            port: 端口号
        
        Returns:
            连接对象
        """
        key = f'{host}:{port}'
        with self._pool_lock:
            if key in self._connection_pool:
                conn = self._connection_pool[key]
                if self._is_connection_valid(conn):
                    return conn
                else:
                    del self._connection_pool[key]
            return None
    
    def put_connection(self, host: str, port: int, conn):
        """将连接放回连接池
        
        Args:
            host: 主机地址
            port: 端口号
            conn: 连接对象
        """
        key = f'{host}:{port}'
        with self._pool_lock:
            if len(self._connection_pool) < 10:
                self._connection_pool[key] = conn
    
    def _is_connection_valid(self, conn) -> bool:
        """检查连接是否有效"""
        try:
            if hasattr(conn, 'ping'):
                conn.ping()
                return True
        except Exception as e:
            logger.debug(f"操作失败: {e}")
            return False
        return False
    
    def start(self):
        """启动传输管理器"""
        self.running = True
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker_thread)
            worker.daemon = True
            worker.start()
            self.task_workers.append(worker)
    
    def stop(self):
        """停止传输管理器"""
        self.running = False
        for worker in self.task_workers:
            worker.join(timeout=2)
    
    def _worker_thread(self):
        """工作线程"""
        while self.running:
            try:
                task = self.transfer_queue.get_next_task()
                if task:
                    self._process_task(task)
                    self.transfer_queue.task_completed(task.task_id)
                    self.transfer_history.add_record(task)
                else:
                    time.sleep(0.1)
            except Exception as e:
                logger.error(f'工作线程异常: {e}')
                time.sleep(0.1)
    
    def _process_task(self, task: TransferTask):
        task.status = 'running'
        task.start_time = datetime.now()
        try:
            import shutil
            source_path = task.source_path
            dest_path = task.dest_path
            
            if not os.path.exists(source_path):
                raise FileNotFoundError(f"源文件不存在: {source_path}")
            
            task.total_size = os.path.getsize(source_path)
            dest_dir = os.path.dirname(dest_path)
            if dest_dir and not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)
            
            shutil.copy2(source_path, dest_path)
            
            if task.status != 'cancelled':
                task.status = 'completed'
                task.progress = task.total_size
        except Exception as e:
            task.status = 'failed'
            task.error_message = str(e)
            task.retry_count += 1
            if task.retry_count < task.max_retries:
                time.sleep(self.retry_interval)
                self.transfer_queue.add_task(task)
        finally:
            task.end_time = datetime.now()
    
    def add_task(self, task: TransferTask):
        """添加传输任务
        
        Args:
            task: 传输任务
        """
        self.transfer_queue.add_task(task)
    
    def cancel_task(self, task_id: str):
        """取消传输任务
        
        Args:
            task_id: 任务ID
        """
        self.transfer_queue.cancel_task(task_id)
    
    def get_task(self, task_id: str) -> Optional[TransferTask]:
        """获取传输任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            Optional[TransferTask]: 传输任务
        """
        return self.transfer_queue.get_task(task_id)
    
    def get_all_tasks(self) -> List[TransferTask]:
        """获取所有传输任务
        
        Returns:
            List[TransferTask]: 传输任务列表
        """
        return self.transfer_queue.get_all_tasks()
    
    def get_transfer_history(self, limit: int = 100) -> List[Dict]:
        """获取传输历史
        
        Args:
            limit: 限制数量
        
        Returns:
            List[Dict]: 传输历史记录
        """
        return self.transfer_history.get_records(limit)
    
    def get_network_status(self) -> Dict:
        """获取网络状态
        
        Returns:
            Dict: 网络状态信息
        """
        return self.network_monitor.get_network_status()
    
    def reorder_tasks(self, task_ids: List[str]):
        """重新排序任务
        
        Args:
            task_ids: 任务ID列表
        """
        self.transfer_queue.reorder_tasks(task_ids)
    
    def retry_failed_task(self, task_id: str):
        """重试失败任务
        
        Args:
            task_id: 任务ID
        """
        task = self.transfer_queue.get_task(task_id)
        if task and task.status == 'failed':
            task.status = 'pending'
            task.retry_count = 0
            task.error_message = ''
            task.start_time = None
            task.end_time = None
            self.transfer_queue.add_task(task)
