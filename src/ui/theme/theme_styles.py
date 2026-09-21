
from models.theme_config import ThemeConfig, ThemeType


def get_light_theme_styles(theme_config: ThemeConfig) -> str:
    colors = theme_config.colors
    fonts = theme_config.fonts
    radius = theme_config.corner_radius
    
    return f"""
        QWidget {{
            background-color: {colors.background};
            color: {colors.text};
            font-family: "{fonts.family}";
            font-size: {fonts.size}pt;
        }}
        
        QListView {{
            background-color: {colors.background};
            border: 1px solid {colors.border};
            border-radius: {radius}px;
            outline: none;
        }}
        
        QListView::item {{
            background-color: transparent;
            border: none;
            padding: 4px;
            border-radius: {radius}px;
        }}
        
        QListView::item:hover {{
            background-color: {colors.hover};
        }}
        
        QListView::item:selected {{
            background-color: {colors.selection};
            color: white;
        }}
        
        QTreeView {{
            background-color: {colors.background};
            border: 1px solid {colors.border};
            border-radius: {radius}px;
            outline: none;
        }}
        
        QTreeView::item {{
            background-color: transparent;
            border: none;
            padding: 4px;
            border-radius: {radius}px;
        }}
        
        QTreeView::item:hover {{
            background-color: {colors.hover};
        }}
        
        QTreeView::item:selected {{
            background-color: {colors.selection};
            color: white;
        }}
        
        QHeaderView::section {{
            background-color: {colors.secondary};
            border: none;
            border-bottom: 1px solid {colors.border};
            padding: 6px;
            font-weight: bold;
        }}
        
        QScrollBar:vertical {{
            background-color: {colors.secondary};
            width: 10px;
            border-radius: 5px;
            margin: 2px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {colors.border};
            border-radius: 5px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {colors.text_secondary};
        }}
        
        QScrollBar:horizontal {{
            background-color: {colors.secondary};
            height: 10px;
            border-radius: 5px;
            margin: 2px;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {colors.border};
            border-radius: 5px;
            min-width: 20px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {colors.text_secondary};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            background: none;
            border: none;
        }}
    """


def get_dark_theme_styles(theme_config: ThemeConfig) -> str:
    colors = theme_config.colors
    fonts = theme_config.fonts
    radius = theme_config.corner_radius
    
    return f"""
        QWidget {{
            background-color: {colors.background};
            color: {colors.text};
            font-family: "{fonts.family}";
            font-size: {fonts.size}pt;
        }}
        
        QListView {{
            background-color: {colors.background};
            border: 1px solid {colors.border};
            border-radius: {radius}px;
            outline: none;
        }}
        
        QListView::item {{
            background-color: transparent;
            border: none;
            padding: 4px;
            border-radius: {radius}px;
        }}
        
        QListView::item:hover {{
            background-color: {colors.hover};
        }}
        
        QListView::item:selected {{
            background-color: {colors.selection};
            color: {colors.background};
        }}
        
        QTreeView {{
            background-color: {colors.background};
            border: 1px solid {colors.border};
            border-radius: {radius}px;
            outline: none;
        }}
        
        QTreeView::item {{
            background-color: transparent;
            border: none;
            padding: 4px;
            border-radius: {radius}px;
        }}
        
        QTreeView::item:hover {{
            background-color: {colors.hover};
        }}
        
        QTreeView::item:selected {{
            background-color: {colors.selection};
            color: {colors.background};
        }}
        
        QHeaderView::section {{
            background-color: {colors.secondary};
            border: none;
            border-bottom: 1px solid {colors.border};
            padding: 6px;
            font-weight: bold;
        }}
        
        QScrollBar:vertical {{
            background-color: {colors.secondary};
            width: 10px;
            border-radius: 5px;
            margin: 2px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {colors.border};
            border-radius: 5px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {colors.text_secondary};
        }}
        
        QScrollBar:horizontal {{
            background-color: {colors.secondary};
            height: 10px;
            border-radius: 5px;
            margin: 2px;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {colors.border};
            border-radius: 5px;
            min-width: 20px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {colors.text_secondary};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            background: none;
            border: none;
        }}
    """


def generate_stylesheet(theme_config: ThemeConfig) -> str:
    if theme_config.theme_type == ThemeType.DARK:
        return get_dark_theme_styles(theme_config)
    else:
        return get_light_theme_styles(theme_config)