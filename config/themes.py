#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主题样式表配置
存储浅色和深色主题的样式表
"""

# 浅色主题样式表
LIGHT_THEME = """
/* 全局样式 */
* {
    color: #333333;
    background-color: #ffffff;
}

/* 主窗口 */
QMainWindow {
    background-color: #ffffff;
}

/* 菜单栏 */
QMenuBar {
    background-color: #f5f5f5;
    border-bottom: 1px solid #e0e0e0;
}

QMenuBar::item {
    background-color: transparent;
    padding: 4px 8px;
}

QMenuBar::item:selected {
    background-color: #e0e0e0;
    border-radius: 3px;
}

QMenu {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 3px;
    padding: 4px 0;
}

QMenu::item {
    background-color: transparent;
    padding: 4px 20px;
    min-width: 120px;
}

QMenu::item:selected {
    background-color: #e0e0e0;
}

/* 工具栏 */
QToolBar {
    background-color: #f5f5f5;
    border-bottom: 1px solid #e0e0e0;
    padding: 4px;
}

QToolBar QToolButton {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 3px;
    padding: 4px;
    margin: 2px;
}

QToolBar QToolButton:hover {
    background-color: #e0e0e0;
}

QToolBar QToolButton:pressed {
    background-color: #d0d0d0;
}

/* 地址栏和导航按钮 */
QLineEdit {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 3px;
    padding: 4px 8px;
}

QLineEdit:focus {
    border-color: #2196F3;
    outline: none;
}

QPushButton {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 3px;
    padding: 4px 8px;
    min-width: 60px;
}

QPushButton:hover {
    background-color: #e0e0e0;
}

QPushButton:pressed {
    background-color: #d0d0d0;
}

QPushButton:disabled {
    background-color: #f5f5f5;
    color: #a0a0a0;
}

/* 文件列表 */
QListView, QTableView {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    selection-background-color: #e3f2fd;
    selection-color: #333333;
}

QListView::item, QTableView::item {
    padding: 4px;
}

QListView::item:selected, QTableView::item:selected {
    background-color: #e3f2fd;
}

QTableView::header {
    background-color: #f5f5f5;
    border-bottom: 1px solid #e0e0e0;
}

QTableView::header::section {
    background-color: #f5f5f5;
    padding: 6px;
    border-right: 1px solid #e0e0e0;
}

/* 状态栏 */
QStatusBar {
    background-color: #f5f5f5;
    border-top: 1px solid #e0e0e0;
    color: #666666;
}

/* 分割器 */
QSplitter {
    background-color: #e0e0e0;
}

QSplitter::handle {
    background-color: #e0e0e0;
}

QSplitter::handle:hover {
    background-color: #bdbdbd;
}

/* 标签页 */
QTabWidget {
    background-color: #ffffff;
}

QTabBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e0e0e0;
}

QTabBar::tab {
    background-color: #f5f5f5;
    border: 1px solid #e0e0e0;
    border-bottom: none;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
    padding: 6px 12px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    border-color: #e0e0e0;
    border-bottom: 1px solid #ffffff;
}

/* 分组框 */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 3px;
    padding: 8px;
    margin-top: 6px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    top: -8px;
    padding: 0 4px;
    background-color: #ffffff;
}

/* 下拉框 */
QComboBox {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 3px;
    padding: 4px 8px;
    min-width: 100px;
}

QComboBox:hover {
    border-color: #bdbdbd;
}

QComboBox::drop-down {
    border: none;
    background-color: transparent;
}

QComboBox::down-arrow {
    image: url(:/icons/down_arrow.png);
    width: 16px;
    height: 16px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 3px;
    padding: 2px;
}

/* 复选框和单选按钮 */
QCheckBox, QRadioButton {
    background-color: transparent;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #e0e0e0;
    border-radius: 3px;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #2196F3;
    image: url(:/icons/checkmark.png);
}

QRadioButton::indicator:checked {
    background-color: #2196F3;
    border-radius: 8px;
    image: url(:/icons/dot.png);
}

/* 滚动条 */
QScrollBar:vertical {
    width: 12px;
    background-color: #f5f5f5;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #bdbdbd;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #9e9e9e;
}

QScrollBar:horizontal {
    height: 12px;
    background-color: #f5f5f5;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #bdbdbd;
    border-radius: 6px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #9e9e9e;
}

