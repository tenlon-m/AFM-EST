#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
线程池管理模块
负责管理应用程序的线程池，处理并发任务
"""

import threading
from typing import Callable, Any, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, Future
from .logger import logger

class ThreadPoolManager:
    """
    线程池管理器类
    提供线程池的创建、任务提交和管理功能
    """
    
    def __init__(self, max_workers: Optional[int] = None):
        """
        初始化线程池管理器
        
        Args:
            max_workers: 线程池最大工作线程数，默认值为CPU核心数
        """
        self.max_workers = max_workers
        self.executor: ThreadPoolExecutor = ThreadPoolExecutor(
            max_workers=max_workers, 
            thread_name_prefix="AFM-EST-Thread"
        )
        self.tasks: Dict[str, Future] = {}
        self.task_counter = 0
        self.lock = threading.Lock()
        logger.info(f"线程池已初始化，最大工作线程数: {self.max_workers}")
    
    def submit(self, func: Callable[..., Any], *args, **kwargs) -> Future:
        """
        提交任务到线程池
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            任务的Future对象
        """
        try:
            # 包装函数，添加异常处理
            def wrapped_func(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"线程池任务执行失败: {func.__name__}, 错误: {e}")
                    logger.exception(f"任务 {func.__name__} 异常详情:")
                    raise
            
            future = self.executor.submit(wrapped_func, *args, **kwargs)
            
            # 记录任务
            with self.lock:
                task_id = f"task_{self.task_counter}"
                self.task_counter += 1
                self.tasks[task_id] = future
                
                # 任务完成后清理
                def cleanup(fut):
                    with self.lock:
                        if task_id in self.tasks:
                            del self.tasks[task_id]
                
                future.add_done_callback(cleanup)
            
            logger.debug(f"任务已提交到线程池: {func.__name__}, 任务ID: {task_id}")
            return future
        except Exception as e:
            logger.error(f"提交任务到线程池失败: {e}")
            raise
    
    def map(self, func: Callable[..., Any], *iterables, timeout: Optional[float] = None, chunksize: int = 1) -> Any:
        """
        使用线程池映射函数到可迭代对象
        
        Args:
            func: 要执行的函数
            *iterables: 可迭代对象
            timeout: 超时时间
            chunksize: 分块大小
            
        Returns:
            函数执行结果的迭代器
        """
        try:
            # 包装函数，添加异常处理
            def wrapped_func(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"线程池映射任务执行失败: {func.__name__}, 错误: {e}")
                    logger.exception(f"映射任务 {func.__name__} 异常详情:")
                    raise
            
            result = self.executor.map(wrapped_func, *iterables, timeout=timeout, chunksize=chunksize)
            logger.debug(f"映射任务已提交到线程池: {func.__name__}")
            return result
        except Exception as e:
            logger.error(f"映射任务提交到线程池失败: {e}")
            raise
    
    def shutdown(self, wait: bool = True) -> None:
        """
        关闭线程池
        
        Args:
            wait: 是否等待所有任务完成
        """
        try:
            # 清理任务
            with self.lock:
                pending_tasks = len(self.tasks)
                if pending_tasks > 0:
                    logger.warning(f"线程池关闭时还有 {pending_tasks} 个待处理任务")
                self.tasks.clear()
            
            self.executor.shutdown(wait=wait)
            logger.info(f"线程池已关闭，等待任务完成: {wait}")
        except Exception as e:
            logger.error(f"关闭线程池失败: {e}")
    
    def get_max_workers(self) -> Optional[int]:
        """
        获取线程池最大工作线程数
        
        Returns:
            最大工作线程数
        """
        return self.max_workers
    
    def set_max_workers(self, max_workers: int) -> None:
        """
        设置线程池最大工作线程数
        注意：此方法会创建一个新的线程池
        
        Args:
            max_workers: 新的最大工作线程数
        """
        if max_workers != self.max_workers:
            old_executor = self.executor
            self.max_workers = max_workers
            self.executor = ThreadPoolExecutor(
                max_workers=max_workers, 
                thread_name_prefix="AFM-EST-Thread"
            )
            old_executor.shutdown(wait=True)
            logger.info(f"线程池已重新初始化，新的最大工作线程数: {self.max_workers}")
    
    def get_pending_tasks(self) -> int:
        """
        获取待处理任务数量
        
        Returns:
            待处理任务数量
        """
        with self.lock:
            return len(self.tasks)
    
    def check_for_leaks(self) -> None:
        """
        检查线程池资源泄漏
        """
        pending = self.get_pending_tasks()
        if pending > 0:
            logger.warning(f"线程池可能存在资源泄漏，当前还有 {pending} 个待处理任务")
        else:
            logger.debug("线程池资源检查：无待处理任务")

# 创建全局线程池管理器实例
thread_pool_manager = ThreadPoolManager()

# 注册退出处理
def cleanup_on_exit():
    """
    程序退出时清理线程池
    """
    logger.info("程序退出，清理线程池资源")
    thread_pool_manager.check_for_leaks()
    thread_pool_manager.shutdown(wait=True)

# 注册退出处理
import atexit
atexit.register(cleanup_on_exit)
