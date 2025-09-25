"""
现代化 Inspa 构建器 GUI

采用 Liquid Glass 设计语言的现代化构建器界面
设计理念：简洁、直观、功能性强
映射需求：NFR-UI-001, NFR-UI-002, NFR-UI-003, FR-GUI-001, FR-GUI-003
"""

import os
import sys
import threading
import json
import queue
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List

try:
    import customtkinter as ctk
    from tkinter import filedialog, messagebox
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    ctk = None
    filedialog = None
    messagebox = None
    print("警告: GUI 依赖未安装，GUI 功能不可用")

# 导入配置和构建器
if GUI_AVAILABLE:
    try:
        from inspa.config.schema import InspaConfig, ProductModel, InstallModel, CompressionAlgorithm
        from inspa.config.loader import load_config
        from inspa.build.builder import Builder as InspaBuilder
        CORE_MODULES_AVAILABLE = True
    except ImportError as e:
        print(f"警告: 无法导入 Inspa 核心模块: {e}")
        # 尝试相对导入
        try:
            from ..config.schema import InspaConfig, ProductModel, InstallModel, CompressionAlgorithm
            from ..config.loader import load_config
            from ..build.builder import Builder as InspaBuilder
            CORE_MODULES_AVAILABLE = True
        except ImportError as e2:
            print(f"警告: 相对导入也失败: {e2}")
            CORE_MODULES_AVAILABLE = False
            # 定义存根类以避免运行时错误
            class InspaConfig: pass
            class ProductModel: pass
            class InstallModel: pass
            class CompressionAlgorithm: pass
            def load_config(path): raise NotImplementedError("核心模块未可用")
            class InspaBuilder: pass
else:
    CORE_MODULES_AVAILABLE = False