QScrollBar::add-line, QScrollBar::sub-line {
    background-color: transparent;
    border: none;
}

/* 对话框 */
QDialog {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 3px;
}

/* 停靠窗口 */
QDockWidget {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
}

QDockWidget::title {
    background-color: #f5f5f5;
    border-bottom: 1px solid #e0e0e0;
    padding: 4px 8px;
}

/* 进度条 */
QProgressBar {
    background-color: #f5f5f5;
    border: 1px solid #e0e0e0;
    border-radius: 3px;
    text-align: center;
    padding: 2px;
}

QProgressBar::chunk {
    background-color: #2196F3;
    border-radius: 3px;
}

/* 文本编辑 */
QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 3px;
    padding: 8px;
}

QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #2196F3;
    outline: none;
}
"""

# 深色主题样式表
DARK_THEME = """
/* 全局样式 */
* {
    color: #e0e0e0;
    background-color: #2d2d2d;
}

/* 主窗口 */
QMainWindow {
    background-color: #2d2d2d;
}

/* 菜单栏 */
QMenuBar {
    background-color: #3d3d3d;
    border-bottom: 1px solid #1e1e1e;
}

QMenuBar::item {
    background-color: transparent;
    padding: 4px 8px;
}

QMenuBar::item:selected {
    background-color: #4d4d4d;
    border-radius: 3px;
}

QMenu {
    background-color: #3d3d3d;
    border: 1px solid #1e1e1e;
    border-radius: 3px;
    padding: 4px 0;
}

QMenu::item {
    background-color: transparent;
    padding: 4px 20px;
    min-width: 120px;
}

QMenu::item:selected {
    background-color: #4d4d4d;
}

/* 工具栏 */
QToolBar {
    background-color: #3d3d3d;
    border-bottom: 1px solid #1e1e1e;
    padding: 4px;
}

QToolBar QToolButton {
    background-color: #2d2d2d;
    border: 1px solid #1e1e1e;
    border-radius: 3px;
    padding: 4px;
    margin: 2px;
}

QToolBar QToolButton:hover {
    background-color: #4d4d4d;
}

QToolBar QToolButton:pressed {
    background-color: #5d5d5d;
}

/* 地址栏和导航按钮 */
QLineEdit {
    background-color: #3d3d3d;
    border: 1px solid #1e1e1e;
    border-radius: 3px;
    padding: 4px 8px;
}

QLineEdit:focus {
    border-color: #2196F3;
    outline: none;
}

QPushButton {
    background-color: #3d3d3d;
    border: 1px solid #1e1e1e;
    border-radius: 3px;
    padding: 4px 8px;
    min-width: 60px;
}

QPushButton:hover {
    background-color: #4d4d4d;
}

QPushButton:pressed {
    background-color: #5d5d5d;
}

QPushButton:disabled {
    background-color: #2d2d2d;
    color: #666666;
}

/* 文件列表 */
QListView, QTableView {
    background-color: #2d2d2d;
    border: 1px solid #1e1e1e;
    selection-background-color: #3d3d3d;
    selection-color: #e0e0e0;
}

QListView::item, QTableView::item {
    padding: 4px;
}

QListView::item:selected, QTableView::item:selected {
    background-color: #3d3d3d;
}

QTableView::header {
    background-color: #3d3d3d;
    border-bottom: 1px solid #1e1e1e;
}

QTableView::header::section {
    background-color: #3d3d3d;
    padding: 6px;
    border-right: 1px solid #1e1e1e;
}

/* 状态栏 */
QStatusBar {
    background-color: #3d3d3d;
    border-top: 1px solid #1e1e1e;
    color: #9e9e9e;
}

/* 分割器 */
QSplitter {
    background-color: #1e1e1e;
}

QSplitter::handle {
    background-color: #1e1e1e;
}

QSplitter::handle:hover {
    background-color: #0e0e0e;
}

/* 标签页 */
QTabWidget {
    background-color: #2d2d2d;
}

QTabBar {
    background-color: #2d2d2d;
    border-bottom: 1px solid #1e1e1e;
}

QTabBar::tab {
    background-color: #3d3d3d;
    border: 1px solid #1e1e1e;
    border-bottom: none;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
    padding: 6px 12px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #2d2d2d;
    border-color: #1e1e1e;
    border-bottom: 1px solid #2d2d2d;
}

