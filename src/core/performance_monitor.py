import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from collections import defaultdict

from PySide6.QtCore import QObject, Signal


@dataclass
class PerformanceMetric:
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def complete(self) -> None:
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time


@dataclass
class PerformanceThreshold:
    operation_name: str
    warning_threshold: float
    error_threshold: float
    on_warning: Optional[Callable] = None
    on_error: Optional[Callable] = None


class PerformanceMonitor(QObject):
    performance_warning = Signal(str, float)
    performance_error = Signal(str, float)
    metric_recorded = Signal(PerformanceMetric)
    
    def __init__(self, max_history: int = 1000, parent=None):
        super().__init__(parent)
        
        self._max_history = max_history
        self._metrics: Dict[str, List[PerformanceMetric]] = defaultdict(list)
        self._thresholds: Dict[str, PerformanceThreshold] = {}
        self._active_operations: Dict[str, PerformanceMetric] = {}
        self._lock = threading.Lock()
    
    def start_operation(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        operation_id = f"{operation_name}_{time.time()}_{threading.current_thread().ident}"
        
        metric = PerformanceMetric(
            operation_name=operation_name,
            start_time=time.time(),
            metadata=metadata or {}
        )
        
        with self._lock:
            self._active_operations[operation_id] = metric
        
        return operation_id
    
    def end_operation(self, operation_id: str) -> Optional[PerformanceMetric]:
        with self._lock:
            metric = self._active_operations.pop(operation_id, None)
            
            if metric is None:
                return None
            
            metric.complete()
            
            self._metrics[metric.operation_name].append(metric)
            
            if len(self._metrics[metric.operation_name]) > self._max_history:
                self._metrics[metric.operation_name].pop(0)
            
            self._check_threshold(metric)
            
        self.metric_recorded.emit(metric)
        return metric
    
    def _check_threshold(self, metric: PerformanceMetric) -> None:
        if metric.duration is None:
            return
        
        threshold = self._thresholds.get(metric.operation_name)
        if threshold is None:
            return
        
        if metric.duration >= threshold.error_threshold:
            self.performance_error.emit(metric.operation_name, metric.duration)
            if threshold.on_error:
                threshold.on_error(metric)
        elif metric.duration >= threshold.warning_threshold:
            self.performance_warning.emit(metric.operation_name, metric.duration)
            if threshold.on_warning:
                threshold.on_warning(metric)
    
    def set_threshold(
        self,
        operation_name: str,
        warning_threshold: float,
        error_threshold: float,
        on_warning: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ) -> None:
        threshold = PerformanceThreshold(
            operation_name=operation_name,
            warning_threshold=warning_threshold,
            error_threshold=error_threshold,
            on_warning=on_warning,
            on_error=on_error
        )
        
        with self._lock:
            self._thresholds[operation_name] = threshold
    
    def get_statistics(self, operation_name: str) -> Dict[str, Any]:
        with self._lock:
            metrics = self._metrics.get(operation_name, [])
            
            if not metrics:
                return {
                    'count': 0,
                    'avg_duration': 0.0,
                    'min_duration': 0.0,
                    'max_duration': 0.0,
                    'total_duration': 0.0,
                }
            
            durations = [m.duration for m in metrics if m.duration is not None]
            
            if not durations:
                return {
                    'count': len(metrics),
                    'avg_duration': 0.0,
                    'min_duration': 0.0,
                    'max_duration': 0.0,
                    'total_duration': 0.0,
                }
            
            return {
                'count': len(durations),
                'avg_duration': sum(durations) / len(durations),
                'min_duration': min(durations),
                'max_duration': max(durations),
                'total_duration': sum(durations),
            }
    
    def generate_report(self) -> Dict[str, Any]:
        with self._lock:
            operation_names = list(self._metrics.keys())
        
        report = {}
        for operation_name in operation_names:
            report[operation_name] = self.get_statistics(operation_name)
        
        return report
    
    def clear_history(self, operation_name: Optional[str] = None) -> None:
        with self._lock:
            if operation_name:
                self._metrics[operation_name].clear()
            else:
                self._metrics.clear()
    
    def get_active_operations(self) -> List[str]:
        with self._lock:
            return list(self._active_operations.keys())