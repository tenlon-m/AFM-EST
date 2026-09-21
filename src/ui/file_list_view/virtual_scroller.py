from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass
import time
from bisect import bisect_right

from PySide6.QtCore import QObject, Signal, QRect, QTimer


@dataclass
class VirtualItem:
    index: int
    position: int
    size: int
    visible: bool


@dataclass
class VirtualScrollConfig:
    buffer_size: int = 5
    item_height: int = 32
    viewport_height: int = 0
    total_items: int = 0
    
    def validate(self) -> bool:
        return (
            self.buffer_size >= 0 and
            self.item_height > 0 and
            self.viewport_height >= 0 and
            self.total_items >= 0
        )


class ScrollThrottler:
    MIN_INTERVAL = 0.016
    
    def __init__(self, interval: float = MIN_INTERVAL):
        self._interval = interval
        self._last_time = 0.0
        self._pending_position: Optional[int] = None
        self._callback: Optional[Callable[[int], None]] = None
    
    def set_callback(self, callback: Callable[[int], None]) -> None:
        self._callback = callback
    
    def throttle(self, position: int) -> bool:
        current_time = time.time()
        elapsed = current_time - self._last_time
        
        if elapsed >= self._interval:
            self._last_time = current_time
            if self._callback:
                self._callback(position)
            self._pending_position = None
            return True
        else:
            self._pending_position = position
            return False
    
    def flush(self) -> None:
        if self._pending_position is not None and self._callback:
            self._callback(self._pending_position)
            self._pending_position = None
            self._last_time = time.time()


