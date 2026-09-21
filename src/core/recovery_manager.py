import time
import threading
from dataclasses import dataclass, field
from typing import Callable, Any, Optional, List, Type
from datetime import datetime



class RetryStrategy:
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        retryable_exceptions: Optional[List[Type[Exception]]] = None
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.retryable_exceptions = retryable_exceptions or [
            ConnectionError,
            TimeoutError,
            OSError,
        ]
    
    def get_wait_time(self, attempt: int) -> float:
        delay = self.initial_delay * (self.backoff_factor ** attempt)
        return min(delay, self.max_delay)
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        if attempt >= self.max_retries:
            return False
        
        return any(
            isinstance(exception, exc_type)
            for exc_type in self.retryable_exceptions
        )


@dataclass
class RecoveryRecord:
    operation_name: str
    attempt: int
    exception: Exception
    timestamp: datetime = field(default_factory=datetime.now)
    wait_time: float = 0.0
    success: bool = False


class RecoveryManager:
    def __init__(self, strategy: Optional[RetryStrategy] = None):
        self._strategy = strategy or RetryStrategy()
        self._history: List[RecoveryRecord] = []
        self._lock = threading.Lock()
    
    def execute_with_recovery(
        self,
        operation: Callable,
        operation_name: str = "operation",
        *args,
        **kwargs
    ) -> Any:
        attempt = 0
        last_exception: Optional[Exception] = None
        
        while True:
            try:
                result = operation(*args, **kwargs)
                
                if attempt > 0:
                    record = RecoveryRecord(
                        operation_name=operation_name,
                        attempt=attempt,
                        exception=last_exception,
                        success=True
                    )
                    with self._lock:
                        self._history.append(record)
                
                return result
            
            except Exception as e:
                last_exception = e
                
                if not self._strategy.should_retry(e, attempt):
                    raise e
                
                wait_time = self._strategy.get_wait_time(attempt)
                
                record = RecoveryRecord(
                    operation_name=operation_name,
                    attempt=attempt + 1,
                    exception=e,
                    wait_time=wait_time,
                    success=False
                )
                with self._lock:
                    self._history.append(record)
                
                time.sleep(wait_time)
                attempt += 1
    
    def get_history(self, operation_name: Optional[str] = None) -> List[RecoveryRecord]:
        with self._lock:
            if operation_name:
                return [
                    record for record in self._history
                    if record.operation_name == operation_name
                ]
            return self._history.copy()
    
    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()
    
    def get_success_rate(self, operation_name: Optional[str] = None) -> float:
        history = self.get_history(operation_name)
        if not history:
            return 0.0
        
        success_count = sum(1 for record in history if record.success)
        return success_count / len(history)
    
    def set_strategy(self, strategy: RetryStrategy) -> None:
        self._strategy = strategy