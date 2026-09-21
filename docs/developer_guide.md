# AFM-EST 文件管理器 - 开发文档

## 架构设计

### 系统架构

```
┌─────────────────────────────────────────────────┐
│              表示层（UI Layer）                  │
│  MainWindow | DualPane | FunctionPanel | Widgets │
└─────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────┐
│              业务层（Business Layer）            │
│  DiskSelector | AddressBar | FileListView       │
│  QuickAccess | ThemeManager | IconManager       │
│  ThumbnailLoader | VirtualScroller              │
└─────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────┐
│              服务层（Service Layer）             │
│  FileService | SearchService | TransferService  │
│  P2PService | FTPService | PreviewService       │
│  ThumbnailCache | ConfigService                 │
└─────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────┐
│              核心层（Core Layer）                │
│  Config | Logger | ThreadPool | Utils           │
│  LanguageManager | PerformanceMonitor           │
│  ResourceTracker | LeakDetector                 │
└─────────────────────────────────────────────────┘
```

### 目录结构

```
src/
├── models/              # 数据模型
│   ├── __init__.py
│   ├── disk_info.py         # 磁盘信息模型
│   ├── history.py           # 历史记录模型
│   ├── quick_access.py      # 快速访问模型
│   ├── view_config.py       # 视图配置模型
│   ├── theme_config.py      # 主题配置模型
│   ├── resource_report.py   # 资源报告模型
│   └── index_config.py      # 索引配置模型
├── core/                # 核心模块
│   ├── config.py            # 配置管理
│   ├── logger.py            # 日志记录
│   ├── thread_pool.py       # 线程池
│   ├── resource_tracker.py  # 资源追踪
│   ├── leak_detector.py     # 泄漏检测
│   ├── recovery_manager.py  # 异常恢复
│   ├── exception_handler.py # 异常处理
│   ├── performance_monitor.py # 性能监控
│   ├── performance_decorator.py # 性能装饰器
│   ├── language_manager.py  # 语言管理
│   ├── platform_detector.py # 平台检测
│   ├── file_system_adapter.py # 文件系统适配
│   └── disk_manager_adapter.py # 磁盘管理适配
├── services/            # 服务层
│   ├── config_service.py    # 配置服务
│   ├── config_migration.py  # 配置迁移
│   ├── index_config_service.py # 索引配置服务
│   ├── index_location_manager.py # 索引位置管理
│   ├── disk_info_provider.py # 磁盘信息提供者
│   ├── bookmark_manager.py  # 收藏夹管理
│   ├── quick_access_manager.py # 快速访问管理
│   ├── thumbnail_cache.py   # 缩略图缓存
│   ├── thumbnail_loader.py  # 缩略图加载器
│   └── p2p/                  # P2P服务模块
│       ├── __init__.py
│       ├── p2p_device.py    # 设备模型
│       ├── connection_state.py # 连接状态
│       ├── transfer_task.py # 传输任务
│       ├── discovery.py     # 设备发现
│       ├── connection.py    # 连接管理
│       ├── transfer.py      # 文件传输
│       └── p2p_service.py   # 统一接口
└── ui/                  # UI层
    ├── disk_selector/       # 磁盘选择器
    │   ├── __init__.py
    │   ├── disk_selector.py
    │   ├── disk_popup.py
    │   └── disk_info_widget.py
    ├── address_bar/         # 地址栏
    │   ├── __init__.py
    │   ├── address_bar.py
    │   ├── breadcrumb.py
    │   └── path_completer.py
    ├── file_list_view/      # 文件列表视图
    │   ├── __init__.py
    │   ├── file_list_view.py
    │   ├── file_list_delegate.py
    │   ├── virtual_scroller.py
    │   └── icon_manager.py
    ├── theme/               # 主题管理
    │   ├── __init__.py
    │   ├── theme_manager.py
    │   └── theme_styles.py
    └── quick_access/        # 快速访问
        ├── __init__.py
        ├── quick_access_bar.py
        └── quick_access_item.py
```

---

## 核心模块说明

### 1. 数据模型（models）

所有数据模型使用 Python dataclass 实现，提供类型安全和序列化支持。

#### DiskInfo
```python
from models.disk_info import DiskInfo, DriveType

disk = DiskInfo(
    drive_letter="C:",
    display_name="本地磁盘 (C:)",
    drive_type=DriveType.FIXED,
    total_space=100000000000,
    used_space=50000000000,
    free_space=50000000000,
)

# 属性
disk.usage_percentage  # 使用率百分比
disk.usage_level       # 使用率级别（low/medium/high）
disk.formatted_total   # 格式化的总容量字符串
```

