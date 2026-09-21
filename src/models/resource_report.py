from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import traceback


@dataclass
class ResourceInfo:
    resource_id: int
    resource_type: str
    allocation_time: datetime
    stack_trace: Optional[str] = None
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'resource_id': self.resource_id,
            'resource_type': self.resource_type,
            'allocation_time': self.allocation_time.isoformat(),
            'stack_trace': self.stack_trace,
            'description': self.description,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResourceInfo':
        return cls(
            resource_id=data['resource_id'],
            resource_type=data['resource_type'],
            allocation_time=datetime.fromisoformat(data['allocation_time']),
            stack_trace=data.get('stack_trace'),
            description=data.get('description', ''),
        )
    
    @classmethod
    def create(cls, resource_id: int, resource_type: str, description: str = "") -> 'ResourceInfo':
        stack_trace = ''.join(traceback.format_stack()[:-1])
        return cls(
            resource_id=resource_id,
            resource_type=resource_type,
            allocation_time=datetime.now(),
            stack_trace=stack_trace,
            description=description,
        )


@dataclass
class LeakReport:
    timestamp: datetime = field(default_factory=datetime.now)
    total_resources: int = 0
    leaked_count: int = 0
    leaked_resources: List[ResourceInfo] = field(default_factory=list)
    checked_types: List[str] = field(default_factory=list)
    
    @property
    def leak_percentage(self) -> float:
        if self.total_resources == 0:
            return 0.0
        return (self.leaked_count / self.total_resources) * 100
    
    @property
    def has_leaks(self) -> bool:
        return self.leaked_count > 0
    
    def add_leaked_resource(self, resource: ResourceInfo) -> None:
        self.leaked_resources.append(resource)
        self.leaked_count = len(self.leaked_resources)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'total_resources': self.total_resources,
            'leaked_count': self.leaked_count,
            'leaked_resources': [r.to_dict() for r in self.leaked_resources],
            'checked_types': self.checked_types,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LeakReport':
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            total_resources=data['total_resources'],
            leaked_count=data['leaked_count'],
            leaked_resources=[
                ResourceInfo.from_dict(r) for r in data.get('leaked_resources', [])
            ],
            checked_types=data.get('checked_types', []),
        )
    
    def to_string(self) -> str:
        lines = [
            "=" * 60,
            "资源泄漏检测报告",
            "=" * 60,
            f"检测时间: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"总资源数: {self.total_resources}",
            f"泄漏数量: {self.leaked_count}",
            f"泄漏比例: {self.leak_percentage:.2f}%",
            f"检测类型: {', '.join(self.checked_types)}",
            "",
        ]
        
        if self.has_leaks:
            lines.append("泄漏资源详情:")
            lines.append("-" * 60)
            for i, resource in enumerate(self.leaked_resources, 1):
                lines.extend([
                    f"[{i}] 资源ID: {resource.resource_id}",
                    f"    类型: {resource.resource_type}",
                    f"    分配时间: {resource.allocation_time.strftime('%Y-%m-%d %H:%M:%S')}",
                    f"    描述: {resource.description}",
                ])
                if resource.stack_trace:
                    lines.append(f"    堆栈跟踪:")
                    for line in resource.stack_trace.split('\n')[:5]:
                        lines.append(f"        {line}")
                lines.append("")
        
        lines.append("=" * 60)
        return '\n'.join(lines)