# 仅在GUI可用时定义GUI类
if GUI_AVAILABLE:
    
    # 设置 CustomTkinter 主题和外观 (固定暗色)
    ctk.set_appearance_mode("dark")

    # === 赛博朋克主题常量定义 ===
    class Colors:
        BACKGROUND = "#0A0B11"   # 更深的暗夜黑（赛博朋克2077风格）
        SURFACE = "#0F1419"      # 深钢蓝黑
        SURFACE_LIGHT = "#1A1F2E"
        CARD = "#151A26"
        BORDER = "#1F2937"
        BORDER_LIGHT = "#374151"
        LIST_BG = "#0D1117"      # 列表背景（深黑）
        LIST_ALT = "#161B22"     # 交替行
        PRIMARY = "#00D4FF"       # 赛博电青
        PRIMARY_LIGHT = "#4DD0E1"
        PRIMARY_DARK = "#00ACC1"
        ACCENT = "#FF0080"        # 霓虹粉（经典赛博粉）
        ACCENT_ALT = "#8E44AD"    # 暗紫（更深沉）
        ORANGE = "#FF6B35"        # 赛博橙红
        ORANGE_LIGHT = "#FF8A65"
        ORANGE_DARK = "#E64A19"
        SUCCESS = "#00FF88"       # 荧光绿（更鲜艳）
        WARNING = "#FFD700"       # 金黄
        ERROR = "#FF1744"         # 赛博红
        INFO = "#00BCD4"          # 信息青
        NEUTRAL = "#263238"       # 中性钢灰
        NEUTRAL_HOVER = "#37474F"
        TEXT_PRIMARY = "#F0F4F8"     # 冷白
        TEXT_SECONDARY = "#B0BEC5"   # 钢青灰
        TEXT_MUTED = "#78909C"       # 暗青灰
        TEXT_LIGHT = "#FFFFFF"
        # 高能饱和色（用于“激情四射”动画模式）
        HYPER_CYAN = "#00FFFF"
        HYPER_PINK = "#FF00FF"
        HYPER_VIOLET = "#BB86FC"
        HYPER_LIME = "#76FF03"
        HYPER_GOLD = "#FFC107"
        HYPER_ORANGE = "#FF5722"
        HYPER_RED = "#F44336"
        # 彩虹调色板（循环渐变路径）
        RAINBOW_PALETTE = [
            HYPER_CYAN,      # 青色
            PRIMARY,         # 电青
            "#2196F3",       # 蓝色
            "#3F51B5",       # 靛青
            HYPER_VIOLET,    # 紫色
            HYPER_PINK,      # 粉红
            ACCENT,          # 霓虹粉
            HYPER_RED,       # 红色
            ERROR,           # 赛博红
            HYPER_ORANGE,    # 橙色
            ORANGE,          # 赛博橙红
            HYPER_GOLD,      # 金色
            WARNING,         # 金黄
            HYPER_LIME,      # 柠檬绿
            SUCCESS,         # 荧光绿
            HYPER_CYAN       # 回到起点形成循环
        ]
        
        # 视觉效果增强色 (使用6位十六进制)
        GLOW_CYAN = "#00B4D8"        # 青色发光
        GLOW_PINK = "#FF0066"        # 粉色发光
        GLOW_GREEN = "#00CC66"       # 绿色发光
        GLOW_GOLD = "#FFB000"        # 金色发光
        
        # 渐变背景色
        GRADIENT_START = "#0A0B11"
        GRADIENT_MID = "#0F1419"
        GRADIENT_END = "#1A1F2E"
        
        # 悬停效果色
        SURFACE_HOVER = "#242B3D"
        CARD_HOVER = "#1C2332"
        BORDER_GLOW = "#00B4D8"

    class Fonts:
        TITLE = ("Segoe UI", 26, "bold")
        H1 = ("Segoe UI", 20, "bold")
        H2 = ("Segoe UI", 18, "bold")
        BODY = ("Segoe UI", 13)
        SMALL = ("Segoe UI", 11)
        MONO_SMALL = ("Consolas", 11)

    class Style:
        BUTTON_PRIMARY = dict(
            fg_color=Colors.ORANGE,
            hover_color=Colors.ORANGE_DARK,
            text_color=Colors.TEXT_LIGHT,
            corner_radius=10,
            font=("Segoe UI", 13, "bold")
        )
        BUTTON_OUTLINE = dict(
            fg_color="transparent",
            hover_color=Colors.NEUTRAL_HOVER,
            text_color=Colors.PRIMARY,
            border_color=Colors.BORDER_LIGHT,
            border_width=1,
            corner_radius=8,
            font=("Segoe UI", 12)
        )
        BUTTON_SECONDARY = dict(
            fg_color=Colors.NEUTRAL,
            hover_color=Colors.NEUTRAL_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            corner_radius=8,
            font=("Segoe UI", 12)
        )
        BUTTON_ACCENT = dict(
            fg_color=Colors.ACCENT,
            hover_color="#E020C9",
            text_color=Colors.TEXT_LIGHT,
            corner_radius=8,
            font=("Segoe UI", 12, "bold")
        )
        BUTTON_ACCENT_ALT = dict(
            fg_color=Colors.ACCENT_ALT,
            hover_color="#7446E6",
            text_color=Colors.TEXT_LIGHT,
            corner_radius=8,
            font=("Segoe UI", 12, "bold")
        )
        BUTTON_DANGER = dict(
            fg_color=Colors.ERROR,
            hover_color="#D62845",
            text_color=Colors.TEXT_LIGHT,
            corner_radius=8,
            font=("Segoe UI", 12, "bold")
        )
        ENTRY = dict(
            fg_color=Colors.SURFACE_LIGHT,
            text_color=Colors.TEXT_PRIMARY,
            placeholder_text_color=Colors.TEXT_MUTED,
            border_color=Colors.BORDER_LIGHT,
            border_width=1,
            corner_radius=8
        )

        @classmethod
        def refresh(cls):
            # 预留：若后续需要动态刷新可在此集中处理
            pass

    Style.refresh()

    class Layout:
        """布局间距常量，统一管理。"""
        P_SECTION_Y = 14
        P_SECTION_X = 20
        P_FIELD_Y = 6
        P_FIELD_TITLE_BOTTOM = 8
        P_GROUP_GAP = 14
        P_BUILD_BOTTOM = 18
        P_BUTTON_INLINE_X = 8
        P_INNER = 20
    
    
    class HelpButton(ctk.CTkButton):
        """帮助按钮组件 - 更小更精致"""
        
        def __init__(self, parent, help_text: str, **kwargs):
            kwargs.update({
                'text': '?',
                'width': 20,
                'height': 20,
                'corner_radius': 10,
                'font': ('', 10),
                'fg_color': 'transparent',
                'hover_color': Colors.SURFACE_LIGHT,
                'text_color': Colors.TEXT_MUTED,
                'border_width': 1,
                'border_color': Colors.BORDER_LIGHT,
                'command': lambda: self.show_help()
            })
            super().__init__(parent, **kwargs)
            self.help_text = help_text
        
        def show_help(self):
            """显示帮助信息"""
            messagebox.showinfo("帮助", self.help_text)
    
    
    class LiquidFrame(ctk.CTkFrame):
        """新配色风格的框架组件 - 增强版"""
        
        def __init__(self, parent, **kwargs):
            enhanced_kwargs = {
                'corner_radius': 12,
                'fg_color': Colors.CARD,
                'border_width': 1,
                'border_color': Colors.BORDER
            }
            enhanced_kwargs.update(kwargs)
            super().__init__(parent, **enhanced_kwargs)
            
            # 添加悬停效果
            self.bind("<Enter>", self._on_enter)
            self.bind("<Leave>", self._on_leave)
            self._original_fg_color = enhanced_kwargs.get('fg_color', Colors.CARD)
            
        def _on_enter(self, event):
            """鼠标悬停时的微妙效果"""
            self.configure(
                fg_color=Colors.CARD_HOVER,
                border_color=Colors.BORDER_GLOW
            )
            
        def _on_leave(self, event):
            """鼠标离开时恢复"""
            self.configure(
                fg_color=self._original_fg_color,
                border_color=Colors.BORDER
            )

    class NeonSectionFrame(LiquidFrame):
        """带左侧霓虹竖条的 Section 容器（颜色由全局统一控制）- 增强版"""
        def __init__(self, parent, **kwargs):
            super().__init__(parent, **kwargs)
            
            # 创建发光霓虹条
            self.neon_bar = ctk.CTkFrame(
                self, 
                width=5, 
                fg_color=Colors.PRIMARY, 
                corner_radius=3
            )
            self.neon_bar.pack(side='left', fill='y', padx=(0, 2))
            
            self.inner = ctk.CTkFrame(self, fg_color='transparent')
            self.inner.pack(side='left', fill='both', expand=True)
            self.content = ctk.CTkFrame(self.inner, fg_color='transparent')
            self.content.pack(fill='both', expand=True)
            
            # 发光动画状态
            self._glow_intensity = 0.5
            self._glow_direction = 1
            
        def set_glow_color(self, color: str):
            """设置发光颜色并启动微动画"""
            try:
                # 使用基础颜色，避免透明度
                self.configure(border_color=color)
                self.neon_bar.configure(fg_color=color)
                
                # 启动微妙的发光脉冲
                self._start_glow_pulse(color)
            except Exception:
                pass
                
        def _start_glow_pulse(self, base_color):
            """启动微妙的发光脉冲效果"""
            def pulse():
                try:
                    # 计算发光强度
                    self._glow_intensity += self._glow_direction * 0.1
                    if self._glow_intensity >= 1.0:
                        self._glow_intensity = 1.0
                        self._glow_direction = -1
                    elif self._glow_intensity <= 0.3:
                        self._glow_intensity = 0.3
                        self._glow_direction = 1
                    
                    # 应用发光效果（微妙的宽度变化）
                    new_width = int(4 + 2 * self._glow_intensity)
                    self.neon_bar.configure(width=new_width)
                    
                    # 继续动画
                    self.after(3000, pulse)  # 慢速脉冲
                except Exception:
                    pass
            
            pulse()
    
    class EnhancedButton(ctk.CTkButton):
        """增强的按钮组件 - 带悬停动画和发光效果"""
        
        def __init__(self, parent, glow_color=None, **kwargs):
            # 默认的现代化按钮样式
            enhanced_kwargs = {
                'corner_radius': 12,
                'border_width': 1,
                'border_color': Colors.BORDER_LIGHT,
                'font': Fonts.BODY,
                'text_color': Colors.TEXT_PRIMARY,
                'fg_color': Colors.SURFACE_LIGHT,
                'hover_color': Colors.SURFACE_HOVER
            }
            enhanced_kwargs.update(kwargs)
            super().__init__(parent, **enhanced_kwargs)
            
            # 发光颜色
            self.glow_color = glow_color or Colors.GLOW_CYAN
            self._original_border_color = enhanced_kwargs.get('border_color', Colors.BORDER_LIGHT)
            self._is_hovering = False
            
            # 绑定悬停事件
            self.bind("<Enter>", self._on_enter)
            self.bind("<Leave>", self._on_leave)
            
        def _on_enter(self, event):
            """悬停时的发光效果"""
            self._is_hovering = True
            self.configure(
                border_color=self.glow_color,
                border_width=2
            )
            # 启动发光动画
            self._start_hover_glow()
            
        def _on_leave(self, event):
            """离开时恢复"""
            self._is_hovering = False
            self.configure(
                border_color=self._original_border_color,
                border_width=1
            )
            
        def _start_hover_glow(self):
            """启动悬停发光动画"""
            base_intensity = 0.6
            
            def glow_pulse():
                if not self._is_hovering:
                    return
                    
                # 简化发光效果，使用基础颜色
                try:
                    self.configure(border_color=self.glow_color)
                except:
                    pass
                
                if self._is_hovering:
                    self.after(200, glow_pulse)
            
            glow_pulse()

    class GlowButton(EnhancedButton):
        """超炫发光按钮 - 用于重要操作"""
        
        def __init__(self, parent, **kwargs):
            # 更炫酷的默认样式
            super_kwargs = {
                'corner_radius': 15,
                'border_width': 2,
                'border_color': Colors.PRIMARY,
                'font': ("Segoe UI", 14, "bold"),
                'text_color': Colors.TEXT_LIGHT,
                'fg_color': Colors.PRIMARY,
                'hover_color': Colors.PRIMARY_LIGHT,
                'glow_color': Colors.GLOW_CYAN
            }
            super_kwargs.update(kwargs)
            super().__init__(parent, **super_kwargs)
            
            # 启动持续发光效果
            self._start_continuous_glow()
            
        def _start_continuous_glow(self):
            """启动持续的微妙发光效果"""            
            def continuous_glow():
                # 简化持续发光，使用基础颜色闪烁
                try:
                    if not self._is_hovering:  # 只在非悬停时应用持续发光
                        current_color = self.cget('border_color')
                        if current_color == self.glow_color:
                            self.configure(border_color=Colors.BORDER_LIGHT)
                        else:
                            self.configure(border_color=self.glow_color)
                except:
                    pass
                
                self.after(2000, continuous_glow)  # 慢速闪烁
            
            continuous_glow()
    
    class GlowFrame(ctk.CTkFrame):
        """发光效果框架组件"""
        
        def __init__(self, parent, glow_color=Colors.GLOW_CYAN, **kwargs):
            enhanced_kwargs = {
                'corner_radius': 20,
                'fg_color': Colors.SURFACE_LIGHT,
                'border_width': 2,
                'border_color': glow_color
            }
            enhanced_kwargs.update(kwargs)
            super().__init__(parent, **enhanced_kwargs)
            self.glow_color = glow_color
            
            # 启动发光动画
            self._glow_intensity = 0.5
            self._glow_direction = 1
            self._start_glow_animation()
            
        def _start_glow_animation(self):
            """启动微妙的发光动画"""
            def animate():
                self._glow_intensity += self._glow_direction * 0.08
                if self._glow_intensity >= 1.0:
                    self._glow_intensity = 1.0
                    self._glow_direction = -1
                elif self._glow_intensity <= 0.2:
                    self._glow_intensity = 0.2
                    self._glow_direction = 1
                
                # 简化发光效果，不使用透明度
                try:
                    if self._glow_intensity > 0.6:
                        self.configure(border_color=self.glow_color)
                    else:
                        self.configure(border_color=Colors.BORDER_LIGHT)
                except:
                    pass
                
                self.after(2500, animate)  # 慢速发光动画
            
            animate()
    
    class EnhancedEntry(ctk.CTkEntry):
        """增强的输入框组件 - 带聚焦动画和发光效果"""
        
        def __init__(self, parent, **kwargs):
            # 默认的现代化输入框样式
            enhanced_kwargs = {
                'corner_radius': 10,
                'border_width': 1,
                'border_color': Colors.BORDER_LIGHT,
                'fg_color': Colors.SURFACE,
                'text_color': Colors.TEXT_PRIMARY,
                'placeholder_text_color': Colors.TEXT_MUTED,
                'font': Fonts.BODY
            }
            enhanced_kwargs.update(kwargs)
            super().__init__(parent, **enhanced_kwargs)
            
            # 动画状态
            self._original_border_color = enhanced_kwargs.get('border_color', Colors.BORDER_LIGHT)
            self._is_focused = False
            
            # 绑定事件
            self.bind("<FocusIn>", self._on_focus_in)
            self.bind("<FocusOut>", self._on_focus_out)
            self.bind("<Enter>", self._on_enter)
            self.bind("<Leave>", self._on_leave)
            
        def _on_focus_in(self, event):
            """聚焦时的发光效果"""
            self._is_focused = True
            self.configure(
                border_color=Colors.PRIMARY,
                border_width=2,
                fg_color=Colors.SURFACE_HOVER
            )
            self._start_focus_glow()
            
        def _on_focus_out(self, event):
            """失去焦点时恢复"""
            self._is_focused = False
            self.configure(
                border_color=self._original_border_color,
                border_width=1,
                fg_color=Colors.SURFACE
            )
            
        def _on_enter(self, event):
            """鼠标悬停时的微妙效果"""
            if not self._is_focused:
                self.configure(
                    border_color=Colors.BORDER_GLOW,
                    fg_color=Colors.SURFACE_HOVER
                )
                
        def _on_leave(self, event):
            """鼠标离开时恢复（如果未聚焦）"""
            if not self._is_focused:
                self.configure(
                    border_color=self._original_border_color,
                    fg_color=Colors.SURFACE
                )
                
        def _start_focus_glow(self):
            """启动聚焦发光动画"""
            intensity = 0.5
            direction = 1
            
            def glow_animation():
                if not self._is_focused:
                    return
                    
                nonlocal intensity, direction
                
                intensity += direction * 0.1
                if intensity >= 1.0:
                    intensity = 1.0
                    direction = -1
                elif intensity <= 0.3:
                    intensity = 0.3
                    direction = 1
                
                # 简化发光效果，不使用透明度
                try:
                    if self._is_focused:
                        if intensity > 0.6:
                            self.configure(border_color=Colors.PRIMARY)
                        else:
                            self.configure(border_color=Colors.BORDER_LIGHT)
                except:
                    pass
                
                if self._is_focused:
                    self.after(800, glow_animation)
            
            glow_animation()

    class EnhancedTextbox(ctk.CTkTextbox):
        """增强的文本框组件"""
        
        def __init__(self, parent, **kwargs):
            enhanced_kwargs = {
                'corner_radius': 12,
                'border_width': 1,
                'border_color': Colors.BORDER_LIGHT,
                'fg_color': Colors.SURFACE,
                'text_color': Colors.TEXT_PRIMARY,
                'font': Fonts.MONO_SMALL
            }
            enhanced_kwargs.update(kwargs)
            super().__init__(parent, **enhanced_kwargs)
            
            # 绑定聚焦效果
            self.bind("<FocusIn>", self._on_focus_in)
            self.bind("<FocusOut>", self._on_focus_out)
            
        def _on_focus_in(self, event):
            self.configure(
                border_color=Colors.PRIMARY,
                border_width=2,
                fg_color=Colors.SURFACE_HOVER
            )
            
        def _on_focus_out(self, event):
            self.configure(
                border_color=Colors.BORDER_LIGHT,
                border_width=1,
                fg_color=Colors.SURFACE
            )
    
    
    class CollapsibleSection(ctk.CTkFrame):
        """可折叠的区域组件"""
        
        def __init__(self, parent, title: str, **kwargs):
            kwargs.update({
                'corner_radius': 8,
                'fg_color': Colors.SURFACE_LIGHT,
                'border_width': 1,
                'border_color': Colors.BORDER_LIGHT
            })
            super().__init__(parent, **kwargs)
            
            self.is_expanded = False
            self.content_frame = None
            
            # 标题栏
            self.header_frame = ctk.CTkFrame(self, fg_color='transparent')
            self.header_frame.pack(fill='x', padx=10, pady=10)
            
            # 展开/折叠按钮
            self.toggle_btn = ctk.CTkButton(
                self.header_frame,
                text="▶",
                width=20,
                height=20,
                font=('', 12),
                fg_color='transparent',
                text_color=Colors.TEXT_SECONDARY,
                hover_color=Colors.SURFACE,
                command=self.toggle
            )
            self.toggle_btn.pack(side='left', padx=(0, 10))
            
            # 标题文本
            self.title_label = ctk.CTkLabel(
                self.header_frame,
                text=title,
                font=Fonts.H2,  # 使用与其他区域一致的字体样式
                text_color=Colors.TEXT_PRIMARY
            )
            self.title_label.pack(side='left')
        
        def add_content(self, setup_func):
            """添加内容"""
            if self.content_frame is None:
                self.content_frame = ctk.CTkFrame(self, fg_color='transparent')
            setup_func(self.content_frame)
            return self.content_frame
        
        def toggle(self):
            """切换展开/折叠状态"""
            if self.is_expanded:
                self.collapse()
            else:
                self.expand()
        
        def expand(self):
            """展开（即时）"""
            if not self.content_frame:
                return
            self.content_frame.pack(fill='x', padx=10, pady=(0, 10))
            self.toggle_btn.configure(text="▼")
            self.is_expanded = True

        def collapse(self):
            """折叠（即时）"""
            if not self.content_frame:
                return
            try:
                self.content_frame.pack_forget()
            except Exception:
                pass
            self.toggle_btn.configure(text="▶")
            self.is_expanded = False
    
    
    class FieldFrame(ctk.CTkFrame):
        """字段框架 - 包含标签、输入控件和帮助按钮"""
        
        def __init__(self, parent, label: str, help_text: str = "", required: bool = False, **kwargs):
            kwargs.update({
                'corner_radius': 8,
                'fg_color': 'transparent'
            })
            super().__init__(parent, **kwargs)
            
            # 标签行
            label_frame = ctk.CTkFrame(self, fg_color='transparent')
            label_frame.pack(fill='x', pady=(0, 5))
            
            # 标签文本
            label_text = f"{'* ' if required else ''}{label}"
            self.label = ctk.CTkLabel(
                label_frame, 
                text=label_text,
                font=('', 13, 'bold' if required else 'normal'),
                text_color=Colors.ERROR if required else Colors.TEXT_PRIMARY
            )
            self.label.pack(side='left')
            
            # 帮助按钮
            if help_text:
                self.help_btn = HelpButton(label_frame, help_text)
                self.help_btn.pack(side='right')
    
    
    class PaddingButton(ctk.CTkFrame):
        """带内边距的按钮容器"""
        
        def __init__(self, parent, **kwargs):
            kwargs.update({
                'corner_radius': 8,
                'fg_color': Colors.SURFACE,
                'border_width': 1,
                'border_color': Colors.BORDER
            })
            super().__init__(parent, **kwargs)
            
        def add_button(self, text: str, command, icon: str = "", width: int = 120, variant: str = 'primary'):
            """添加按钮 (支持 variant: primary|secondary|accent|accent_alt|danger|outline)"""
            style_map = {
                'primary': Style.BUTTON_PRIMARY,
                'secondary': Style.BUTTON_SECONDARY,
                'accent': Style.BUTTON_ACCENT,
                'accent_alt': Style.BUTTON_ACCENT_ALT,
                'danger': Style.BUTTON_DANGER,
                'outline': Style.BUTTON_OUTLINE,
            }
            style = style_map.get(variant, Style.BUTTON_PRIMARY).copy()
            btn_text = f"{icon} {text}" if icon else text
            btn = ctk.CTkButton(
                self,
                text=btn_text,
                width=width,
                height=32,
                **style,
                command=command
            )
            btn.pack(side='left', padx=8, pady=8)
            return btn
    
    
    class BuildProgressDialog(ctk.CTkToplevel):
        """构建进度对话框"""
        
        def __init__(self, parent):
            super().__init__(parent)
            self.title("构建安装器")
            self.geometry("500x350")
            self.resizable(False, False)
            
            # 设置模态
            self.transient(parent)
            self.grab_set()
            
            # 居中显示
            self.center_window()
            
            # 进度信息
            self.cancelled = False
            self.setup_ui()
        
        def center_window(self):
            """窗口居中"""
            self.update_idletasks()
            x = (self.winfo_screenwidth() // 2) - (500 // 2)
            y = (self.winfo_screenheight() // 2) - (350 // 2)
            self.geometry(f"500x350+{x}+{y}")
        
        def setup_ui(self):
            """设置UI"""
            # 标题
            title_label = ctk.CTkLabel(self, text="🏗️ 正在构建安装器", font=Fonts.H1, text_color=Colors.PRIMARY)
            title_label.pack(pady=(20, 10))
            
            # 当前状态
            self.status_var = ctk.StringVar(value="准备中...")
            self.status_label = ctk.CTkLabel(self, textvariable=self.status_var, font=Fonts.BODY, text_color=Colors.TEXT_SECONDARY)
            self.status_label.pack(pady=5)
            
            # 进度条
            self.progress_bar = ctk.CTkProgressBar(self, width=400, progress_color=Colors.PRIMARY, fg_color=Colors.SURFACE_LIGHT)
            self.progress_bar.pack(pady=10)
            self.progress_bar.set(0)
            
            # 详细日志（折叠）
            self.log_frame = LiquidFrame(self, width=450, height=150)
            self.log_frame.pack(pady=10, padx=25, fill='both', expand=True)
            
            self.log_text = ctk.CTkTextbox(self.log_frame, width=420, height=120, fg_color=Colors.BACKGROUND, text_color=Colors.TEXT_PRIMARY, border_width=0, font=Fonts.MONO_SMALL)
            self.log_text.pack(pady=10, padx=10, fill='both', expand=True)
            
            # 按钮框架
            btn_frame = ctk.CTkFrame(self, fg_color='transparent')
            btn_frame.pack(pady=10)
            
            # 取消按钮
            self.cancel_btn = ctk.CTkButton(btn_frame, text="取消", width=100, command=self.cancel_build, fg_color=Colors.ERROR, hover_color=Colors.PRIMARY_DARK, text_color='white')
            self.cancel_btn.pack(side='left', padx=10)
            
            # 关闭按钮（初始隐藏）
            self.close_btn = ctk.CTkButton(btn_frame, text="关闭", width=100, command=self.destroy, fg_color=Colors.SUCCESS, hover_color=Colors.ACCENT, text_color='white')
        
        def update_progress(self, progress: float, status: str, log: str = ""):
            """更新进度"""
            self.progress_bar.set(progress)
            self.status_var.set(status)
            
            if log:
                self.log_text.insert('end', f"{log}\n")
                self.log_text.see('end')
            
            self.update()
        
        def show_error(self, error_msg: str):
            """显示错误"""
            self.status_var.set(f"❌ 构建失败")
            self.log_text.insert('end', f"\n❌ 错误: {error_msg}\n")
            self.log_text.see('end')
            
            # 切换按钮
            self.cancel_btn.pack_forget()
            self.close_btn.pack(side='left', padx=10)
        
        def show_success(self, output_path: str):
            """显示成功"""
            self.progress_bar.set(1.0)
            self.status_var.set(f"✅ 构建成功！")
            self.log_text.insert('end', f"\n✅ 安装器已生成: {output_path}\n")
            self.log_text.see('end')
            
            # 切换按钮
            self.cancel_btn.pack_forget()
            self.close_btn.pack(side='left', padx=10)
        
        def cancel_build(self):
            """取消构建"""
            self.cancelled = True
            self.destroy()
    

    
    class PostActionDialog(ctk.CTkToplevel):
        """后置脚本配置对话框"""
        
        def __init__(self, parent):
            super().__init__(parent)
            self.title("配置后置脚本")
            self.geometry("500x400")
            self.resizable(False, False)
            
            # 设置模态
            self.transient(parent)
            self.grab_set()
            
            self.action = None
            self.setup_ui()
            self.center_window()
        
        def center_window(self):
            """窗口居中"""
            self.update_idletasks()
            x = (self.winfo_screenwidth() // 2) - (500 // 2)
            y = (self.winfo_screenheight() // 2) - (400 // 2)
            self.geometry(f"500x400+{x}+{y}")
        
        def setup_ui(self):
            """设置UI"""
            main_frame = ctk.CTkFrame(self, fg_color='transparent')
            main_frame.pack(fill='both', expand=True, padx=20, pady=20)
            
            # 脚本类型
            type_label = ctk.CTkLabel(main_frame, text="脚本类型:", font=Fonts.BODY)
            type_label.pack(anchor='w', pady=(0, 5))
            
            self.script_type = ctk.CTkOptionMenu(
                main_frame,
                values=["powershell", "batch"],
                fg_color=Colors.BACKGROUND,
                button_color=Colors.PRIMARY
            )
            self.script_type.pack(fill='x', pady=(0, 10))
            
            # 命令
            cmd_label = ctk.CTkLabel(main_frame, text="命令或脚本路径:", font=Fonts.BODY)
            cmd_label.pack(anchor='w', pady=(0, 5))
            
            self.command = ctk.CTkEntry(main_frame, placeholder_text="输入命令或选择脚本文件", **Style.ENTRY)
            self.command.pack(fill='x', pady=(0, 10))
            
            # 按钮框架
            btn_frame = ctk.CTkFrame(self, fg_color='transparent')
            btn_frame.pack(fill='x', pady=20)
            
            # 取消和确定按钮
            cancel_btn = ctk.CTkButton(
                btn_frame,
                text="取消",
                width=100,
                command=self.cancel,
                **Style.BUTTON_SECONDARY
            )
            cancel_btn.pack(side='left', padx=20)
            
            ok_btn = ctk.CTkButton(
                btn_frame,
                text="确定",
                width=100,
                command=self.confirm,
                **Style.BUTTON_PRIMARY
            )
            ok_btn.pack(side='right', padx=20)
        
        def confirm(self):
            """确认配置"""
            if not self.command.get().strip():
                return
                
            self.action = {
                'type': self.script_type.get(),
                'command': self.command.get().strip(),
                'args': None,
                'hidden': True,
                'timeout_sec': 300,
                'show_in_ui': True,
                'run_if': 'always',
                'working_dir': None
            }
            self.destroy()
        
        def cancel(self):
            """取消配置"""
            self.action = None
            self.destroy()
        
        def get_action(self):
            """获取配置的脚本动作"""
            self.wait_window()
            return self.action


    class InspaBuilderGUI:
        """Inspa 构建器主界面"""
        
        def __init__(self):
            self.root = ctk.CTk()
            self.config_data = {}
            self.input_paths = []
            self.setup_window()
            self.setup_ui()
            self.load_default_config()
            
            # 显示核心模块状态
            if not CORE_MODULES_AVAILABLE:
                # 在标题栏中添加状态提示
                self.root.title("Inspa - Windows 安装器构建工具 (核心模块未加载)")
                # 可以考虑添加一个状态栏或提示
        
        def setup_window(self):
            """设置窗口 - 增强版带启动动画"""
            self.root.title("Inspa - Windows 安装器构建工具 ✨")
            self.root.geometry("800x900")
            self.root.minsize(750, 800)
            
            # 启动时窗口透明度动画
            self.root.attributes("-alpha", 0.0)  # 开始时完全透明
            self._start_window_fade_in()

        def _start_window_fade_in(self):
            """窗口淡入动画"""
            alpha = 0.0
            def fade_in():
                nonlocal alpha
                alpha += 0.05
                if alpha >= 1.0:
                    alpha = 1.0
                    
                try:
                    self.root.attributes("-alpha", alpha)
                except:
                    pass
                
                if alpha < 1.0:
                    self.root.after(30, fade_in)  # 快速平滑淡入
                    
            fade_in()

        # --- 前置声明：配置导入导出在文件后部实现，避免 header 中引用时报缺失 ---
        # 原导入导出方法在类后部定义
            
            # 设置应用图标（如果存在）
            # self.root.iconbitmap("assets/icon.ico")
            
            # 居中显示
            self.center_window()
        
        def center_window(self):
            """窗口居中 - 带缩放动画"""
            self.root.update_idletasks()
            x = (self.root.winfo_screenwidth() // 2) - (800 // 2)
            y = (self.root.winfo_screenheight() // 2) - (900 // 2)
            
            # 先设置到稍小的尺寸，然后缩放到正常大小
            self.root.geometry(f"700x800+{x + 50}+{y + 50}")
            self._start_window_scale_in(x, y)
            
        def _start_window_scale_in(self, target_x, target_y):
            """窗口缩放动画"""
            current_width = 700
            current_height = 800
            current_x = target_x + 50
            current_y = target_y + 50
            
            def scale_in():
                nonlocal current_width, current_height, current_x, current_y
                
                # 逐渐接近目标尺寸
                current_width += (800 - current_width) * 0.15
                current_height += (900 - current_height) * 0.15
                current_x += (target_x - current_x) * 0.15
                current_y += (target_y - current_y) * 0.15
                
                try:
                    self.root.geometry(f"{int(current_width)}x{int(current_height)}+{int(current_x)}+{int(current_y)}")
                except:
                    pass
                
                # 如果还没到达目标尺寸，继续动画
                if abs(current_width - 800) > 1 or abs(current_height - 900) > 1:
                    self.root.after(16, scale_in)  # 60fps
                else:
                    # 最终设置为精确尺寸
                    self.root.geometry(f"800x900+{target_x}+{target_y}")
                    
            scale_in()
        
        def setup_ui(self):
            """设置用户界面 - 增强美化版"""
            # 设置主窗口背景色（渐变效果）
            self.root.configure(fg_color=Colors.BACKGROUND)
            self._glow_sections: list[NeonSectionFrame] = []
            
            # 启动背景微动画
            self._start_background_animation()
            
            # 创建增强滚动框架
            self.main_frame = ctk.CTkScrollableFrame(
                self.root,
                fg_color=Colors.GRADIENT_MID,
                corner_radius=15,
                border_width=1,
                border_color=Colors.BORDER_GLOW
            )
            self.main_frame.pack(fill='both', expand=True, padx=12, pady=12)
            
            # 添加界面元素
            self.setup_header()
            self.setup_product_section()
            self.setup_resources_section()
            self.setup_ui_section()
            self.setup_install_section()
            self.setup_compression_section()
            self.setup_input_section()
            self.setup_post_actions_section()
            self.setup_env_section()
            self.setup_build_section()
            self.setup_status_bar()
            
            # 启动全局发光循环
            self._start_glow_cycle()
            
        def _start_background_animation(self):
            """启动背景微妙动画效果"""
            bg_intensity = 0.5
            bg_direction = 1
            
            def animate_background():
                nonlocal bg_intensity, bg_direction
                
                bg_intensity += bg_direction * 0.02
                if bg_intensity >= 1.0:
                    bg_intensity = 1.0
                    bg_direction = -1
                elif bg_intensity <= 0.3:
                    bg_intensity = 0.3
                    bg_direction = 1
                
                # 微妙的背景颜色变化
                try:
                    # 计算背景色的微变化
                    base_rgb = (10, 11, 17)  # Colors.BACKGROUND 的 RGB
                    variation = int(5 * bg_intensity)
                    new_rgb = (
                        min(base_rgb[0] + variation, 25),
                        min(base_rgb[1] + variation, 26), 
                        min(base_rgb[2] + variation, 32)
                    )
                    new_color = f"#{new_rgb[0]:02x}{new_rgb[1]:02x}{new_rgb[2]:02x}"
                    
                    self.root.configure(fg_color=new_color)
                except:
                    pass
                
                self.root.after(4000, animate_background)  # 非常慢的变化
                
            animate_background()
            
            # 创建滚动框架
            self.main_frame = ctk.CTkScrollableFrame(
                self.root,
                corner_radius=0,
                fg_color=Colors.SURFACE
            )
            self.main_frame.pack(fill='both', expand=True, padx=20, pady=10)
            
            # 标题区域
            self.setup_header()
            
            # 产品信息区域（必填）
            self.setup_product_section()
            
            # 资源配置区域（图标等）
            self.setup_resources_section()
            
            # 安装配置区域（必填）
            self.setup_install_section()
            
            # 界面配置区域
            self.setup_ui_section()
            
            # 输入文件区域（必填）
            self.setup_input_section()
            
            # 压缩设置区域（可折叠）
            self.setup_compression_section()
            
            # 后置脚本区域（可折叠）
            self.setup_post_actions_section()
            
            # 环境变量区域（可折叠）
            self.setup_env_section()
            
            # 高级设置区域（可折叠）
            self.setup_advanced_section()
            
            # 构建按钮区域
            self.setup_build_section()

            # 状态栏
            self.setup_status_bar()
            self._start_glow_cycle()
            self._activate_energy_mode()

        def _register_glow(self, frame: 'NeonSectionFrame'):
            self._glow_sections.append(frame)

        def _start_glow_cycle(self):
            # 使用 RAINBOW_PALETTE 做平滑渐变 (线性插值)
            palette = Colors.RAINBOW_PALETTE
            if not palette:
                return
            state = {
                'i': 0,          # 当前调色板索引
                'step': 0,       # 当前插值步
                'max_step': 18,  # 每两色之间插值步数
            }

            def hex_to_rgb(h: str):
                h = h.lstrip('#')
                return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
            def rgb_to_hex(rgb):
                return '#%02X%02X%02X' % rgb
            def lerp(a: int, b: int, t: float) -> int:
                return int(a + (b - a) * t)

            def tick():
                i = state['i']
                step = state['step']
                a = palette[i % len(palette)]
                b = palette[(i + 1) % len(palette)]
                ra, ga, ba = hex_to_rgb(a)
                rb, gb, bb = hex_to_rgb(b)
                t = step / state['max_step']
                color = rgb_to_hex((lerp(ra, rb, t), lerp(ga, gb, t), lerp(ba, bb, t)))
                for f in self._glow_sections:
                    f.set_glow_color(color)
                # 步推进
                step += 1
                if step > state['max_step']:
                    step = 0
                    i += 1
                state['i'] = i
                state['step'] = step
                self.root.after(300, tick)
            self.root.after(300, tick)

        def setup_status_bar(self):
            """底部状态栏"""
            bar = ctk.CTkFrame(self.root, fg_color=Colors.BACKGROUND, height=26)
            bar.pack(fill='x', side='bottom')
            bar.grid_propagate(False)
            self.status_files_var = ctk.StringVar(value="文件: 0")
            self.status_size_var = ctk.StringVar(value="大小: 0 B")
            self.status_msg_var = ctk.StringVar(value="就绪")
            files_label = ctk.CTkLabel(bar, textvariable=self.status_files_var, font=Fonts.SMALL, text_color=Colors.TEXT_MUTED)
            files_label.pack(side='left', padx=12)
            size_label = ctk.CTkLabel(bar, textvariable=self.status_size_var, font=Fonts.SMALL, text_color=Colors.TEXT_MUTED)
            size_label.pack(side='left')
            msg_label = ctk.CTkLabel(bar, textvariable=self.status_msg_var, font=Fonts.SMALL, text_color=Colors.TEXT_MUTED)
            msg_label.pack(side='right', padx=12)
        
        def setup_header(self):
            """设置标题区域"""
            header_frame = LiquidFrame(self.main_frame)
            header_frame.pack(fill='x', pady=(0, 20))
            header_frame.configure(height=80)  # 增加header高度确保内容显示完整
            
            # 右侧工具栏容器
            tool_btn_frame = ctk.CTkFrame(header_frame, fg_color='transparent')
            tool_btn_frame.pack(side='right', padx=14, pady=(15,10))  # 调整pady确保居中
            
            # 居中标题：使用内部独立容器 place 绝对居中
            title_container = ctk.CTkFrame(header_frame, fg_color='transparent')
            title_container.place(relx=0.5, rely=0.5, anchor='center')  # 改为完全居中
            title_label = ctk.CTkLabel(title_container, text="🚀 Inspa", font=Fonts.TITLE, text_color=Colors.ORANGE)
            title_label.pack()
            self._title_label = title_label  # 保存引用供动画使用

            # 固定暗色主题，无主题切换
            self.current_theme = 'dark'

            # 信息按钮（显示副描述） - 使用统一的HelpButton样式
            subtitle_text = "现代化的 Windows 单文件自解压安装器构建工具"
            if not CORE_MODULES_AVAILABLE:
                subtitle_text += "\n⚠️ 核心模块未加载 - 部分功能将不可用"
            
            info_btn = HelpButton(tool_btn_frame, subtitle_text)
            info_btn.pack(side='left', padx=6)

            # 启动标题炫彩循环
            self._start_title_cycle()

        def _start_title_cycle(self):
            if not hasattr(self, '_title_label'):
                return
            palette = Colors.RAINBOW_PALETTE
            if not palette:
                return
            # 保存引用供同步使用
            self._sync_cycle_state = {'i': 0}
            
            def step():
                try:
                    color = palette[self._sync_cycle_state['i'] % len(palette)]
                    self._title_label.configure(text_color=color)
                    self._sync_cycle_state['i'] += 1
                except Exception:
                    return
                self.root.after(400, step)
            self.root.after(400, step)

        # 主题切换相关逻辑已移除（固定暗色）
        
        def setup_product_section(self):
            """设置产品信息区域"""
            section_frame = NeonSectionFrame(self.main_frame)
            section_frame.pack(fill='x', pady=(0, Layout.P_SECTION_Y))
            self._register_glow(section_frame)

            # 标题
            section_title = ctk.CTkLabel(
                section_frame.content,
                text="📦 产品信息",
                font=Fonts.H2,
                text_color=Colors.TEXT_PRIMARY,
                anchor='w'
            )
            section_title.pack(fill='x', padx=Layout.P_SECTION_X, pady=(15, Layout.P_FIELD_TITLE_BOTTOM))

            # 网格容器
            grid = ctk.CTkFrame(section_frame.content, fg_color='transparent')
            grid.pack(fill='x', padx=Layout.P_SECTION_X, pady=(0, Layout.P_GROUP_GAP))
            for i in range(2):
                grid.grid_columnconfigure(i, weight=1, uniform="prod")

            def make_field(row: int, col: int, label: str, placeholder: str, help_text: str = "", required: bool = False, attr: str | None = None):
                wrapper = FieldFrame(grid, label=label, help_text=help_text, required=required)
                wrapper.grid(row=row, column=col, sticky='nsew', padx=(0 if col == 0 else 16), pady=Layout.P_FIELD_Y)
                entry = ctk.CTkEntry(wrapper, placeholder_text=placeholder, **Style.ENTRY)
                entry.pack(fill='x', pady=(5, 0))
                if attr:
                    setattr(self, attr, entry)
                return entry

            # 第1行：必填字段
            make_field(
                0, 0,
                label="产品名称",
                placeholder="例如：我的应用程序",
                help_text="安装器和程序显示名称",
                required=True,
                attr='product_name'
            )
            make_field(
                0, 1,
                label="版本号",
                placeholder="1.0.0",
                help_text="语义化版本 (SemVer)",
                required=True,
                attr='product_version'
            )
            
            # 第2行：公司和描述
            make_field(
                1, 0,
                label="公司名称",
                placeholder="例如：我的公司",
                help_text="开发公司或组织名称",
                attr='product_company'
            )
            make_field(
                1, 1,
                label="产品描述",
                placeholder="一句话简介",
                help_text="将显示在安装器中",
                attr='product_description'
            )
            
            # 第3行：版权和网站
            make_field(
                2, 0,
                label="版权信息",
                placeholder="© 2024 我的公司. 保留所有权利.",
                help_text="版权声明信息",
                attr='product_copyright'
            )
            make_field(
                2, 1,
                label="官网地址",
                placeholder="https://example.com",
                help_text="产品或公司官方网站",
                attr='product_website'
            )
        
        def setup_resources_section(self):
            """设置资源配置区域"""
            section_frame = NeonSectionFrame(self.main_frame)
            section_frame.pack(fill='x', pady=(0, Layout.P_SECTION_Y))
            self._register_glow(section_frame)
            
            # 区域标题
            section_title = ctk.CTkLabel(
                section_frame.content,
                text="🎨 资源配置",
                font=Fonts.H2,
                text_color=Colors.TEXT_PRIMARY,
                anchor='w'
            )
            section_title.pack(fill='x', padx=Layout.P_SECTION_X, pady=(15, Layout.P_FIELD_TITLE_BOTTOM))
            
            # 图标文件配置
            icon_field = FieldFrame(
                section_frame.content,
                label="自定义图标",
                help_text="选择自定义图标文件 (.ico 格式)"
            )
            icon_field.pack(fill='x', padx=Layout.P_SECTION_X, pady=Layout.P_FIELD_Y)
            
            icon_frame = ctk.CTkFrame(icon_field, fg_color='transparent')
            icon_frame.pack(fill='x', pady=(5, 0))
            
            self.icon_path = ctk.CTkEntry(
                icon_frame,
                placeholder_text="选择 .ico 图标文件（可选）",
                **Style.ENTRY
            )
            self.icon_path.pack(side='left', fill='x', expand=True, padx=(0, 10))
            
            browse_icon_btn = ctk.CTkButton(
                icon_frame,
                text="浏览",
                width=70,
                command=self.browse_icon_path,
                **Style.BUTTON_OUTLINE
            )
            browse_icon_btn.pack(side='right')
        
        def setup_install_section(self):
            """设置安装配置区域"""
            section_frame = NeonSectionFrame(self.main_frame)
            section_frame.pack(fill='x', pady=(0, Layout.P_SECTION_Y))
            self._register_glow(section_frame)
            
            # 区域标题
            section_title = ctk.CTkLabel(
                section_frame.content,
                text="⚙️ 安装设置",
                font=Fonts.H2,
                text_color=Colors.TEXT_PRIMARY,
                anchor='w'
            )
            section_title.pack(fill='x', padx=Layout.P_SECTION_X, pady=(15, Layout.P_FIELD_TITLE_BOTTOM))
            
            # 默认安装路径（必填）
            path_field = FieldFrame(
                section_frame.content,
                label="默认安装路径",
                help_text="软件的默认安装目录，支持环境变量（如 %ProgramFiles%）",
                required=True
            )
            path_field.pack(fill='x', padx=Layout.P_SECTION_X, pady=Layout.P_FIELD_Y)
            
            path_frame = ctk.CTkFrame(path_field, fg_color='transparent')
            path_frame.pack(fill='x', pady=(5, 0))
            
            self.install_path = ctk.CTkEntry(
                path_frame,
                placeholder_text="C:\\Program Files\\我的应用",
                **Style.ENTRY
            )
            self.install_path.pack(side='left', fill='x', expand=True, padx=(0, 10))
            
            browse_btn = ctk.CTkButton(
                path_frame,
                text="浏览",
                width=70,
                command=self.browse_install_path,
                **Style.BUTTON_OUTLINE
            )
            browse_btn.pack(side='right')
            
            # 安装选项
            options_frame = ctk.CTkFrame(section_frame.content, fg_color='transparent')
            options_frame.pack(fill='x', padx=Layout.P_SECTION_X, pady=(10, 0))
            
            # 安装选项第1列
            options_left = ctk.CTkFrame(options_frame, fg_color='transparent')
            options_left.pack(side='left', fill='both', expand=True, padx=(0, 10))
            
            self.allow_user_path = ctk.CTkCheckBox(
                options_left,
                text="允许用户修改安装路径"
            )
            self.allow_user_path.pack(anchor='w', pady=2)
            
            self.force_hidden_path = ctk.CTkCheckBox(
                options_left,
                text="强制隐藏路径选择"
            )
            self.force_hidden_path.pack(anchor='w', pady=2)
            
            self.show_ui = ctk.CTkCheckBox(
                options_left,
                text="显示安装界面"
            )
            self.show_ui.pack(anchor='w', pady=2)
            
            self.silent_allowed = ctk.CTkCheckBox(
                options_left,
                text="允许静默安装"
            )
            self.silent_allowed.pack(anchor='w', pady=2)
            
            # 安装选项第2列
            options_right = ctk.CTkFrame(options_frame, fg_color='transparent')
            options_right.pack(side='left', fill='both', expand=True)
            
            self.require_admin = ctk.CTkCheckBox(
                options_right,
                text="需要管理员权限"
            )
            self.require_admin.pack(anchor='w', pady=2)
            
            # 协议文件配置
            license_field = FieldFrame(
                section_frame.content,
                label="许可协议文件",
                help_text="选择许可协议文件 (.txt/.md/.rst 格式，可选)"
            )
            license_field.pack(fill='x', padx=Layout.P_SECTION_X, pady=(10, Layout.P_FIELD_Y))
            
            license_frame = ctk.CTkFrame(license_field, fg_color='transparent')
            license_frame.pack(fill='x', pady=(5, 0))
            
            self.license_file = ctk.CTkEntry(
                license_frame,
                placeholder_text="许可协议文件路径（可选）",
                **Style.ENTRY
            )
            self.license_file.pack(side='left', fill='x', expand=True, padx=(0, 10))
            
            browse_license_btn = ctk.CTkButton(
                license_frame,
                text="浏览",
                width=70,
                command=self.browse_license_file,
                **Style.BUTTON_OUTLINE
            )
            browse_license_btn.pack(side='right')
            
            # 隐私文件配置
            privacy_field = FieldFrame(
                section_frame.content,
                label="隐私声明文件",
                help_text="选择隐私声明文件 (.txt/.md/.rst 格式，可选)"
            )
            privacy_field.pack(fill='x', padx=Layout.P_SECTION_X, pady=(0, Layout.P_GROUP_GAP))
            
            privacy_frame = ctk.CTkFrame(privacy_field, fg_color='transparent')
            privacy_frame.pack(fill='x', pady=(5, 0))
            
            self.privacy_file = ctk.CTkEntry(
                privacy_frame,
                placeholder_text="隐私声明文件路径（可选）",
                **Style.ENTRY
            )
            self.privacy_file.pack(side='left', fill='x', expand=True, padx=(0, 10))
            
            browse_privacy_btn = ctk.CTkButton(
                privacy_frame,
                text="浏览",
                width=70,
                command=self.browse_privacy_file,
                **Style.BUTTON_OUTLINE
            )
            browse_privacy_btn.pack(side='right')
        
        def setup_ui_section(self):
            """设置UI配置区域"""
            section_frame = NeonSectionFrame(self.main_frame)
            section_frame.pack(fill='x', pady=(0, Layout.P_SECTION_Y))
            self._register_glow(section_frame)
            
            # 区域标题
            section_title = ctk.CTkLabel(
                section_frame.content,
                text="🎨 界面配置",
                font=Fonts.H2,
                text_color=Colors.TEXT_PRIMARY,
                anchor='w'
            )
            section_title.pack(fill='x', padx=Layout.P_SECTION_X, pady=(15, Layout.P_FIELD_TITLE_BOTTOM))
            
            # UI配置网格
            ui_grid = ctk.CTkFrame(section_frame.content, fg_color='transparent')
            ui_grid.pack(fill='x', padx=Layout.P_SECTION_X, pady=(0, Layout.P_GROUP_GAP))
            for i in range(2):
                ui_grid.grid_columnconfigure(i, weight=1, uniform="ui")
            
            def make_ui_field(row: int, col: int, label: str, placeholder: str, help_text: str = "", attr: str | None = None):
                wrapper = FieldFrame(ui_grid, label=label, help_text=help_text)
                wrapper.grid(row=row, column=col, sticky='nsew', padx=(0 if col == 0 else 16), pady=Layout.P_FIELD_Y)
                entry = ctk.CTkEntry(wrapper, placeholder_text=placeholder, **Style.ENTRY)
                entry.pack(fill='x', pady=(5, 0))
                if attr:
                    setattr(self, attr, entry)
                return entry
            
            # UI字段
            make_ui_field(
                0, 0,
                label="窗口标题",
                placeholder="自动生成（产品名称 + 安装程序）",
                help_text="安装器窗口标题栏显示的文字",
                attr='ui_window_title'
            )
            make_ui_field(
                0, 1,
                label="欢迎页主标题",
                placeholder="自动生成（欢迎安装 + 产品名称）",
                help_text="安装器欢迎页面的主标题",
                attr='ui_welcome_heading'
            )
            make_ui_field(
                1, 0,
                label="欢迎页副标题",
                placeholder="请按步骤完成安装",
                help_text="安装器欢迎页面的副标题",
                attr='ui_welcome_subtitle'
            )
            
            # UI选项
            ui_options = ctk.CTkFrame(section_frame.content, fg_color='transparent')
            ui_options.pack(fill='x', padx=Layout.P_SECTION_X, pady=(10, Layout.P_GROUP_GAP))
            
            self.show_script_output = ctk.CTkCheckBox(
                ui_options,
                text="在进度页面显示脚本输出"
            )
            self.show_script_output.pack(anchor='w', pady=2)
        
        def setup_input_section(self):
            """设置输入文件区域"""
            section_frame = NeonSectionFrame(self.main_frame)
            section_frame.pack(fill='x', pady=(0, Layout.P_SECTION_Y))
            self._register_glow(section_frame)
            
            # 区域标题
            section_title = ctk.CTkLabel(
                section_frame.content,
                text="📁 输入文件",
                font=Fonts.H2,
                text_color=Colors.TEXT_PRIMARY,
                anchor='w'
            )
            section_title.pack(fill='x', padx=Layout.P_SECTION_X, pady=(15, Layout.P_FIELD_TITLE_BOTTOM))
            
            # 输入路径列表
            input_field = FieldFrame(
                section_frame.content,
                label="要打包的文件或目录",
                help_text="选择需要打包到安装器中的文件和文件夹",
                required=True
            )
            input_field.pack(fill='x', padx=Layout.P_SECTION_X, pady=Layout.P_FIELD_Y)
            
            # 输入列表容器（可滚动）
            list_frame = ctk.CTkFrame(
                input_field,
                fg_color=Colors.LIST_BG,
                border_width=1,
                border_color=Colors.BORDER
            )
            list_frame.pack(fill='x', pady=(5, 0))

            self.file_list_canvas = ctk.CTkScrollableFrame(
                list_frame,
                fg_color=Colors.LIST_BG,
                height=140,
                corner_radius=0
            )
            self.file_list_canvas.pack(fill='x', padx=8, pady=(8, 4))
            # 存储当前文件行 Frame 引用（不做精细类型注解避免运行期解析 GUI 类名）
            self._file_rows = []  # type: ignore
            self._dest_path_map: dict[str, str] = {}
            self._size_cache: dict[str, int] = {}
            self._size_dirty = True
            # 拖拽支持占位：若安装 tkinterdnd2 可扩展为真正拖拽
            try:
                import tkinterdnd2  # type: ignore  # noqa: F401
                self._dnd_available = True
            except Exception:
                self._dnd_available = False
            
            # 使用 PaddingButton 容器
            btn_container = PaddingButton(list_frame)
            btn_container.pack(fill='x', padx=10, pady=10)
            
            # 添加按钮
            btn_container.add_button("📄 添加文件", self.add_files, width=100, variant='primary')
            btn_container.add_button("📁 添加文件夹", self.add_folder, width=108, variant='accent')

            # 选项（去重 / 展开目录）
            opts_frame = ctk.CTkFrame(section_frame.content, fg_color='transparent')
            opts_frame.pack(fill='x', padx=Layout.P_SECTION_X, pady=(4, 4))
            self.opt_dedup = ctk.CTkCheckBox(opts_frame, text='自动去重', command=lambda: self.update_input_list())
            self.opt_dedup.pack(side='left')
            self.opt_expand_dir = ctk.CTkCheckBox(opts_frame, text='展开目录为文件', command=lambda: self.update_input_list())
            self.opt_expand_dir.pack(side='left', padx=14)
            # 默认开启去重
            self.opt_dedup.select()

            # 拖拽提示标签
            drag_tip = ctk.CTkLabel(section_frame.content,
                                    text=('可拖拽文件/目录到此（已检测到 tkinterdnd2）' if self._dnd_available else '安装 tkinterdnd2 以启用拖拽添加文件'),
                                    text_color=Colors.TEXT_MUTED,
                                    font=Fonts.SMALL,
                                    anchor='w')
            drag_tip.pack(fill='x', padx=Layout.P_SECTION_X, pady=(0,4))
            
            # 清空按钮（右对齐）
            clear_frame = ctk.CTkFrame(btn_container, fg_color='transparent')
            clear_frame.pack(side='right', fill='y')
            
            clear_btn = ctk.CTkButton(
                clear_frame,
                text="🗑️ 清空",
                width=80,
                height=32,
                **Style.BUTTON_DANGER,
                command=self.clear_inputs
            )
            clear_btn.pack(pady=8)
        
        def setup_compression_section(self):
            """设置压缩区域"""
            section = CollapsibleSection(
                self.main_frame,
                "🗜️ 压缩设置"
            )
            section.pack(fill='x', pady=(0, Layout.P_SECTION_Y))
            
            def setup_compression_content(parent):
                # 压缩算法
                algo_field = FieldFrame(
                    parent,
                    label="压缩算法",
                    help_text="ZSTD 提供更好的压缩比，ZIP 兼容性更好"
                )
                algo_field.pack(fill='x', padx=20, pady=5)
                
                self.compression_algo = ctk.CTkOptionMenu(
                    algo_field,
                    values=["zstd", "zip"],
                    command=self.on_compression_change,
                    fg_color=Colors.BACKGROUND,
                    button_color=Colors.PRIMARY,
                    button_hover_color=Colors.PRIMARY_DARK
                )
                self.compression_algo.pack(anchor='w', pady=(5, 0))
                
                # 压缩级别
                level_field = FieldFrame(
                    parent,
                    label="压缩级别",
                    help_text="更高的级别提供更好的压缩比，但需要更多时间"
                )
                level_field.pack(fill='x', padx=20, pady=(Layout.P_FIELD_Y, Layout.P_GROUP_GAP))
                
                level_frame = ctk.CTkFrame(level_field, fg_color='transparent')
                level_frame.pack(fill='x', pady=(5, 0))
                
                self.compression_level = ctk.CTkSlider(
                    level_frame,
                    from_=1,
                    to=22,
                    number_of_steps=21,
                    progress_color=Colors.PRIMARY,
                    button_color=Colors.PRIMARY,
                    button_hover_color=Colors.PRIMARY_DARK
                )
                self.compression_level.pack(side='left', fill='x', expand=True, padx=(0, 10))
                
                self.level_label = ctk.CTkLabel(
                    level_frame, 
                    text="3",
                    text_color=Colors.TEXT_PRIMARY
                )
                self.level_label.pack(side='right')
                
                self.compression_level.configure(command=self.update_level_label)
                self.compression_level.set(3)
                    
                self.compression_level.configure(command=self.update_level_label)
                self.compression_level.set(3)
                
            section.add_content(setup_compression_content)
            # 默认保持折叠状态（不调用 expand）
        
        def setup_post_actions_section(self):
            """设置后置脚本区域（可折叠）"""
            post_section = CollapsibleSection(
                self.main_frame,
                "⚡ 后置脚本"
            )
            post_section.pack(fill='x', pady=(0, 15))
            
            def setup_post_content(parent):
                # 后置脚本说明
                info_label = ctk.CTkLabel(
                    parent,
                    text="配置安装完成后执行的脚本或命令",
                    font=Fonts.SMALL,
                    text_color=Colors.TEXT_MUTED
                )
                info_label.pack(fill='x', padx=20, pady=(5, 10))
                
                # 脚本列表容器
                self.post_actions_frame = ctk.CTkScrollableFrame(
                    parent,
                    fg_color=Colors.LIST_BG,
                    height=120,
                    corner_radius=8
                )
                self.post_actions_frame.pack(fill='x', padx=20, pady=5)
                
                self.post_actions = []  # 存储脚本配置
                
                # 添加脚本按钮
                add_script_btn = ctk.CTkButton(
                    parent,
                    text="➕ 添加脚本",
                    command=self.add_post_action,
                    **Style.BUTTON_ACCENT
                )
                add_script_btn.pack(pady=10)
            
            post_section.add_content(setup_post_content)
        
        def setup_env_section(self):
            """设置环境变量区域（可折叠）"""
            env_section = CollapsibleSection(
                self.main_frame,
                "🌍 环境变量"
            )
            env_section.pack(fill='x', pady=(0, 15))
            
            def setup_env_content(parent):
                # 系统作用域选项
                scope_frame = ctk.CTkFrame(parent, fg_color='transparent')
                scope_frame.pack(fill='x', padx=20, pady=5)
                
                self.env_system_scope = ctk.CTkCheckBox(
                    scope_frame,
                    text="使用系统级作用域（需要管理员权限）"
                )
                self.env_system_scope.pack(anchor='w', pady=2)
                
                # PATH 环境变量
                path_field = FieldFrame(
                    parent,
                    label="添加到 PATH",
                    help_text="要添加到 PATH 环境变量的路径，一行一个"
                )
                path_field.pack(fill='x', padx=20, pady=5)
                
                self.env_path = ctk.CTkTextbox(
                    path_field,
                    height=80,
                    fg_color=Colors.BACKGROUND,
                    border_width=1,
                    border_color=Colors.BORDER,
                    text_color=Colors.TEXT_PRIMARY
                )
                self.env_path.pack(fill='x', pady=(5, 0))
                
                # 自定义环境变量
                custom_field = FieldFrame(
                    parent,
                    label="自定义环境变量",
                    help_text="格式：变量名=变量值，一行一个"
                )
                custom_field.pack(fill='x', padx=20, pady=(10, 15))
                
                self.env_custom = ctk.CTkTextbox(
                    custom_field,
                    height=80,
                    fg_color=Colors.BACKGROUND,
                    border_width=1,
                    border_color=Colors.BORDER,
                    text_color=Colors.TEXT_PRIMARY
                )
                self.env_custom.pack(fill='x', pady=(5, 0))
            
            env_section.add_content(setup_env_content)
        
        def setup_advanced_section(self):
            """设置高级选项区域（可折叠）"""
            advanced_section = CollapsibleSection(
                self.main_frame,
                "🔧 高级选项"
            )
            advanced_section.pack(fill='x', pady=(0, 15))
            
            def setup_advanced_content(parent):
                # 排除模式
                exclude_field = FieldFrame(
                    parent,
                    label="排除模式",
                    help_text="使用 glob 模式排除不需要的文件，一行一个模式"
                )
                exclude_field.pack(fill='x', padx=20, pady=5)
                
                self.exclude_patterns = ctk.CTkTextbox(
                    exclude_field,
                    height=80,
                    fg_color=Colors.BACKGROUND,
                    border_width=1,
                    border_color=Colors.BORDER,
                    text_color=Colors.TEXT_PRIMARY
                )
                self.exclude_patterns.pack(fill='x', pady=(5, 0))
                # 插入默认内容
                self.exclude_patterns.insert('1.0', "*.pyc\n__pycache__/\n*.log")
                
                # 配置文件操作
                config_field = FieldFrame(
                    parent,
                    label="配置文件",
                    help_text="可以导入现有配置文件或导出当前设置"
                )
                config_field.pack(fill='x', padx=20, pady=(10, 15))
                
                config_container = PaddingButton(config_field)
                config_container.pack(fill='x', pady=(5, 0))
                
                config_container.add_button("📂 导入配置", self.import_config, width=100)
                config_container.add_button("💾 导出配置", self.export_config, width=100)
            
            advanced_section.add_content(setup_advanced_content)
        
        def setup_build_section(self):
            """设置构建区域"""
            build_frame = NeonSectionFrame(self.main_frame)
            build_frame.pack(fill='x', pady=(0, Layout.P_BUILD_BOTTOM))
            self._register_glow(build_frame)
            
            # 输出路径
            output_field = FieldFrame(
                build_frame.content,
                label="输出路径",
                help_text="生成的安装器 EXE 文件保存位置"
            )
            output_field.pack(fill='x', padx=Layout.P_SECTION_X, pady=(15, Layout.P_FIELD_TITLE_BOTTOM))
            
            output_frame = ctk.CTkFrame(output_field, fg_color='transparent')
            output_frame.pack(fill='x', pady=(5, 0))
            
            self.output_path = ctk.CTkEntry(
                output_frame,
                placeholder_text="installer.exe",
                **Style.ENTRY
            )
            self.output_path.pack(side='left', fill='x', expand=True, padx=(0, 10))
            
            browse_output_btn = ctk.CTkButton(
                output_frame,
                text="浏览",
                width=70,
                command=self.browse_output_path,
                **Style.BUTTON_OUTLINE
            )
            browse_output_btn.pack(side='right')
            
            # 构建按钮
            self.build_btn = GlowButton(
                build_frame,
                text="🚀 构建安装器",
                height=40,
                font=("Segoe UI", 16, "bold"),
                fg_color=Colors.SUCCESS,
                hover_color=Colors.HYPER_LIME,
                text_color=Colors.TEXT_LIGHT,
                border_color=Colors.GLOW_GREEN,
                glow_color=Colors.GLOW_GREEN,
                command=self.start_build
            )
            btn_wrapper = ctk.CTkFrame(build_frame.content, fg_color='transparent')
            btn_wrapper.pack(fill='x', padx=18, pady=(10, 24))
            glow_bg = GlowFrame(btn_wrapper, glow_color=Colors.GLOW_GREEN)
            glow_bg.pack(fill='x', padx=4, pady=4)
            self.build_btn.pack(in_=glow_bg, fill='x', padx=8, pady=8)
            self._start_pulse_animation()
            self._start_build_button_pulse()

        def _start_pulse_animation(self):
            """已停用的脉冲动画（保持静态颜色以减少干扰）。"""
            # 保持成功绿色，不做动画
            if hasattr(self, 'build_btn'):
                self.build_btn.configure(fg_color=Colors.SUCCESS)

        def _start_build_button_pulse(self):
            if not hasattr(self, 'build_btn'):
                return
            # 使用与title同步的颜色循环
            def pulse():
                try:
                    if hasattr(self, '_sync_cycle_state'):
                        idx = self._sync_cycle_state['i'] % len(Colors.RAINBOW_PALETTE)
                        color = Colors.RAINBOW_PALETTE[idx]
                        self.build_btn.configure(fg_color=color, hover_color=color)
                except Exception:
                    return
                self.root.after(400, pulse)  # 与title同步400ms
            self.root.after(400, pulse)

        def _activate_energy_mode(self):
            """集中开启高动效：背景微闪烁。"""
            base = Colors.BACKGROUND
            # 预计算两个变体
            def hex_to_rgb(h: str):
                h = h.lstrip('#'); return tuple(int(h[i:i+2],16) for i in (0,2,4))
            def rgb_to_hex(rgb):
                return '#%02X%02X%02X' % rgb
            r,g,b = hex_to_rgb(base)
            up = rgb_to_hex((min(r+6,255), min(g+6,255), min(b+10,255)))
            down = rgb_to_hex((max(r-4,0), max(g-4,0), max(b-6,0)))
            seq = [base, up, base, down]
            idx = {'i':0}
            def flicker():
                try:
                    color = seq[idx['i'] % len(seq)]
                    self.main_frame.configure(fg_color=color)
                    idx['i'] += 1
                except Exception:
                    return
                self.root.after(1800, flicker)
            self.root.after(1800, flicker)
        
        def load_default_config(self):
            """加载默认配置"""
            # 设置默认值
            self.product_name.insert(0, "我的应用程序")
            self.product_version.insert(0, "1.0.0")
            self.install_path.insert(0, "C:\\Program Files\\我的应用程序")
            self.output_path.insert(0, "installer.exe")
            
            # 设置默认选项
            self.allow_user_path.select()
            self.show_ui.select()
            self.silent_allowed.select()
            
            if hasattr(self, 'show_script_output'):
                self.show_script_output.select()
            
            # 设置默认排除模式
            self.exclude_patterns.insert('end', "*.pyc\n__pycache__/\n*.log\n*.tmp\n.git/")
        
        # 事件处理方法
        def browse_install_path(self):
            """浏览安装路径"""
            path = filedialog.askdirectory(title="选择默认安装目录")
            if path:
                self.install_path.delete(0, 'end')
                self.install_path.insert(0, path)
        
        def browse_output_path(self):
            """浏览输出路径"""
            path = filedialog.asksaveasfilename(
                title="保存安装器",
                defaultextension=".exe",
                filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
            )
            if path:
                self.output_path.delete(0, 'end')
                self.output_path.insert(0, path)
        
        def browse_icon_path(self):
            """浏览图标文件"""
            path = filedialog.askopenfilename(
                title="选择图标文件",
                filetypes=[("图标文件", "*.ico"), ("所有文件", "*.*")]
            )
            if path:
                self.icon_path.delete(0, 'end')
                self.icon_path.insert(0, path)
        
        def browse_license_file(self):
            """浏览许可协议文件"""
            path = filedialog.askopenfilename(
                title="选择许可协议文件",
                filetypes=[
                    ("文本文件", "*.txt"),
                    ("Markdown", "*.md"),
                    ("reStructuredText", "*.rst"),
                    ("所有文件", "*.*")
                ]
            )
            if path:
                self.license_file.delete(0, 'end')
                self.license_file.insert(0, path)
        
        def browse_privacy_file(self):
            """浏览隐私声明文件"""
            path = filedialog.askopenfilename(
                title="选择隐私声明文件",
                filetypes=[
                    ("文本文件", "*.txt"),
                    ("Markdown", "*.md"),
                    ("reStructuredText", "*.rst"),
                    ("所有文件", "*.*")
                ]
            )
            if path:
                self.privacy_file.delete(0, 'end')
                self.privacy_file.insert(0, path)
        
        def add_post_action(self):
            """添加后置脚本"""
            # 创建一个对话框来配置脚本
            dialog = PostActionDialog(self.root)
            action = dialog.get_action()
            
            if action:
                self.post_actions.append(action)
                self.update_post_actions_list()
        
        def update_post_actions_list(self):
            """更新后置脚本列表显示"""
            # 清理现有显示
            for widget in self.post_actions_frame.winfo_children():
                widget.destroy()
            
            for i, action in enumerate(self.post_actions):
                action_frame = ctk.CTkFrame(self.post_actions_frame, fg_color=Colors.SURFACE_LIGHT)
                action_frame.pack(fill='x', pady=2, padx=5)
                
                # 脚本信息
                info = f"{action['type']}: {action['command']}"
                if len(info) > 60:
                    info = info[:57] + "..."
                
                info_label = ctk.CTkLabel(
                    action_frame,
                    text=info,
                    font=Fonts.MONO_SMALL,
                    text_color=Colors.TEXT_PRIMARY
                )
                info_label.pack(side='left', fill='x', expand=True, padx=8, pady=4)
                
                # 删除按钮
                del_btn = ctk.CTkButton(
                    action_frame,
                    text="✕",
                    width=24,
                    height=20,
                    command=lambda idx=i: self.remove_post_action(idx),
                    **Style.BUTTON_DANGER
                )
                del_btn.pack(side='right', padx=4, pady=2)
        
        def remove_post_action(self, index: int):
            """删除后置脚本"""
            if 0 <= index < len(self.post_actions):
                self.post_actions.pop(index)
                self.update_post_actions_list()
        
        def add_files(self):
            """添加文件"""
            files = filedialog.askopenfilenames(title="选择要打包的文件")
            for file in files:
                self.input_paths.append(file)
            if self.opt_dedup.get():
                self._deduplicate_inputs()
            self._size_dirty = True
            self.update_input_list()
        
        def add_folder(self):
            """添加文件夹"""
            folder = filedialog.askdirectory(title="选择要打包的文件夹")
            if folder:
                self.input_paths.append(folder)
                if self.opt_dedup.get():
                    self._deduplicate_inputs()
                self._size_dirty = True
                self.update_input_list()

        def _deduplicate_inputs(self):
            # 保持原顺序的去重
            seen = set()
            new_list = []
            for p in self.input_paths:
                if p not in seen:
                    seen.add(p)
                    new_list.append(p)
            self.input_paths = new_list
        
        # --- 缺失的方法补回 ---
        def clear_inputs(self):
            """清空输入列表"""
            self.input_paths.clear()
            self.update_input_list()

        def update_input_list(self):
            """更新输入列表显示并刷新状态栏 (交互式行)"""
            # 清理旧行
            for row in getattr(self, '_file_rows', []):
                try:
                    row.destroy()
                except Exception:
                    pass
            self._file_rows.clear()

            alt = False
            import os
            # 颜色插值辅助
            def hex_to_rgb(h: str):
                h = h.lstrip('#')
                return tuple(int(h[i:i+2], 16) for i in (0,2,4))
            def rgb_to_hex(rgb):
                return '#%02X%02X%02X' % rgb
            def tween(c1: str, c2: str, steps: int = 10) -> list[str]:
                r1,g1,b1 = hex_to_rgb(c1); r2,g2,b2 = hex_to_rgb(c2)
                out=[]
                for s in range(steps):
                    t = s/(steps-1)
                    r=int(r1+(r2-r1)*t); g=int(g1+(g2-g1)*t); b=int(b1+(b2-b1)*t)
                    out.append(rgb_to_hex((r,g,b)))
                return out
            for idx, p in enumerate(self.input_paths, start=1):
                row = ctk.CTkFrame(self.file_list_canvas, fg_color=Colors.LIST_ALT if alt else Colors.LIST_BG, corner_radius=4)
                row.pack(fill='x', pady=2)
                alt = not alt

                # 序号
                num_label = ctk.CTkLabel(row, text=f"{idx}", width=24, anchor='w', text_color=Colors.TEXT_MUTED, font=Fonts.MONO_SMALL)
                num_label.pack(side='left', padx=(6, 4))

                # 左侧路径标签（可双击）
                exists = os.path.exists(p)
                readable = False
                if exists:
                    try:
                        readable = os.access(p, os.R_OK)
                    except Exception:
                        readable = False
                text_color = Colors.TEXT_PRIMARY if (exists and readable) else Colors.ERROR
                path_label = ctk.CTkLabel(row, text=p, anchor='w', text_color=text_color, font=Fonts.MONO_SMALL)
                path_label.pack(side='left', fill='x', expand=True, padx=4, pady=4)

                # 目标子路径（可编辑）
                dest_wrapper = ctk.CTkFrame(row, fg_color='transparent')
                dest_wrapper.pack(side='right', padx=4, pady=4)
                if p not in self._dest_path_map:
                    import os
                    self._dest_path_map[p] = os.path.basename(p.rstrip('/\\')) or 'root'
                entry = ctk.CTkEntry(dest_wrapper, width=140, **Style.ENTRY)
                entry.insert(0, self._dest_path_map[p])
                entry.pack(side='left')
                entry.bind('<FocusOut>', lambda e, src=p, ent=entry: self._on_dest_edit(src, ent))
                tip_label = ctk.CTkLabel(dest_wrapper, text='→', text_color=Colors.TEXT_MUTED, width=10)
                tip_label.pack(side='left', padx=(4,0))

                # 删除按钮
                del_btn = ctk.CTkButton(row, text='✕', width=26, height=24, fg_color=Colors.SURFACE_LIGHT, hover_color=Colors.ERROR, text_color=Colors.TEXT_MUTED, command=lambda path=p: self._remove_input_path(path))
                del_btn.pack(side='right', padx=6, pady=4)

                # 绑定交互
                path_label.bind('<Double-Button-1>', lambda e, path=p: self._open_in_explorer(path))
                def _animate_bg(frame, frames: list[str], idx0=0):
                    if idx0 >= len(frames):
                        return
                    try:
                        frame.configure(fg_color=frames[idx0])
                    except Exception:
                        return
                    frame.after(20, lambda: _animate_bg(frame, frames, idx0+1))
                base_color = Colors.LIST_ALT if ((idx-1) % 2) else Colors.LIST_BG
                hover_target = Colors.SURFACE_LIGHT
                forward_seq = tween(base_color, hover_target, 12)
                back_seq = list(reversed(forward_seq))
                def _on_enter(evt, r=row):
                    _animate_bg(r, forward_seq)
                def _on_leave(evt, r=row):
                    _animate_bg(r, back_seq)
                row.bind('<Enter>', _on_enter)
                row.bind('<Leave>', _on_leave)
                path_label.bind('<Button-3>', lambda e, path=p: self._show_file_context_menu(e, path))
                row.bind('<Button-3>', lambda e, path=p: self._show_file_context_menu(e, path))

                self._file_rows.append(row)

            if hasattr(self, 'status_files_var'):
                self.status_files_var.set(f"文件: {len(self.input_paths)}")
            self._update_total_size_async()

        def _remove_input_path(self, path: str):
            try:
                self.input_paths.remove(path)
            except ValueError:
                return
            self._dest_path_map.pop(path, None)
            # 移除缓存并标记更新
            self._size_cache.pop(path, None)
            self._size_dirty = True
            self.update_input_list()

        def _on_dest_edit(self, src_path: str, entry_widget):
            val = entry_widget.get().strip().replace('\\','/').lstrip('/')
            if not val:
                import os
                val = os.path.basename(src_path.rstrip('/\\')) or 'root'
                entry_widget.delete(0,'end')
                entry_widget.insert(0,val)
            self._dest_path_map[src_path] = val

        def _open_in_explorer(self, path: str):
            import subprocess, os
            try:
                if os.path.isdir(path):
                    subprocess.Popen(['explorer', path])
                else:
                    subprocess.Popen(['explorer', '/select,', path])
            except Exception:
                pass

        def _show_file_context_menu(self, event, path: str):
            import tkinter as tk
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label='打开位置', command=lambda p=path: self._open_in_explorer(p))
            menu.add_command(label='移除', command=lambda p=path: self._remove_input_path(p))
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        def _update_total_size_async(self):
            if not hasattr(self, '_size_thread') or not self._size_thread.is_alive():
                import threading
                self._size_thread = threading.Thread(target=self._calc_total_size, daemon=True)
                self._size_thread.start()

        def _calc_total_size(self):
            import os, time
            # 若未标记脏且缓存可用，则直接显示
            if not self._size_dirty and self._size_cache:
                total_cached = sum(self._size_cache.values())
                if hasattr(self, 'status_size_var'):
                    try:
                        self.status_size_var.set(f"大小: {self._fmt_size(total_cached)}")
                    except Exception:
                        pass
                return

            total = 0
            new_cache: dict[str, int] = {}
            for p in self.input_paths:
                if p in self._size_cache:
                    sz = self._size_cache[p]
                    total += sz
                    new_cache[p] = sz
                    continue
                size_val = 0
                if os.path.isfile(p):
                    try:
                        size_val = os.path.getsize(p)
                    except Exception:
                        size_val = 0
                elif os.path.isdir(p):
                    for root, _dirs, files in os.walk(p):
                        for f in files:
                            fp = os.path.join(root, f)
                            try:
                                size_val += os.path.getsize(fp)
                            except Exception:
                                pass
                new_cache[p] = size_val
                total += size_val
            self._size_cache = new_cache
            self._size_dirty = False
            def fmt(sz: int):
                units = ['B','KB','MB','GB','TB']
                v = float(sz)
                for u in units:
                    if v < 1024 or u == units[-1]:
                        return f"{v:.2f} {u}"
                    v /= 1024
            if hasattr(self, 'status_size_var'):
                try:
                    self.status_size_var.set(f"大小: {fmt(total)}")
                except Exception:
                    pass

        def _fmt_size(self, sz: int) -> str:
            units = ['B','KB','MB','GB','TB']
            v = float(sz)
            for u in units:
                if v < 1024 or u == units[-1]:
                    return f"{v:.2f} {u}"
                v /= 1024
            return f"{v:.2f} TB"

        def on_compression_change(self, value):
            """压缩算法改变时调整级别范围"""
            if value == 'zstd':
                self.compression_level.configure(to=22)
            else:
                self.compression_level.configure(to=9)
                if self.compression_level.get() > 9:
                    self.compression_level.set(9)
            self.update_level_label(self.compression_level.get())

        def update_level_label(self, value):
            self.level_label.configure(text=str(int(float(value))))

        def import_config(self):
            """导入配置文件"""
            if not CORE_MODULES_AVAILABLE:
                messagebox.showerror("错误", "核心模块未可用，无法导入配置文件")
                return
            file_path = filedialog.askopenfilename(
                title="选择配置文件",
                filetypes=[("YAML文件", "*.yaml"), ("YAML文件", "*.yml"), ("所有文件", "*.*")]
            )
            if file_path:
                try:
                    config = load_config(Path(file_path))
                    self.load_config_to_ui(config)
                    messagebox.showinfo("成功", "配置文件导入成功！")
                except Exception as e:
                    messagebox.showerror("错误", f"导入配置文件失败：{e}")
        
        def export_config(self):
            """导出配置文件"""
            if not CORE_MODULES_AVAILABLE:
                messagebox.showerror("错误", "核心模块未可用，无法导出配置文件")
                return
                
            file_path = filedialog.asksaveasfilename(
                title="保存配置文件",
                defaultextension=".yaml",
                filetypes=[("YAML文件", "*.yaml"), ("所有文件", "*.*")]
            )
            if file_path:
                try:
                    config = self.build_config()
                    self.save_config_to_file(config, Path(file_path))
                    messagebox.showinfo("成功", "配置文件导出成功！")
                except Exception as e:
                    messagebox.showerror("错误", f"导出配置文件失败：{e}")
        
        def load_config_to_ui(self, config: InspaConfig):
            """将配置加载到UI"""
            # 清空现有内容
            self.clear_ui_fields()
            
            # 产品信息
            if config.product.name:
                self.product_name.insert(0, config.product.name)
            if config.product.version:
                self.product_version.insert(0, config.product.version)
            if config.product.company:
                self.product_company.insert(0, config.product.company)
            if config.product.description:
                self.product_description.insert(0, config.product.description)
            if config.product.copyright:
                self.product_copyright.insert(0, config.product.copyright)
            if config.product.website:
                self.product_website.insert(0, config.product.website)
            
            # 资源配置
            if config.resources and config.resources.icon:
                self.icon_path.insert(0, str(config.resources.icon))
            
            # UI 配置
            if config.ui:
                if config.ui.window_title:
                    self.window_title.insert(0, config.ui.window_title)
                if config.ui.welcome_heading:
                    self.welcome_heading.insert(0, config.ui.welcome_heading)
                if config.ui.welcome_subtitle:
                    self.welcome_subtitle.insert(0, config.ui.welcome_subtitle)
            
            # 安装设置
            if config.install.default_path:
                self.install_path.insert(0, config.install.default_path)
            
            if config.install.license_file:
                self.license_file.insert(0, str(config.install.license_file))
            if config.install.privacy_file:
                self.privacy_file.insert(0, str(config.install.privacy_file))
            
            # 设置复选框
            if config.install.allow_user_path:
                self.allow_user_path.select()
            else:
                self.allow_user_path.deselect()
            
            if config.install.show_ui:
                self.show_ui.select()
            else:
                self.show_ui.deselect()
                
            if config.install.silent_allowed:
                self.silent_allowed.select()
            else:
                self.silent_allowed.deselect()
            
            if config.install.require_admin:
                self.require_admin.select()
            else:
                self.require_admin.deselect()
                
            if config.install.force_hidden_path:
                self.force_hidden_path.select()
            else:
                self.force_hidden_path.deselect()
            
            # 压缩设置
            self.compression_algo.set(config.compression.algo.value)
            self.compression_level.set(config.compression.level)
            
            # 输入路径
            self.input_paths.clear()
            for input_path in config.inputs:
                self.input_paths.append(str(input_path.path))
            self.update_input_list()
            
            # 排除模式
            if config.exclude:
                self.exclude_patterns.delete('1.0', 'end')
                self.exclude_patterns.insert('end', '\n'.join(config.exclude))
            
            # 后置脚本
            if config.post_actions:
                self.post_actions_list = []
                for action in config.post_actions:
                    action_dict = {
                        'type': action.type.value,
                        'command': action.command,
                        'args': list(action.args) if action.args else [],
                        'hidden': action.hidden,
                        'timeout_sec': action.timeout_sec,
                        'show_in_ui': action.show_in_ui,
                        'run_if': action.run_if.value,
                        'working_dir': action.working_dir
                    }
                    self.post_actions_list.append(action_dict)
                self.update_post_actions_list()
            
            # 环境变量
            if config.env:
                # 清空现有环境变量
                for widget in self.env_vars_frame.winfo_children():
                    widget.destroy()
                
                # 添加路径环境变量
                if config.env.add_path:
                    for path in config.env.add_path:
                        self.add_env_var('PATH', path, append_path=True)
                
                # 添加设置环境变量
                if config.env.set:
                    for key, value in config.env.set.items():
                        self.add_env_var(key, value, append_path=False)
        
        def clear_ui_fields(self):
            """清空UI字段"""
            self.product_name.delete(0, 'end')
            self.product_version.delete(0, 'end')
            self.product_company.delete(0, 'end')
            self.product_description.delete(0, 'end')
            self.install_path.delete(0, 'end')
            self.exclude_patterns.delete('1.0', 'end')
            self.input_paths.clear()
            self.update_input_list()
        
        def build_config(self) -> InspaConfig:
            """从UI构建配置对象"""
            if not CORE_MODULES_AVAILABLE:
                raise RuntimeError("核心模块不可用，无法构建配置")
            
            # 收集产品信息
            product = ProductModel(
                name=self.product_name.get().strip(),
                version=self.product_version.get().strip(),
                company=self.product_company.get().strip() or None,
                description=self.product_description.get().strip() or None,
                copyright=self.product_copyright.get().strip() or None,
                website=self.product_website.get().strip() or None
            )
            
            # 资源配置
            resources = None
            icon_path = self.icon_path.get().strip()
            if icon_path:
                from inspa.config.schema import ResourcesModel
                resources = ResourcesModel(icon=Path(icon_path))
            
            # UI配置
            from inspa.config.schema import UIModel
            ui = UIModel(
                window_title=self.ui_window_title.get().strip() or None,
                welcome_heading=self.ui_welcome_heading.get().strip() or None,
                welcome_subtitle=self.ui_welcome_subtitle.get().strip() or None,
                show_progress_script_output=bool(self.show_script_output.get())
            )
            
            # 安装设置
            install = InstallModel(
                default_path=self.install_path.get().strip(),
                allow_user_path=bool(self.allow_user_path.get()),
                force_hidden_path=bool(self.force_hidden_path.get()),
                show_ui=bool(self.show_ui.get()),
                silent_allowed=bool(self.silent_allowed.get()),
                require_admin=bool(self.require_admin.get()),
                license_file=Path(self.license_file.get().strip()) if self.license_file.get().strip() else None,
                privacy_file=Path(self.privacy_file.get().strip()) if self.privacy_file.get().strip() else None
            )
            
            # 压缩配置
            algo_val = self.compression_algo.get().lower()
            try:
                algo_enum = CompressionAlgorithm(algo_val)
            except Exception:
                algo_enum = CompressionAlgorithm.ZSTD  # 回退
            
            from inspa.config.schema import CompressionModel
            compression = CompressionModel(
                algo=algo_enum,
                level=int(float(self.compression_level.get()))
            )

            # 输入路径
            from inspa.config.schema import InputPathModel
            inputs = []
            for src in self.input_paths:
                input_model = InputPathModel(
                    path=Path(src),
                    recursive=True,  # 默认递归
                    preserve_structure=True  # 默认保持结构
                )
                inputs.append(input_model)

            # 排除模式
            exclude_patterns = []
            try:
                raw = self.exclude_patterns.get('1.0', 'end').strip()
                if raw:
                    exclude_patterns = [l.strip() for l in raw.splitlines() if l.strip()]
            except Exception:
                pass

            # 后置脚本
            post_actions = None
            if hasattr(self, 'post_actions') and self.post_actions:
                from inspa.config.schema import PostActionModel, ScriptType, RunCondition
                post_actions = []
                for action_dict in self.post_actions:
                    post_action = PostActionModel(
                        type=ScriptType(action_dict['type']),
                        command=action_dict['command'],
                        args=action_dict.get('args'),
                        hidden=action_dict.get('hidden', True),
                        timeout_sec=action_dict.get('timeout_sec', 300),
                        show_in_ui=action_dict.get('show_in_ui', True),
                        run_if=RunCondition(action_dict.get('run_if', 'always')),
                        working_dir=action_dict.get('working_dir')
                    )
                    post_actions.append(post_action)

            # 环境变量
            env = None
            if hasattr(self, 'env_path') or hasattr(self, 'env_custom'):
                from inspa.config.schema import EnvironmentModel
                
                # PATH 变量
                add_path = None
                try:
                    path_text = self.env_path.get('1.0', 'end').strip()
                    if path_text:
                        add_path = [line.strip() for line in path_text.splitlines() if line.strip()]
                except Exception:
                    pass
                
                # 自定义环境变量
                env_set = None
                try:
                    custom_text = self.env_custom.get('1.0', 'end').strip()
                    if custom_text:
                        env_set = {}
                        for line in custom_text.splitlines():
                            line = line.strip()
                            if '=' in line:
                                key, value = line.split('=', 1)
                                env_set[key.strip()] = value.strip()
                except Exception:
                    pass
                
                if add_path or env_set:
                    env = EnvironmentModel(
                        add_path=add_path,
                        set=env_set,
                        system_scope=bool(self.env_system_scope.get()) if hasattr(self, 'env_system_scope') else False
                    )

            # 构建完整配置
            config = InspaConfig(
                product=product,
                resources=resources,
                ui=ui,
                install=install,
                inputs=inputs,
                compression=compression,
                exclude=exclude_patterns if exclude_patterns else None,
                post_actions=post_actions,
                env=env
            )
            
            return config
        
        def save_config_to_file(self, config: InspaConfig, file_path: Path):
            """保存配置到文件"""
            # TODO: 实现配置保存逻辑
            pass
        
        def start_build(self):
            """开始构建"""
            # 检查核心模块是否可用
            if not CORE_MODULES_AVAILABLE:
                messagebox.showerror(
                    "错误", 
                    "Inspa 核心模块未可用，无法进行构建。\n\n"
                    "可能的原因：\n"
                    "1. 项目未正确安装 (pip install -e .)\n"
                    "2. Python 路径设置问题\n"
                    "3. 依赖模块缺失\n\n"
                    "请检查安装并重新启动程序。"
                )
                return
            
            # 验证输入
            if not self.validate_inputs():
                return
            
            # 创建进度对话框
            progress_dialog = BuildProgressDialog(self.root)
            
            # 在后台线程中执行构建
            # 禁用主按钮，更新状态
            self.build_btn.configure(state='disabled')
            if hasattr(self, 'status_msg_var'):
                self.status_msg_var.set('正在构建...')

            def build_thread():
                try:
                    # 使用真实的 Builder 进行构建
                    from pathlib import Path
                    
                    # 构建配置对象
                    config = self.build_config()
                    
                    # 创建构建器实例
                    builder = InspaBuilder()
                    
                    # 输出路径处理
                    output_path_str = self.output_path.get().strip()
                    if not output_path_str:
                        output_path_str = "installer.exe"
                    output_path = Path(output_path_str)
                    
                    # 确保输出目录存在
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 进度回调适配器：(stage_name, current, total, detail) -> update_progress(progress, status, log)
                    def progress_adapter(stage_name: str, current: int, total: int, detail: str):
                        if progress_dialog.cancelled:
                            return
                        progress = current / max(total, 1)
                        status = f"{stage_name} ({current}/{total})"
                        progress_dialog.update_progress(progress, status, detail)
                    
                    # 执行构建
                    result = builder.build(
                        config=config,
                        output_path=output_path,
                        progress_callback=progress_adapter
                    )
                    
                    if not progress_dialog.cancelled and result.success:
                        progress_dialog.show_success(str(result.output_path))
                        if hasattr(self, 'status_msg_var'):
                            self.status_msg_var.set('构建完成')
                    elif not result.success:
                        error_msg = getattr(result, 'error', '构建失败，原因未知')
                        progress_dialog.show_error(error_msg)
                        if hasattr(self, 'status_msg_var'):
                            self.status_msg_var.set('构建失败')
                        
                except Exception as e:
                    import traceback
                    error_detail = f"{str(e)}\n\n详细信息:\n{traceback.format_exc()}"
                    progress_dialog.show_error(error_detail)
                    if hasattr(self, 'status_msg_var'):
                        self.status_msg_var.set('构建失败')
                finally:
                    # 恢复按钮
                    try:
                        self.build_btn.configure(state='normal')
                    except Exception:
                        pass
            
            # 启动构建线程
            build_thread_obj = threading.Thread(target=build_thread, daemon=True)
            build_thread_obj.start()
        
        def validate_inputs(self) -> bool:
            """验证输入"""
            errors = []
            
            if not self.product_name.get().strip():
                errors.append("请输入产品名称")
            
            if not self.product_version.get().strip():
                errors.append("请输入产品版本")
            
            if not self.install_path.get().strip():
                errors.append("请输入默认安装路径")
            
            if not self.input_paths:
                errors.append("请添加要打包的文件或文件夹")
            
            if errors:
                messagebox.showerror("输入错误", "\n".join(errors))
                return False
            
            return True
        
        def run(self):
            """运行GUI"""
            self.root.mainloop()
    
    # 兼容性别名
    BuilderGUI = InspaBuilderGUI

else:
    # 如果GUI不可用，提供存根类
    class BuilderGUI:
        def __init__(self):
            raise ImportError("GUI 依赖未安装，无法启动图形界面")
        
        def run(self):
            raise ImportError("GUI 依赖未安装，无法启动图形界面")


def main():
    """GUI 主函数"""
    if not GUI_AVAILABLE:
        print("错误: GUI 依赖未安装")
        print("请安装依赖: pip install customtkinter")
        return 1
    
    try:
        app = BuilderGUI()
        app.run()
        return 0
    except Exception as e:
        print(f"GUI 启动失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())