#### HistoryManager
```python
from models.history import HistoryManager

manager = HistoryManager()
manager.add("/path/to/file")
history = manager.get_all()
manager.save("config/history.json")
```

#### QuickAccessItem
```python
from models.quick_access import QuickAccessItem

item = QuickAccessItem.create_from_path("/path/to/folder")
item.is_pinned = True
score = item.calculate_score()  # 智能排序分数
```

#### ViewConfig
```python
from models.view_config import ViewConfig, ViewMode, IconSize

config = ViewConfig()
config.view_mode = ViewMode.ICONS
config.icon_size = IconSize.LARGE
data = config.to_dict()
restored = ViewConfig.from_dict(data)
```

### 2. 核心服务（core）

#### ConfigService
```python
from services.config_service import ConfigService

config = ConfigService()
config.set("ui.theme", "dark")
theme = config.get("ui.theme", "light")
```

#### ResourceTracker
```python
from core.resource_tracker import ResourceTracker

tracker = ResourceTracker()
resource_id = tracker.register_resource(resource, "socket", "Network socket")
tracker.release_resource(resource_id)
report = tracker.detect_leaks()
```

#### PerformanceMonitor
```python
from core.performance_monitor import PerformanceMonitor
from core.performance_decorator import monitor_performance

monitor = PerformanceMonitor()

@monitor_performance("file_operation")
def copy_file(src, dst):
    # 文件操作
    pass
```

### 3. UI 组件（ui）

#### DiskSelector
```python
from ui.disk_selector.disk_selector import DiskSelector

selector = DiskSelector()
selector.disk_selected.connect(self.on_disk_selected)
selector.refresh_disks()
```

#### AddressBar
```python
from ui.address_bar.address_bar import AddressBar

address_bar = AddressBar()
address_bar.set_path("/home/user/documents")
address_bar.path_navigated.connect(self.on_path_navigated)
```

#### ModernFileListView
```python
from ui.file_list_view import ModernFileListView
from models.view_config import ViewMode, IconSize

file_view = ModernFileListView()
file_view.set_view_mode(ViewMode.ICONS)
file_view.set_icon_size(IconSize.LARGE)
file_view.set_path("/home/user/documents")

# 信号连接
file_view.item_activated.connect(self.on_item_activated)
file_view.selection_changed.connect(self.on_selection_changed)
file_view.view_mode_changed.connect(self.on_view_mode_changed)
```

#### VirtualScroller
```python
from ui.file_list_view.virtual_scroller import VirtualScroller

scroller = VirtualScroller()
scroller.set_item_count(10000)
scroller.set_item_height(32)
scroller.set_viewport_height(600)
scroller.set_scroll_position(100)

# 获取可见范围
start, end = scroller.get_visible_range()
```

#### ThumbnailLoader
```python
from services.thumbnail_loader import ThumbnailLoader
from PySide6.QtCore import QSize

loader = ThumbnailLoader()
loader.loaded.connect(self.on_thumbnail_loaded)

# 异步加载
pixmap = loader.load_thumbnail_async("/path/to/image.jpg", QSize(100, 100))

# 同步加载
pixmap = loader.load_thumbnail_sync("/path/to/image.jpg", QSize(100, 100))
```

#### ThemeManager
```python
from ui.theme.theme_manager import ThemeManager
from models.theme_config import ThemeType

theme_manager = ThemeManager()
theme_manager.set_theme(ThemeType.DARK)
theme_manager.toggle_theme()

# 监听主题变化
theme_manager.theme_changed.connect(self.on_theme_changed)
```

---

## 开发指南

### 代码规范

1. **类型注解**：所有函数和方法使用类型注解
2. **文档字符串**：公共方法提供文档字符串
3. **异常处理**：使用异常处理器捕获和处理异常
4. **日志记录**：使用 Logger 记录关键操作

### 添加新功能

1. 在 `models/` 创建数据模型
2. 在 `services/` 创建服务类
3. 在 `ui/` 创建 UI 组件
4. 编写单元测试

### 性能优化

1. 使用 `@monitor_performance` 装饰器监控性能
2. 大数据集使用虚拟化渲染（VirtualScroller）
3. 异步加载耗时资源（ThumbnailLoader）
4. 使用缓存减少重复计算（ThumbnailCache）

