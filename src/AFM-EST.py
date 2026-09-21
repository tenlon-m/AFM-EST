#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用程序入口
"""

import sys
import os
import warnings

# Add current directory and PyInstaller extracted directory to Python path
base_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(base_path)  # 项目根目录
sys.path.insert(0, base_path)
sys.path.insert(0, project_root)  # 添加项目根目录以访问config
sys.path.insert(0, os.getcwd())

# Handle PyInstaller temporary directory
if hasattr(sys, '_MEIPASS'):
    sys.path.insert(0, os.path.join(sys._MEIPASS, 'config'))  # pyright: ignore[reportAttributeAccessIssue]
    sys.path.insert(0, sys._MEIPASS)  # pyright: ignore[reportAttributeAccessIssue]

# 屏蔽第三方库的弃用警告
warnings.filterwarnings("ignore", category=DeprecationWarning)
try:
    from cryptography.utils import CryptographyDeprecationWarning
    warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)
except ImportError:
    pass


# 延迟导入非核心模块
from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtCore import Qt

# 现在可以使用绝对导入
from core.logger import logger

def show_splash_screen(app):
    """显示启动画面"""
    # 创建简单的启动画面
    splash_pixmap = QPixmap(300, 100)
    splash_pixmap.fill(QColor(30, 30, 30))
    
    splash = QSplashScreen(splash_pixmap, Qt.WindowStaysOnTopHint)  # pyright: ignore[reportAttributeAccessIssue]
    splash.showMessage(
        "AFM-EST 文件管理器\n正在加载...",
        Qt.AlignCenter | Qt.AlignBottom,  # pyright: ignore[reportAttributeAccessIssue]
        QColor(255, 255, 255)
    )
    splash.show()
    app.processEvents()
    
    return splash

def main():
    """
    应用程序主函数
    """
    try:
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        logger.info(f"=== AFM-EST 应用程序启动 ===")
        logger.info(f"当前时间: {current_time}")
        logger.info(f"当前工作目录: {os.getcwd()}")
        logger.info(f"Python路径: {sys.path}")
        logger.info(f"__file__: {__file__}")
        
        # 在Qt初始化前设置环境变量，禁用D3D11硬件加速，解决视频渲染错误
        if os.name == 'nt':
            # 禁用D3D11相关功能
            os.environ['QT_D3D_NO_SMOKE_TEST'] = '1'
            os.environ['QT_D3D11_NO_HARDWARE_LAYER'] = '1'
            os.environ['QT_D3D11_ENABLED'] = '0'  # 完全禁用D3D11
            os.environ['QT_OPENGL'] = 'software'  # 使用软件渲染
            os.environ['QT_QUICK_BACKEND'] = 'software'  # 使用软件后端
            
            # 禁用视频硬件加速
            os.environ['QT_AV_FOUNDATION_ENABLE_HW_DECODING'] = '0'
            
            # 调整FFmpeg日志级别，减少MP3警告
            os.environ['FFREPORT'] = 'file=-:level=32'  # 只记录错误
            os.environ['QT_MEDIA_LOG_LEVEL'] = '2'  # 只显示错误，不显示警告
            
            # 禁用不必要的警告
            os.environ['QT_LOGGING_RULES'] = 'qt.multimedia.*=false;*.warning=false'
        
        logger.info("AFM-EST 应用程序启动")
        
        # 创建应用程序实例
        app = QApplication(sys.argv)
        app.setApplicationName("AFM-EST")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("AFM-EST Team")
        
        # 设置应用程序图标
        from PySide6.QtGui import QIcon

        try:
            # 尝试不同的路径获取方式（跨平台兼容）
            icon_path = None

            # 方式1：PyInstaller 打包环境
            if hasattr(sys, '_MEIPASS'):
                icon_path = os.path.join(sys._MEIPASS, "resources", "wjssdb.ico")  # pyright: ignore[reportAttributeAccessIssue]

            # 方式2：开发环境 - 检查多种可能的图标格式
            if not icon_path or not os.path.exists(icon_path):
                possible_icons = ["wjssdb.ico", "wjssdb.png", "app.ico", "app.png"]
                for icon_name in possible_icons:
                    # 检查 resources/icons 目录
                    test_path = os.path.join(project_root, "resources", "icons", icon_name)
                    if os.path.exists(test_path):
                        icon_path = test_path
                        break

                    # 检查 resources 目录
                    test_path = os.path.join(project_root, "resources", icon_name)
                    if os.path.exists(test_path):
                        icon_path = test_path
                        break

            # 方式3：当前工作目录
            if not icon_path or not os.path.exists(icon_path):
                for icon_name in ["wjssdb.ico", "wjssdb.png"]:
                    test_path = os.path.join(os.getcwd(), "resources", "icons", icon_name)
                    if os.path.exists(test_path):
                        icon_path = test_path
                        break

                    test_path = os.path.join(os.getcwd(), "resources", icon_name)
                    if os.path.exists(test_path):
                        icon_path = test_path
                        break


            # 设置图标
            if icon_path and os.path.exists(icon_path):
                app.setWindowIcon(QIcon(icon_path))
                logger.info(f"已设置应用程序图标: {icon_path}")
            else:
                logger.warning("未找到应用程序图标，使用默认图标")

        except Exception as e:
            logger.exception(f"设置图标时出错: {e}")
            import traceback
            traceback.print_exc()

        
        # 显示启动画面
        splash = show_splash_screen(app)
        
        # 延迟导入MainWindow以提升启动速度
        splash.showMessage("正在加载主窗口...", Qt.AlignCenter | Qt.AlignBottom, QColor(255, 255, 255))  # pyright: ignore[reportAttributeAccessIssue]
        app.processEvents()
        
        try:
            from ui.main_window import MainWindow
        except Exception as e:
            logger.exception(f"导入MainWindow时出错: {e}")
            raise
        
        # 创建主窗口
        splash.showMessage("正在初始化...\n这可能需要几秒钟", Qt.AlignCenter | Qt.AlignBottom, QColor(255, 255, 255))  # pyright: ignore[reportAttributeAccessIssue]
        app.processEvents()
        
        # 使用定时器确保启动画面更新
        from PySide6.QtCore import QTimer
        init_timer = QTimer()
        init_timer.setSingleShot(True)
        
        window = None
        error_occurred = False
        
        def create_window():
            nonlocal window, error_occurred
            try:
                window = MainWindow()
                # 关闭启动画面
                splash.finish(window)
                # 显示主窗口
                window.show()
                
                # 在启动画面关闭后检查并提示构建索引
                QTimer.singleShot(500, check_and_prompt_index)
            except Exception as e:
                error_occurred = True
                logger.exception(f"创建MainWindow失败: {e}")
                splash.close()
                import traceback
                traceback.print_exc()
        
        def check_and_prompt_index():
            """检查并提示构建索引（确保启动画面已关闭）"""
            try:
                if window and hasattr(window, 'dual_pane') and hasattr(window.dual_pane, 'function_panel'):
                    window.dual_pane.function_panel._check_and_prompt_index()
                else:
                    logger.error("[UI] 无法访问功能面板")
            except Exception as e:
                logger.error(f"[UI] 检查索引状态失败: {e}")
        
        # 同步创建窗口（因为Qt要求在主线程）
        create_window()
        
        if error_occurred or window is None:
            logger.error("应用程序启动失败")
            return
        
        # 运行应用程序
        logger.info("AFM-EST 应用程序已启动，进入主事件循环")
        try:
            sys.exit(app.exec())
        except KeyboardInterrupt:
            # 捕获Ctrl+C中断，正常退出
            logger.info("应用程序被用户中断")
            sys.exit(0)
        
    except Exception as e:
        logger.exception(f"应用程序启动失败: {e}")
        logger.crash_report()
        
        sys.exit(1)
    finally:
        logger.info("AFM-EST 应用程序已退出")

if __name__ == "__main__":
    main()
logger.info("正在启动应用程序...")