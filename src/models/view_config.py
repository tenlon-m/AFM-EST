from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class ViewMode(Enum):
    DETAILS = "details"
    ICONS = "icons"
    THUMBNAILS = "thumbnails"
    LIST = "list"
    TILE = "tile"


class IconSize(Enum):
    SMALL = 16
    MEDIUM = 32
    LARGE = 48
    EXTRA_LARGE = 96
    
    @classmethod
    def from_value(cls, value: int) -> 'IconSize':
        for size in cls:
            if size.value == value:
                return size
        return cls.MEDIUM


@dataclass
class ColumnConfig:
    name: str
    display_name: str
    width: int
    visible: bool = True
    order: int = 0
    sortable: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'display_name': self.display_name,
            'width': self.width,
            'visible': self.visible,
            'order': self.order,
            'sortable': self.sortable,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ColumnConfig':
        return cls(
            name=data['name'],
            display_name=data['display_name'],
            width=data['width'],
            visible=data.get('visible', True),
            order=data.get('order', 0),
            sortable=data.get('sortable', True),
        )


@dataclass
class ViewConfig:
    view_mode: ViewMode = ViewMode.DETAILS
    icon_size: IconSize = IconSize.MEDIUM
    columns: List[ColumnConfig] = field(default_factory=list)
    sort_column: str = "name"
    sort_order: int = 0
    show_hidden_files: bool = False
    group_by: str = "none"
    
    def __post_init__(self):
        if not self.columns:
            self.columns = self._create_default_columns()
    
    @staticmethod
    def _create_default_columns() -> List[ColumnConfig]:
        return [
            ColumnConfig(name="name", display_name="名称", width=200, order=0),
            ColumnConfig(name="size", display_name="大小", width=100, order=1),
            ColumnConfig(name="type", display_name="类型", width=100, order=2),
            ColumnConfig(name="modified", display_name="修改日期", width=150, order=3),
            ColumnConfig(name="created", display_name="创建日期", width=150, order=4, visible=False),
        ]
    
    def get_visible_columns(self) -> List[ColumnConfig]:
        return sorted(
            [col for col in self.columns if col.visible],
            key=lambda x: x.order
        )
    
    def get_column(self, name: str) -> Optional[ColumnConfig]:
        for col in self.columns:
            if col.name == name:
                return col
        return None
    
    def set_column_width(self, name: str, width: int) -> None:
        col = self.get_column(name)
        if col:
            col.width = width
    
    def set_column_visible(self, name: str, visible: bool) -> None:
        col = self.get_column(name)
        if col:
            col.visible = visible
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'view_mode': self.view_mode.value,
            'icon_size': self.icon_size.value,
            'columns': [col.to_dict() for col in self.columns],
            'sort_column': self.sort_column,
            'sort_order': self.sort_order,
            'show_hidden_files': self.show_hidden_files,
            'group_by': self.group_by,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ViewConfig':
        columns = [
            ColumnConfig.from_dict(col_data)
            for col_data in data.get('columns', [])
        ]
        
        return cls(
            view_mode=ViewMode(data.get('view_mode', 'details')),
            icon_size=IconSize.from_value(data.get('icon_size', 32)),
            columns=columns if columns else None,
            sort_column=data.get('sort_column', 'name'),
            sort_order=data.get('sort_order', 0),
            show_hidden_files=data.get('show_hidden_files', False),
            group_by=data.get('group_by', 'none'),
        )