---

## 测试指南

### 测试结构

```
tests/
├── unit/                # 单元测试
├── integration/         # 集成测试
│   ├── test_disk_selector.py
│   ├── test_address_bar.py
│   └── test_file_list_view.py
├── performance/         # 性能测试
│   └── test_performance.py
└── e2e/                 # 端到端测试
    └── test_user_scenarios.py
```

### 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行性能测试
pytest tests/performance/

# 运行端到端测试
pytest tests/e2e/

# 生成覆盖率报告
pytest --cov=src tests/
```

### 性能测试指标

| 测试项 | 目标值 | 说明 |
|-------|--------|------|
| 文件列表渲染 | < 500ms | 1000项以内 |
| 虚拟滚动更新 | < 100ms | 100次滚动操作 |
| 主题切换 | < 300ms | 单次切换 |
| 缩略图缓存操作 | < 100ms | 1000次操作 |
| 图标管理操作 | < 500ms | 1000次操作 |

---

## 部署指南

### 构建可执行文件

```bash
# Windows
python scripts/deploy.py --build --platform=windows

# Linux
python scripts/deploy.py --build --platform=linux
```

### 创建便携版

```bash
python scripts/deploy.py --portable
```

### 创建安装程序

```bash
python scripts/deploy.py --installer
```

### 打包依赖

```bash
python scripts/deploy.py --deps
```

### 完整构建

```bash
python scripts/deploy.py --all
```

---

## API 参考

### ModernFileListView

**方法**：
- `set_view_mode(mode: ViewMode)` - 设置视图模式
- `get_view_mode() -> ViewMode` - 获取视图模式
- `set_icon_size(size: IconSize)` - 设置图标尺寸
- `get_icon_size() -> IconSize` - 获取图标尺寸
- `set_path(path: str)` - 设置当前路径
- `get_current_path() -> Optional[str]` - 获取当前路径
- `refresh()` - 刷新文件列表
- `get_selected_items() -> List[str]` - 获取选中项
- `select_all()` - 全选
- `clear_selection()` - 清除选择

**信号**：
- `item_activated(str)` - 项目激活
- `selection_changed(list)` - 选择变更
- `view_mode_changed(ViewMode)` - 视图模式变更

### ThumbnailLoader

**方法**：
- `load_thumbnail_async(path: str, size: QSize) -> Optional[QPixmap]` - 异步加载
- `load_thumbnail_sync(path: str, size: QSize) -> Optional[QPixmap]` - 同步加载
- `cancel_loading(path: str) -> bool` - 取消加载
- `cancel_all() -> int` - 取消所有加载
- `get_cache_statistics() -> Dict[str, int]` - 获取缓存统计
- `clear_cache()` - 清除缓存
- `cleanup_cache() -> int` - 清理过期缓存

**信号**：
- `loaded(str, QPixmap)` - 缩略图加载完成
- `failed(str)` - 缩略图加载失败

### VirtualScroller

**方法**：
- `set_item_count(count: int)` - 设置项目总数
- `set_item_height(height: int)` - 设置项目高度
- `set_viewport_height(height: int)` - 设置视口高度
- `set_scroll_position(position: int)` - 设置滚动位置
- `get_visible_range() -> Tuple[int, int]` - 获取可见范围
- `get_item_position(index: int) -> int` - 获取项目位置
- `scroll_to_item(index: int) -> int` - 滚动到指定项目

**信号**：
- `range_changed(int, int)` - 可见范围变更

---

## 性能优化建议

### 文件列表性能

1. **启用虚拟化渲染**：默认启用，支持10000+文件
2. **调整缓冲区大小**：VirtualScroller的buffer_size参数
3. **使用详细信息视图**：避免缩略图生成开销
4. **减少缓存大小**：ThumbnailCache的max_size参数

### 内存优化

1. **定期清理缓存**：调用cleanup_cache()清理过期缓存
2. **限制缩略图缓存**：设置合理的max_size和TTL
3. **使用资源追踪**：ResourceTracker检测内存泄漏

### UI响应性

1. **异步加载**：使用ThumbnailLoader异步加载缩略图
2. **延迟渲染**：使用VirtualScroller延迟渲染不可见项
3. **性能监控**：使用@monitor_performance装饰器监控性能

---

**版本**: v1.0.0  
**更新日期**: 2026-06-17
