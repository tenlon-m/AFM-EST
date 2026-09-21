import threading
from typing import Optional, Set
from datetime import datetime

from PySide6.QtCore import QObject, Signal, QTimer

from .resource_tracker import ResourceTracker
from models.resource_report import LeakReport


class LeakDetector(QObject):
    leak_detected = Signal(LeakReport)
    detection_completed = Signal(LeakReport)
    
    DEFAULT_INTERVAL = 300
    DEFAULT_THRESHOLD = 5
    
    def __init__(
        self,
        interval_seconds: int = DEFAULT_INTERVAL,
        leak_threshold: int = DEFAULT_THRESHOLD,
        parent=None
    ):
        super().__init__(parent)
        
        self._interval = interval_seconds
        self._threshold = leak_threshold
        self._resource_tracker = ResourceTracker()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._perform_detection)
        self._is_running = False
        self._last_report: Optional[LeakReport] = None
        self._lock = threading.Lock()
    
    def start(self) -> None:
        with self._lock:
            if not self._is_running:
                self._is_running = True
                self._timer.start(self._interval * 1000)
    
    def stop(self) -> None:
        with self._lock:
            if self._is_running:
                self._is_running = False
                self._timer.stop()
    
    def set_interval(self, seconds: int) -> None:
        self._interval = seconds
        with self._lock:
            if self._is_running:
                self._timer.setInterval(seconds * 1000)
    
    def set_threshold(self, threshold: int) -> None:
        self._threshold = threshold
    
    def _perform_detection(self) -> None:
        report = self.detect_now()
        self._last_report = report
        
        if report.has_leaks:
            self.leak_detected.emit(report)
        
        self.detection_completed.emit(report)
    
    def detect_now(self, resource_types: Optional[Set[str]] = None) -> LeakReport:
        return self._resource_tracker.detect_leaks(resource_types)
    
    def get_last_report(self) -> Optional[LeakReport]:
        return self._last_report
    
    def generate_report(self, resource_types: Optional[Set[str]] = None) -> str:
        report = self.detect_now(resource_types)
        return report.to_string()
    
    def is_running(self) -> bool:
        return self._is_running
    
    def get_interval(self) -> int:
        return self._interval
    
    def get_threshold(self) -> int:
        return self._threshold