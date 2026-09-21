#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志系统模块
负责记录应用程序的日志信息
"""

import logging
import os
import traceback
import sys
from pathlib import Path
from datetime import datetime

def _get_default_log_dir() -> str:
    log_dir_env = os.environ.get('AFM_EST_LOG_DIR')
    if log_dir_env:
        return log_dir_env
    
    try:
        from services.index_location_manager import IndexLocationManager
        manager = IndexLocationManager()
        index_dir = manager.get_default_location()
        return str(Path(index_dir).parent / 'logs')
    except Exception:
        pass
    
    appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
    return str(Path(appdata) / 'AFM-EST' / 'logs')

class Logger:
    """
    日志系统类
    提供不同级别的日志记录功能
    """
    
    def __init__(self, log_dir: str = None, log_level: int = logging.INFO):
        """
        初始化日志系统
        
        Args:
            log_dir: 日志文件目录
            log_level: 日志级别
        """
        if log_dir is None:
            log_dir = _get_default_log_dir()
        self.log_dir = Path(log_dir)
        self.log_level = log_level
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """
        设置日志记录器
        
        Returns:
            配置好的日志记录器
        """
        # 确保日志目录存在
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建日志记录器
        logger = logging.getLogger("AFM-EST")
        logger.setLevel(self.log_level)
        logger.propagate = False
        
        # 清除现有的处理器
        if logger.handlers:
            logger.handlers.clear()
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        
        # 创建文件处理器
        log_file = self.log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(self.log_level)
        
        # 定义日志格式
        log_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        console_handler.setFormatter(log_format)
        file_handler.setFormatter(log_format)
        
        # 添加处理器到日志记录器
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        return logger
    
    def debug(self, message: str, *args, **kwargs) -> None:
        """
        记录调试级别的日志
        
        Args:
            message: 日志消息
            *args: 格式化参数
            **kwargs: 额外参数
        """
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs) -> None:
        """
        记录信息级别的日志
        
        Args:
            message: 日志消息
            *args: 格式化参数
            **kwargs: 额外参数
        """
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs) -> None:
        """
        记录警告级别的日志
        
        Args:
            message: 日志消息
            *args: 格式化参数
            **kwargs: 额外参数
        """
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs) -> None:
        """
        记录错误级别的日志
        
        Args:
            message: 日志消息
            *args: 格式化参数
            **kwargs: 额外参数
        """
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs) -> None:
        """
        记录严重错误级别的日志
        
        Args:
            message: 日志消息
            *args: 格式化参数
            **kwargs: 额外参数
        """
        self.logger.critical(message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs) -> None:
        """
        记录异常级别的日志
        
        Args:
            message: 日志消息
            *args: 格式化参数
            **kwargs: 额外参数
        """
        self.logger.exception(message, *args, **kwargs)
    
    def crash_report(self, exc_info: tuple = None) -> None:
        if exc_info is None:
            exc_info = sys.exc_info()
        
        if not exc_info or exc_info[0] is None:
            self.warning("crash_report调用时无异常信息")
            return
        
        crash_dir = self.log_dir / "crashes"
        crash_dir.mkdir(parents=True, exist_ok=True)
        
        crash_file = crash_dir / f"crash_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        try:
            with open(crash_file, 'w', encoding='utf-8') as f:
                f.write(f"=== AFM-EST 崩溃报告 ===\n")
                f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Python版本: {sys.version}\n")
                f.write(f"系统: {sys.platform}\n")
                f.write(f"异常类型: {exc_info[0].__name__ if exc_info[0] else 'Unknown'}\n")
                f.write(f"异常消息: {exc_info[1]}\n")
                f.write("\n=== 堆栈跟踪 ===\n")
                if exc_info[2]:
                    traceback.print_exception(exc_info[0], exc_info[1], exc_info[2], file=f)
            
            self.critical(f"已生成崩溃报告: {crash_file}")
        except Exception as e:
            self.error(f"生成崩溃报告失败: {e}")
    
    def close(self) -> None:
        """
        关闭日志系统，释放资源
        """
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)

# 创建全局日志记录器实例
logger = Logger()

# 设置全局异常处理
def setup_global_exception_handler():
    """
    设置全局异常处理
    """
    def exception_handler(exc_type, exc_value, exc_traceback):
        """
        全局异常处理器
        """
        if issubclass(exc_type, KeyboardInterrupt):
            # 忽略Ctrl+C中断
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # 记录异常
        logger.critical(f"发生未捕获的异常: {exc_value}")
        logger.crash_report((exc_type, exc_value, exc_traceback))
        
        # 调用原始的异常处理
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    sys.excepthook = exception_handler

# 设置全局异常处理
setup_global_exception_handler()


class NullLogger:
    """统一的无操作日志器，用于core.logger导入失败时的回退"""
    def debug(self, *args, **kwargs): pass
    def info(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass
    def critical(self, *args, **kwargs): pass
    def exception(self, *args, **kwargs): pass

null_logger = NullLogger()
