import functools
from typing import Callable, Any
from enum import Enum

from core.logger import logger as _logger


class ExceptionCategory(Enum):
    NETWORK = "network"
    FILE_SYSTEM = "file_system"
    PERMISSION = "permission"
    CONFIG = "config"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


class ExceptionHandler:
    def __init__(self, logger=None):
        self._logger = logger or _logger
    
    def _categorize(self, exception: Exception) -> ExceptionCategory:
        if isinstance(exception, (ConnectionError, TimeoutError, OSError)):
            if "network" in str(exception).lower() or "connection" in str(exception).lower():
                return ExceptionCategory.NETWORK
        
        if isinstance(exception, (FileNotFoundError, FileExistsError, IsADirectoryError, NotADirectoryError)):
            return ExceptionCategory.FILE_SYSTEM
        
        if isinstance(exception, PermissionError):
            return ExceptionCategory.PERMISSION
        
        if isinstance(exception, (KeyError, ValueError, TypeError)) and "config" in str(exception).lower():
            return ExceptionCategory.CONFIG
        
        if isinstance(exception, MemoryError):
            return ExceptionCategory.RESOURCE
        
        return ExceptionCategory.UNKNOWN
    
    def handle_network_exception(self, exception: Exception, context: str = "") -> None:
        self._logger.error(f"Network error in {context}: {exception}")
    
    def handle_file_system_exception(self, exception: Exception, context: str = "") -> None:
        self._logger.error(f"File system error in {context}: {exception}")
    
    def handle_permission_exception(self, exception: Exception, context: str = "") -> None:
        self._logger.error(f"Permission error in {context}: {exception}")
    
    def handle_config_exception(self, exception: Exception, context: str = "") -> None:
        self._logger.error(f"Configuration error in {context}: {exception}")
    
    def handle_resource_exception(self, exception: Exception, context: str = "") -> None:
        self._logger.error(f"Resource error in {context}: {exception}")
    
    def handle_unknown_exception(self, exception: Exception, context: str = "") -> None:
        self._logger.error(f"Unknown error in {context}: {exception}")
    
    def handle(self, exception: Exception, context: str = "") -> None:
        category = self._categorize(exception)
        
        handlers = {
            ExceptionCategory.NETWORK: self.handle_network_exception,
            ExceptionCategory.FILE_SYSTEM: self.handle_file_system_exception,
            ExceptionCategory.PERMISSION: self.handle_permission_exception,
            ExceptionCategory.CONFIG: self.handle_config_exception,
            ExceptionCategory.RESOURCE: self.handle_resource_exception,
            ExceptionCategory.UNKNOWN: self.handle_unknown_exception,
        }
        
        handler = handlers.get(category, self.handle_unknown_exception)
        handler(exception, context)


def safe_file_operation(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            _logger.error(f"File not found: {e}")
            raise
        except PermissionError as e:
            _logger.error(f"Permission denied: {e}")
            raise
        except OSError as e:
            _logger.error(f"OS error: {e}")
            raise
        except Exception as e:
            _logger.error(f"Unexpected error in file operation: {e}")
            raise
    
    return wrapper


def safe_directory_operation(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except NotADirectoryError as e:
            _logger.error(f"Not a directory: {e}")
            raise
        except IsADirectoryError as e:
            _logger.error(f"Is a directory: {e}")
            raise
        except PermissionError as e:
            _logger.error(f"Permission denied: {e}")
            raise
        except OSError as e:
            _logger.error(f"OS error: {e}")
            raise
        except Exception as e:
            _logger.error(f"Unexpected error in directory operation: {e}")
            raise
    
    return wrapper