class VirtualScroller(QObject):
    range_changed = Signal(int, int)
    scroll_optimized = Signal(int)
    
    DEFAULT_BUFFER_SIZE = 5
    DEFAULT_ITEM_HEIGHT = 32
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._item_count = 0
        self._item_height = self.DEFAULT_ITEM_HEIGHT
        self._buffer_size = self.DEFAULT_BUFFER_SIZE
        self._viewport_height = 0
        self._scroll_position = 0
        self._visible_range: Tuple[int, int] = (0, 0)
        self._dynamic_heights: List[int] = []
        self._use_dynamic_height = False
        
        self._height_prefix_sum: List[int] = []
        
        self._throttler = ScrollThrottler()
        self._throttler.set_callback(self._apply_scroll_position)
        
        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.timeout.connect(self._throttler.flush)
    
    def set_item_count(self, count: int) -> None:
        self._item_count = count
        self._dynamic_heights = [self._item_height] * count
        self._update_height_prefix_sum()
        self._update_visible_range()
    
    def _update_height_prefix_sum(self) -> None:
        self._height_prefix_sum = []
        accumulated = 0
        for height in self._dynamic_heights:
            self._height_prefix_sum.append(accumulated)
            accumulated += height
        self._height_prefix_sum.append(accumulated)
    
    def get_item_count(self) -> int:
        return self._item_count
    
    def set_item_height(self, height: int) -> None:
        if height <= 0:
            return
        
        self._item_height = height
        if not self._use_dynamic_height:
            self._dynamic_heights = [height] * self._item_count
        
        self._update_visible_range()
    
    def get_item_height(self) -> int:
        return self._item_height
    
    def set_buffer_size(self, size: int) -> None:
        self._buffer_size = max(0, size)
        self._update_visible_range()
    
    def set_viewport_height(self, height: int) -> None:
        self._viewport_height = max(0, height)
        self._update_visible_range()
    
    def get_viewport_height(self) -> int:
        return self._viewport_height
    
    def set_scroll_position(self, position: int) -> None:
        self._scroll_position = max(0, position)
        self._update_visible_range()
    
    def get_scroll_position(self) -> int:
        return self._scroll_position
    
    def update_visible_range(self) -> Tuple[int, int]:
        return self._update_visible_range()
    
    def _update_visible_range(self) -> Tuple[int, int]:
        if self._item_count == 0 or self._viewport_height == 0:
            self._visible_range = (0, 0)
            return self._visible_range
        
        if self._use_dynamic_height:
            start_index = self._find_index_at_position(self._scroll_position)
            end_position = self._scroll_position + self._viewport_height
            end_index = self._find_index_at_position(end_position)
        else:
            start_index = self._scroll_position // self._item_height
            visible_count = self._viewport_height // self._item_height + 1
            end_index = start_index + visible_count
        
        start_index = max(0, start_index - self._buffer_size)
        end_index = min(self._item_count - 1, end_index + self._buffer_size)
        
        old_range = self._visible_range
        self._visible_range = (start_index, end_index)
        
        if old_range != self._visible_range:
            self.range_changed.emit(start_index, end_index)
        
        return self._visible_range
    
    def get_visible_range(self) -> Tuple[int, int]:
        return self._visible_range
    
    def get_item_position(self, index: int) -> int:
        if index < 0 or index >= self._item_count:
            return 0
        
        if self._use_dynamic_height:
            return sum(self._dynamic_heights[:index])
        else:
            return index * self._item_height
    
    def get_item_rect(self, index: int) -> QRect:
        if index < 0 or index >= self._item_count:
            return QRect()
        
        y = self.get_item_position(index)
        height = self._dynamic_heights[index] if self._use_dynamic_height else self._item_height
        
        return QRect(0, y, 0, height)
    
    def is_item_visible(self, index: int) -> bool:
        if index < 0 or index >= self._item_count:
            return False
        
        start, end = self._visible_range
        return start <= index <= end
    
    def scroll_to_item(self, index: int) -> int:
        if index < 0 or index >= self._item_count:
            return self._scroll_position
        
        item_position = self.get_item_position(index)
        item_height = self._dynamic_heights[index] if self._use_dynamic_height else self._item_height
        
        if item_position < self._scroll_position:
            new_position = item_position
        elif item_position + item_height > self._scroll_position + self._viewport_height:
            new_position = item_position + item_height - self._viewport_height
        else:
            return self._scroll_position
        
        self._scroll_position = max(0, new_position)
        self._update_visible_range()
        return self._scroll_position
    
    def get_total_height(self) -> int:
        if self._use_dynamic_height:
            return sum(self._dynamic_heights)
        else:
            return self._item_count * self._item_height
    
    def set_dynamic_height_mode(self, enabled: bool) -> None:
        self._use_dynamic_height = enabled
        if not enabled:
            self._dynamic_heights = [self._item_height] * self._item_count
    
    def update_item_height(self, index: int, height: int) -> None:
        if index < 0 or index >= self._item_count or height <= 0:
            return
        
        self._dynamic_heights[index] = height
        self._update_visible_range()
    
    def _find_index_at_position(self, position: int) -> int:
        if not self._height_prefix_sum:
            return 0
        
        index = bisect_right(self._height_prefix_sum, position) - 1
        return max(0, min(index, self._item_count - 1))
    
    def get_visible_items(self) -> List[VirtualItem]:
        start, end = self._visible_range
        items = []
        
        for i in range(start, end + 1):
            position = self.get_item_position(i)
            size = self._dynamic_heights[i] if self._use_dynamic_height else self._item_height
            items.append(VirtualItem(i, position, size, True))
        
        return items
    
    def get_max_scroll_position(self) -> int:
        total_height = self.get_total_height()
        return max(0, total_height - self._viewport_height)
    
    def set_scroll_position_throttled(self, position: int) -> bool:
        if self._throttler.throttle(position):
            self._flush_timer.stop()
            return True
        else:
            self._flush_timer.start(int(self._throttler._interval * 1000))
            return False
    
    def _apply_scroll_position(self, position: int) -> None:
        self._scroll_position = max(0, position)
        self._update_visible_range()
        self.scroll_optimized.emit(self._scroll_position)
    
    def get_statistics(self) -> dict:
        return {
            'item_count': self._item_count,
            'visible_range': self._visible_range,
            'visible_count': self._visible_range[1] - self._visible_range[0] + 1 if self._visible_range[1] >= self._visible_range[0] else 0,
            'scroll_position': self._scroll_position,
            'viewport_height': self._viewport_height,
            'total_height': self.get_total_height(),
            'use_dynamic_height': self._use_dynamic_height,
        }