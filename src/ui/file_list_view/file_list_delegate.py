
from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from PySide6.QtCore import Qt, QSize, QRect, QModelIndex
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QIcon, QBrush

from models.view_config import ViewMode, IconSize
from .icon_manager import IconManager


class FileListDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._icon_manager = IconManager()
        self._icon_size = IconSize.MEDIUM
        self._view_mode = ViewMode.DETAILS
        self._corner_radius = 8
        
        self._hover_color = QColor(240, 240, 240)
        self._selected_color = QColor(0, 120, 215)
        self._selected_text_color = QColor(255, 255, 255)
        self._text_color = QColor(0, 0, 0)
        self._border_color = QColor(200, 200, 200)
    
    def set_icon_size(self, size: IconSize) -> None:
        self._icon_size = size
    
    def set_view_mode(self, mode: ViewMode) -> None:
        self._view_mode = mode
    
    def set_corner_radius(self, radius: int) -> None:
        self._corner_radius = radius
    
    def set_colors(self, hover_color: QColor, selected_color: QColor, text_color: QColor) -> None:
        self._hover_color = hover_color
        self._selected_color = selected_color
        self._text_color = text_color
    
    def paint(self, painter: QPainter, option, index: QModelIndex):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        
        is_selected = option.state & QStyle.State_Selected
        is_hover = option.state & QStyle.State_MouseOver
        
        self._draw_modern_background(painter, option.rect, is_selected, is_hover)
        
        if is_selected:
            self._draw_rounded_selection(painter, option.rect)
        
        self._draw_content(painter, option, index)
        
        painter.restore()
    
    def _draw_modern_background(self, painter: QPainter, rect: QRect, is_selected: bool, is_hover: bool):
        if is_selected:
            color = self._selected_color
            color.setAlpha(40)
        elif is_hover:
            color = self._hover_color
        else:
            return
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(color))
        
        adjusted_rect = rect.adjusted(2, 2, -2, -2)
        painter.drawRoundedRect(adjusted_rect, self._corner_radius, self._corner_radius)
    
    def _draw_rounded_selection(self, painter: QPainter, rect: QRect):
        pen = QPen(self._selected_color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        
        adjusted_rect = rect.adjusted(2, 2, -2, -2)
        painter.drawRoundedRect(adjusted_rect, self._corner_radius, self._corner_radius)
    
    def _draw_content(self, painter: QPainter, option, index: QModelIndex):
        if self._view_mode == ViewMode.DETAILS:
            self._draw_details_content(painter, option, index)
        elif self._view_mode == ViewMode.ICONS:
            self._draw_icons_content(painter, option, index)
        elif self._view_mode == ViewMode.THUMBNAILS:
            self._draw_thumbnails_content(painter, option, index)
        elif self._view_mode == ViewMode.LIST:
            self._draw_list_content(painter, option, index)
        elif self._view_mode == ViewMode.TILE:
            self._draw_tile_content(painter, option, index)
    
    def _draw_details_content(self, painter: QPainter, option, index: QModelIndex):
        is_selected = option.state & QStyle.State_Selected
        text_color = self._selected_text_color if is_selected else self._text_color
        
        icon_rect = QRect(option.rect.left() + 8, option.rect.top() + 4, 24, 24)
        self._draw_file_icon(painter, icon_rect, index)
        
        text_rect = QRect(icon_rect.right() + 8, option.rect.top(), option.rect.width() - icon_rect.width() - 24, option.rect.height())
        display_text = index.data(Qt.DisplayRole)
        
        if display_text:
            painter.setPen(text_color)
            font = QFont()
            font.setPointSize(9)
            painter.setFont(font)
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, str(display_text))
    
    def _draw_icons_content(self, painter: QPainter, option, index: QModelIndex):
        is_selected = option.state & QStyle.State_Selected
        text_color = self._selected_text_color if is_selected else self._text_color
        
        icon_size = self._icon_size.value
        icon_rect = QRect(
            option.rect.left() + (option.rect.width() - icon_size) // 2,
            option.rect.top() + 8,
            icon_size,
            icon_size
        )
        self._draw_file_icon(painter, icon_rect, index)
        
        text_rect = QRect(
            option.rect.left() + 4,
            icon_rect.bottom() + 4,
            option.rect.width() - 8,
            option.rect.height() - icon_size - 16
        )
        display_text = index.data(Qt.DisplayRole)
        
        if display_text:
            painter.setPen(text_color)
            font = QFont()
            font.setPointSize(9)
            painter.setFont(font)
            
            metrics = painter.fontMetrics()
            elided_text = metrics.elidedText(str(display_text), Qt.ElideRight, text_rect.width())
            painter.drawText(text_rect, Qt.AlignTop | Qt.AlignHCenter, elided_text)
    
    def _draw_thumbnails_content(self, painter: QPainter, option, index: QModelIndex):
        self._draw_icons_content(painter, option, index)
    
    def _draw_list_content(self, painter: QPainter, option, index: QModelIndex):
        self._draw_details_content(painter, option, index)
    
    def _draw_tile_content(self, painter: QPainter, option, index: QModelIndex):
        is_selected = option.state & QStyle.State_Selected
        text_color = self._selected_text_color if is_selected else self._text_color
        
        icon_rect = QRect(option.rect.left() + 8, option.rect.top() + 8, 48, 48)
        self._draw_file_icon(painter, icon_rect, index)
        
        text_rect = QRect(
            icon_rect.right() + 8,
            option.rect.top() + 8,
            option.rect.width() - icon_rect.width() - 24,
            option.rect.height() - 16
        )
        display_text = index.data(Qt.DisplayRole)
        
        if display_text:
            painter.setPen(text_color)
            font = QFont()
            font.setPointSize(10)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(text_rect, Qt.AlignTop | Qt.AlignLeft, str(display_text))
    
    def _draw_file_icon(self, painter: QPainter, rect: QRect, index: QModelIndex):
        file_path = index.data(Qt.UserRole)
        is_dir = index.data(Qt.UserRole + 1)
        
        if is_dir:
            icon = self._icon_manager.get_folder_icon(self._icon_size)
        elif file_path:
            icon = self._icon_manager.get_file_icon(str(file_path), self._icon_size)
        else:
            icon = QIcon()
        
        if not icon.isNull():
            icon.paint(painter, rect)
    
    def sizeHint(self, option, index: QModelIndex) -> QSize:
        if self._view_mode == ViewMode.DETAILS:
            return QSize(200, 32)
        elif self._view_mode == ViewMode.ICONS:
            icon_size = self._icon_size.value
            return QSize(icon_size + 16, icon_size + 48)
        elif self._view_mode == ViewMode.THUMBNAILS:
            icon_size = self._icon_size.value
            return QSize(icon_size + 16, icon_size + 48)
        elif self._view_mode == ViewMode.LIST:
            return QSize(200, 24)
        elif self._view_mode == ViewMode.TILE:
            return QSize(200, 64)
        
        return QSize(200, 32)