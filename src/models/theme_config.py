from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional


class ThemeType(Enum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


@dataclass
class ColorConfig:
    background: str = "#FFFFFF"
    foreground: str = "#000000"
    accent: str = "#0078D4"
    secondary: str = "#F3F3F3"
    border: str = "#E5E5E5"
    selection: str = "#0078D4"
    hover: str = "#F5F5F5"
    text: str = "#000000"
    text_secondary: str = "#666666"
    success: str = "#107C10"
    warning: str = "#FFB900"
    error: str = "#D83B01"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'background': self.background,
            'foreground': self.foreground,
            'accent': self.accent,
            'secondary': self.secondary,
            'border': self.border,
            'selection': self.selection,
            'hover': self.hover,
            'text': self.text,
            'text_secondary': self.text_secondary,
            'success': self.success,
            'warning': self.warning,
            'error': self.error,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ColorConfig':
        return cls(
            background=data.get('background', '#FFFFFF'),
            foreground=data.get('foreground', '#000000'),
            accent=data.get('accent', '#0078D4'),
            secondary=data.get('secondary', '#F3F3F3'),
            border=data.get('border', '#E5E5E5'),
            selection=data.get('selection', '#0078D4'),
            hover=data.get('hover', '#F5F5F5'),
            text=data.get('text', '#000000'),
            text_secondary=data.get('text_secondary', '#666666'),
            success=data.get('success', '#107C10'),
            warning=data.get('warning', '#FFB900'),
            error=data.get('error', '#D83B01'),
        )


@dataclass
class FontConfig:
    family: str = "Segoe UI"
    size: int = 9
    weight: int = 400
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'family': self.family,
            'size': self.size,
            'weight': self.weight,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FontConfig':
        return cls(
            family=data.get('family', 'Segoe UI'),
            size=data.get('size', 9),
            weight=data.get('weight', 400),
        )


@dataclass
class AnimationConfig:
    enabled: bool = True
    duration: int = 300
    easing: str = "easeInOutCubic"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'enabled': self.enabled,
            'duration': self.duration,
            'easing': self.easing,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnimationConfig':
        return cls(
            enabled=data.get('enabled', True),
            duration=data.get('duration', 300),
            easing=data.get('easing', 'easeInOutCubic'),
        )


@dataclass
class ThemeConfig:
    theme_type: ThemeType = ThemeType.LIGHT
    colors: ColorConfig = field(default_factory=ColorConfig)
    fonts: FontConfig = field(default_factory=FontConfig)
    animations: AnimationConfig = field(default_factory=AnimationConfig)
    mica_enabled: bool = False
    corner_radius: int = 8
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'theme_type': self.theme_type.value,
            'colors': self.colors.to_dict(),
            'fonts': self.fonts.to_dict(),
            'animations': self.animations.to_dict(),
            'mica_enabled': self.mica_enabled,
            'corner_radius': self.corner_radius,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThemeConfig':
        return cls(
            theme_type=ThemeType(data.get('theme_type', 'light')),
            colors=ColorConfig.from_dict(data.get('colors', {})),
            fonts=FontConfig.from_dict(data.get('fonts', {})),
            animations=AnimationConfig.from_dict(data.get('animations', {})),
            mica_enabled=data.get('mica_enabled', False),
            corner_radius=data.get('corner_radius', 8),
        )
    
    @classmethod
    def create_light_theme(cls) -> 'ThemeConfig':
        return cls(
            theme_type=ThemeType.LIGHT,
            colors=ColorConfig(
                background="#FFFFFF",
                foreground="#000000",
                accent="#0078D4",
                secondary="#F3F3F3",
                border="#E5E5E5",
                selection="#0078D4",
                hover="#F5F5F5",
                text="#000000",
                text_secondary="#666666",
            ),
            mica_enabled=False,
        )
    
    @classmethod
    def create_dark_theme(cls) -> 'ThemeConfig':
        return cls(
            theme_type=ThemeType.DARK,
            colors=ColorConfig(
                background="#202020",
                foreground="#FFFFFF",
                accent="#60CDFF",
                secondary="#2D2D2D",
                border="#404040",
                selection="#60CDFF",
                hover="#383838",
                text="#FFFFFF",
                text_secondary="#B0B0B0",
            ),
            mica_enabled=True,
        )