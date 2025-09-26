"""GUI 主题与样式抽离模块.
重设计版：降低色彩噪音，集中主色 (PRIMARY) + 语义色，其他通过层次/留白表达。

结构:
 - Colors: 基础与语义调色板 + 中性色阶
 - Fonts: 字体层级
 - Spacing / Radii / Elevation: 设计 tokens
 - Style: 组件样式原子
 - Utilities: ensure_contrast / blend / darken 等
"""
from __future__ import annotations
from typing import Dict, Any

class Colors:
    """Modernized Inspa Theme.
    A cleaner, more professional take on the cyberpunk aesthetic.
    Focuses on clarity, spacing, and a primary accent color.
    """
    # Background layers: Softer than pure black
    BACKGROUND = "#17181a"      # Very dark, slightly cool gray
    SURFACE = "#1f2023"         # Main component background
    SURFACE_LIGHT = "#292b2e"    # Lighter layer for cards/sections
    SURFACE_HOVER = "#34363a"    # Hover state for surfaces
    LIST_BG = "#1a1b1d"
    LIST_ALT = "#222326"

    # Primary accent color (a slightly desaturated, modern yellow)
    PRIMARY = "#F0C419"
    PRIMARY_LIGHT = "#F3D04A"
    PRIMARY_DARK = "#D4AD16"
    ACCENT = "#E54B64"           # A modern, soft red for secondary actions
    ACCENT_ALT = "#EC6F83"

    # Semantic colors
    SUCCESS = "#28a745"
    WARNING = "#ffc107"
    ERROR = "#dc3545"
    INFO = "#17a2b8"

    # Borders and dividers
    BORDER = "#3a3c40"
    BORDER_LIGHT = "#4a4d52"
    BORDER_GLOW = PRIMARY

    # Text colors
    TEXT_PRIMARY = "#EAEAEA"
    TEXT_SECONDARY = "#B0B0B0"
    TEXT_MUTED = "#7A7A7A"
    TEXT_LIGHT = "#FFFFFF"

    # Neutral colors for buttons, etc.
    NEUTRAL = "#343a40"
    NEUTRAL_HOVER = "#495057"

    # Glow colors (used sparingly)
    GLOW_CYAN = INFO
    GLOW_PINK = ACCENT
    GLOW_GREEN = SUCCESS
    GLOW_GOLD = PRIMARY


class Fonts:
    FAMILY = "Segoe UI"
    TITLE = (FAMILY, 24, "bold")
    H1 = (FAMILY, 20, "bold")
    H2 = (FAMILY, 16, "bold")
    H3 = (FAMILY, 14, "bold")
    BODY = (FAMILY, 13)
    SMALL = (FAMILY, 12)
    MONO_SMALL = ("Consolas", 12)

class Style:
    # Navigation button style
    BUTTON_NAV: Dict[str, Any] = dict(
        fg_color="transparent",
        hover_color=Colors.SURFACE_HOVER,
        text_color=Colors.TEXT_SECONDARY,
        corner_radius=8,
        font=("Segoe UI", 13, "bold"),
        anchor="w"
    )

    # Primary button: bold, clear, and inviting
    BUTTON_PRIMARY: Dict[str, Any] = dict(
        fg_color=Colors.PRIMARY,
        hover_color=Colors.PRIMARY_LIGHT,
        text_color="#1A1A1A",
        corner_radius=12,
        font=("Segoe UI", 14, "bold")
    )
    # Outline button: for secondary actions that need emphasis
    BUTTON_OUTLINE: Dict[str, Any] = dict(
        fg_color="transparent",
        hover_color=Colors.NEUTRAL_HOVER,
        text_color=Colors.PRIMARY,
        border_color=Colors.PRIMARY,
        border_width=2,
        corner_radius=12,
        font=("Segoe UI", 13, "bold")
    )
    # Secondary button: for less critical actions
    BUTTON_SECONDARY: Dict[str, Any] = dict(
        fg_color=Colors.NEUTRAL,
        hover_color=Colors.NEUTRAL_HOVER,
        text_color=Colors.TEXT_SECONDARY,
        corner_radius=10,
        font=("Segoe UI", 13)
    )
    # Accent button: for actions like "add" or "new"
    BUTTON_ACCENT: Dict[str, Any] = dict(
        fg_color=Colors.ACCENT,
        hover_color=Colors.ACCENT_ALT,
        text_color=Colors.TEXT_LIGHT,
        corner_radius=10,
        font=("Segoe UI", 13, "bold")
    )
    BUTTON_DANGER: Dict[str, Any] = dict(
        fg_color=Colors.ERROR,
        hover_color="#E55061",
        text_color=Colors.TEXT_LIGHT,
        corner_radius=10,
        font=("Segoe UI", 13, "bold")
    )
    # Silver/light gray button, now more of a general-purpose light button
    BUTTON_SILVER: Dict[str, Any] = dict(
        fg_color=Colors.SURFACE_LIGHT,
        hover_color=Colors.NEUTRAL,
        text_color=Colors.TEXT_PRIMARY,
        corner_radius=10,
        font=("Segoe UI", 13),
        border_width=1,
        border_color=Colors.BORDER
    )
    # Entry style: clean, modern, with clear focus state
    ENTRY: Dict[str, Any] = dict(
        fg_color=Colors.SURFACE,
        text_color=Colors.TEXT_PRIMARY,
        placeholder_text_color=Colors.TEXT_MUTED,
        border_color=Colors.BORDER,
        border_width=2,
        corner_radius=10,
        font=Fonts.BODY
    )

    TEXTBOX: Dict[str, Any] = dict(
        fg_color=Colors.SURFACE,
        text_color=Colors.TEXT_PRIMARY,
        border_color=Colors.BORDER,
        border_width=2,
        corner_radius=10,
        font=Fonts.BODY
    )

    SLIDER: Dict[str, Any] = dict(
        button_color=Colors.PRIMARY,
        button_hover_color=Colors.PRIMARY_LIGHT,
        progress_color=Colors.SURFACE_LIGHT,
    )

    LABEL: Dict[str, Any] = dict(
        font=Fonts.BODY,
        text_color=Colors.TEXT_SECONDARY
    )

    # Ghost button: for subtle, non-critical actions
    BUTTON_GHOST: Dict[str, Any] = dict(
        fg_color="transparent",
        hover_color=Colors.SURFACE_HOVER,
        text_color=Colors.TEXT_SECONDARY,
        corner_radius=8,
        font=Fonts.SMALL
    )

    # Semantic glow styles (for build status, etc.)
    GLOW_SUCCESS: Dict[str, Any] = dict(
        glow_color=Colors.SUCCESS,
        border_color=Colors.SUCCESS,
        fg_color=Colors.SUCCESS,
        hover_color="#218838",
        text_color=Colors.TEXT_LIGHT
    )
    GLOW_ERROR: Dict[str, Any] = dict(
        glow_color=Colors.ERROR,
        border_color=Colors.ERROR,
        fg_color=Colors.ERROR,
        hover_color="#C82333",
        text_color=Colors.TEXT_LIGHT
    )
    GLOW_WARNING: Dict[str, Any] = dict(
        glow_color=Colors.WARNING,
        border_color=Colors.WARNING,
        fg_color=Colors.WARNING,
        hover_color="#E0A800",
        text_color="#1A1A1A"
    )
    GLOW_INFO: Dict[str, Any] = dict(
        glow_color=Colors.INFO,
        border_color=Colors.INFO,
        fg_color=Colors.INFO,
        hover_color="#138496",
        text_color=Colors.TEXT_LIGHT
    )

