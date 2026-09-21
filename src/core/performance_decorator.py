import functools

from typing import Callable, Any, Optional

from .performance_monitor import PerformanceMonitor


_performance_monitor: Optional[PerformanceMonitor] = None


def set_performance_monitor(monitor: PerformanceMonitor) -> None:
    global _performance_monitor
    _performance_monitor = monitor


def get_performance_monitor() -> Optional[PerformanceMonitor]:
    return _performance_monitor


def monitor_performance(operation_name: Optional[str] = None) -> Callable:
    def decorator(func: Callable) -> Callable:
        nonlocal operation_name
        if operation_name is None:
            operation_name = func.__name__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            monitor = get_performance_monitor()
            
            if monitor is None:
                return func(*args, **kwargs)
            
            operation_id = monitor.start_operation(operation_name)
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                monitor.end_operation(operation_id)
        
        return wrapper
    
    return decorator


def measure_time(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        monitor = get_performance_monitor()
        operation_id = None
        if monitor:
            operation_id = monitor.start_operation(func.__name__)
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            if monitor and operation_id:
                monitor.end_operation(operation_id)
    
    return wrapper