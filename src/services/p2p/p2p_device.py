from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum


class DeviceStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"


@dataclass
class P2PDevice:
    device_id: str
    hostname: str
    ip_address: str
    port: int
    status: DeviceStatus = DeviceStatus.ONLINE
    last_seen: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'device_id': self.device_id,
            'hostname': self.hostname,
            'ip_address': self.ip_address,
            'port': self.port,
            'status': self.status.value,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'P2PDevice':
        last_seen = None
        if data.get('last_seen'):
            try:
                last_seen = datetime.fromisoformat(data['last_seen'])
            except ValueError:
                pass
        
        return cls(
            device_id=data['device_id'],
            hostname=data['hostname'],
            ip_address=data['ip_address'],
            port=data['port'],
            status=DeviceStatus(data.get('status', 'online')),
            last_seen=last_seen,
            metadata=data.get('metadata', {}),
        )
    
    def update_last_seen(self) -> None:
        self.last_seen = datetime.now()
    
    def is_online(self) -> bool:
        return self.status == DeviceStatus.ONLINE
    
    def get_address(self) -> str:
        return f"{self.ip_address}:{self.port}"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, P2PDevice):
            return False
        return self.device_id == other.device_id
    
    def __hash__(self) -> int:
        return hash(self.device_id)