/* 分组框 */
QGroupBox {
    background-color: #2d2d2d;
    border: 1px solid #1e1e1e;
    border-radius: 3px;
    padding: 8px;
    margin-top: 6px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    top: -8px;
    padding: 0 4px;
    background-color: #2d2d2d;
}

/* 下拉框 */
QComboBox {
    background-color: #3d3d3d;
    border: 1px solid #1e1e1e;
    border-radius: 3px;
    padding: 4px 8px;
    min-width: 100px;
}

QComboBox:hover {
    border-color: #4d4d4d;
}

QComboBox::drop-down {
    border: none;
    background-color: transparent;
}

QComboBox::down-arrow {
    image: url(:/icons/down_arrow_dark.png);
    width: 16px;
    height: 16px;
}

QComboBox QAbstractItemView {
    background-color: #3d3d3d;
    border: 1px solid #1e1e1e;
    border-radius: 3px;
    padding: 2px;
}

/* 复选框和单选按钮 */
QCheckBox, QRadioButton {
    background-color: transparent;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #1e1e1e;
    border-radius: 3px;
    background-color: #3d3d3d;
}

QCheckBox::indicator:checked {
    background-color: #2196F3;
    image: url(:/icons/checkmark_dark.png);
}

QRadioButton::indicator:checked {
    background-color: #2196F3;
    border-radius: 8px;
    image: url(:/icons/dot_dark.png);
}

/* 滚动条 */
QScrollBar:vertical {
    width: 12px;
    background-color: #3d3d3d;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #5d5d5d;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #6d6d6d;
}

QScrollBar:horizontal {
    height: 12px;
    background-color: #3d3d3d;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #5d5d5d;
    border-radius: 6px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #6d6d6d;
}

QScrollBar::add-line, QScrollBar::sub-line {
    background-color: transparent;
    border: none;
}

/* 对话框 */
QDialog {
    background-color: #2d2d2d;
    border: 1px solid #1e1e1e;
    border-radius: 3px;
}

/* 停靠窗口 */
QDockWidget {
    background-color: #2d2d2d;
    border: 1px solid #1e1e1e;
}

QDockWidget::title {
    background-color: #3d3d3d;
    border-bottom: 1px solid #1e1e1e;
    padding: 4px 8px;
}

/* 进度条 */
QProgressBar {
    background-color: #3d3d3d;
    border: 1px solid #1e1e1e;
    border-radius: 3px;
    text-align: center;
    padding: 2px;
}

QProgressBar::chunk {
    background-color: #2196F3;
    border-radius: 3px;
}

/* 文本编辑 */
QTextEdit, QPlainTextEdit {
    background-color: #3d3d3d;
    border: 1px solid #1e1e1e;
    border-radius: 3px;
    padding: 8px;
}

QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #2196F3;
    outline: none;
}

/* 文件列表视图 */
QTreeView, QListView {
    background-color: #2d2d2d;
    border: 1px solid #1e1e1e;
    color: #e0e0e0;
}

/* 文件列表标题栏 */
QHeaderView {
    background-color: #3d3d3d;
    border-bottom: 1px solid #1e1e1e;
    color: #e0e0e0;
}

QHeaderView::section {
    background-color: #3d3d3d;
    border: 1px solid #1e1e1e;
    padding: 4px 8px;
    color: #e0e0e0;
}

QHeaderView::section:horizontal {
    border-bottom: 1px solid #1e1e1e;
}

QHeaderView::section:vertical {
    border-right: 1px solid #1e1e1e;
}

/* 文件列表项 */
QTreeView::item {
    background-color: #2d2d2d;
    padding: 4px 8px;
    color: #e0e0e0;
}

QTreeView::item:alternate {
    background-color: #333333;
}

QTreeView::item:selected {
    background-color: #4d4d4d;
}

QTreeView::item:hover {
    background-color: #4d4d4d;
}

/* 列表视图项 */
QListView::item {
    background-color: #2d2d2d;
    color: #e0e0e0;
}

QListView::item:alternate {
    background-color: #333333;
}

QListView::item:selected {
    background-color: #4d4d4d;
}

QListView::item:hover {
    background-color: #4d4d4d;
}
"""