# ====== 设计 Tokens ======
class Spacing:
    XS = 4
    S = 8
    M = 12
    L = 16
    XL = 24

class Radii:
    XS = 4
    S = 6
    M = 8
    L = 12
    XL = 16

class Elevation:
    # 仅逻辑层级 (GUI 不直接生成阴影，可用于后续自定义)
    LEVEL0 = 0  # 背景 / 根
    LEVEL1 = 1  # Section
    LEVEL2 = 2  # 浮层 / Dialog

# ====== Utilities ======
def _linear_channel(c: float) -> float:
    return c/12.92 if c <= 0.03928 else ((c+0.055)/1.055) ** 2.4

def relative_luminance(hex_color: str) -> float:
    h = hex_color.lstrip('#')
    r = int(h[0:2],16)/255
    g = int(h[2:4],16)/255
    b = int(h[4:6],16)/255
    lr, lg, lb = _linear_channel(r), _linear_channel(g), _linear_channel(b)
    return 0.2126*lr + 0.7152*lg + 0.0722*lb

def contrast_ratio(fg: str, bg: str) -> float:
    l1, l2 = relative_luminance(fg), relative_luminance(bg)
    high, low = (l1, l2) if l1 > l2 else (l2, l1)
    return (high + 0.05) / (low + 0.05)

def ensure_contrast(bg: str, light: str = Colors.TEXT_LIGHT, dark: str = '#1A1A1A', threshold: float = 4.0) -> str:
    """返回在给定背景上可读性更好的文本颜色.
    优先使用深色（暗底白字 / 亮底深字)；对比不足时自动调整。
    """
    try:
        # 判断背景亮度
        lum = relative_luminance(bg)
        preferred = dark if lum > 0.6 else light
        # 与背景对比度不足时反转
        if contrast_ratio(preferred, bg) < threshold:
            alt = light if preferred == dark else dark
            if contrast_ratio(alt, bg) > contrast_ratio(preferred, bg):
                return alt
        return preferred
    except Exception:
        return light

def darken(hex_color: str, factor: float = 0.8) -> str:
    try:
        h = hex_color.lstrip('#')
        r = int(h[0:2],16)
        g = int(h[2:4],16)
        b = int(h[4:6],16)
        r = int(r*factor)
        g = int(g*factor)
        b = int(b*factor)
        return f"#{r:02X}{g:02X}{b:02X}"
    except Exception:
        return hex_color

def blend(a: str, b: str, t: float = 0.5) -> str:
    try:
        a1 = a.lstrip('#'); b1 = b.lstrip('#')
        ar,ag,ab = int(a1[0:2],16), int(a1[2:4],16), int(a1[4:6],16)
        br,bg,bb = int(b1[0:2],16), int(b1[2:4],16), int(b1[4:6],16)
        r = int(ar + (br-ar)*t)
        g = int(ag + (bg-ag)*t)
        b_ = int(ab + (bb-ab)*t)
        return f"#{r:02X}{g:02X}{b_:02X}"
    except Exception:
        return a
