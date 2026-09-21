import threading
import weakref
from typing import Dict, Any, Optional, Set
from datetime import datetime

from core.logger import logger

from models.resource_report import ResourceInfo, LeakReport


class ResourceTracker:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._resources: Dict[int, ResourceInfo] = {}
        self._weak_refs: Dict[int, weakref.ref] = {}
        self._resource_lock = threading.Lock()
        self._next_id = 1
        self._initialized = True
    
    def register_resource(self, resource: Any, resource_type: str, description: str = "") -> int:
        with self._resource_lock:
            resource_id = self._next_id
            self._next_id += 1
            
            info = ResourceInfo.create(
                resource_id=resource_id,
                resource_type=resource_type,
                description=description
            )
            
            self._resources[resource_id] = info
            
            try:
                weak_ref = weakref.ref(resource, lambda ref: self._on_resource_collected(resource_id))
                self._weak_refs[resource_id] = weak_ref
            except TypeError as e:
                logger.debug(f"资源不支持弱引用: {resource_id}")
            
            return resource_id
    
    def release_resource(self, resource_id: int) -> bool:
        with self._resource_lock:
            if resource_id in self._resources:
                del self._resources[resource_id]
                if resource_id in self._weak_refs:
                    del self._weak_refs[resource_id]
                return True
            return False
    
    def _on_resource_collected(self, resource_id: int) -> None:
        with self._resource_lock:
            if resource_id in self._resources:
                del self._resources[resource_id]
            if resource_id in self._weak_refs:
                del self._weak_refs[resource_id]
    
    def detect_leaks(self, resource_types: Optional[Set[str]] = None) -> LeakReport:
        with self._resource_lock:
            leaked_resources = []
            checked_types = list(resource_types) if resource_types else []
            
            for resource_id, info in self._resources.items():
                if resource_types and info.resource_type not in resource_types:
                    continue
                
                weak_ref = self._weak_refs.get(resource_id)
                if weak_ref is None or weak_ref() is None:
                    leaked_resources.append(info)
            
            total_resources = len([
                r for r in self._resources.values()
                if not resource_types or r.resource_type in resource_types
            ])
            
            return LeakReport(
                timestamp=datetime.now(),
                total_resources=total_resources,
                leaked_count=len(leaked_resources),
                leaked_resources=leaked_resources,
                checked_types=checked_types,
            )
    
    def get_active_resources(self, resource_type: Optional[str] = None) -> list:
        with self._resource_lock:
            resources = []
            for resource_id, info in self._resources.items():
                if resource_type and info.resource_type != resource_type:
                    continue
                
                weak_ref = self._weak_refs.get(resource_id)
                if weak_ref:
                    resource = weak_ref()
                    if resource is not None:
                        resources.append((resource_id, resource, info))
            
            return resources
    
    def get_resource_count(self, resource_type: Optional[str] = None) -> int:
        with self._resource_lock:
            if resource_type:
                return sum(1 for info in self._resources.values() if info.resource_type == resource_type)
            return len(self._resources)
    
    def clear_all(self) -> None:
        with self._resource_lock:
            self._resources.clear()
            self._weak_refs.clear()