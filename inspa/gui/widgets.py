"""
CustomTkinter custom widgets for Inspa GUI.
"""
import customtkinter as ctk
from tkinter import messagebox
from typing import Any as _Any

from .theme import Colors, Fonts, Style, ensure_contrast

class Layout:
    """布局间距常量，统一管理。"""
    P_SECTION_Y = 14          # Section 之间的垂直间距
    P_SECTION_X = 20          # Section 内左右统一 padding
    P_FIELD_Y = 6             # 字段(行)之间的垂直间距
    P_FIELD_TITLE_BOTTOM = 8  # 字段标题与字段控件之间的间距
    P_GROUP_GAP = 14          # 同组块之间的额外分隔
    P_BUILD_BOTTOM = 8        # 最后构建区与底部距离

    _scale = 1.0

    @classmethod
    def apply_scale(cls, scale: float):
        cls._scale = scale
        cls.P_SECTION_Y = int(14 * scale)
        cls.P_SECTION_X = int(20 * scale)
        cls.P_FIELD_Y = max(2, int(6 * scale))
        cls.P_FIELD_TITLE_BOTTOM = max(4, int(8 * scale))
        cls.P_GROUP_GAP = int(14 * scale)
        cls.P_BUILD_BOTTOM = int(8 * scale)

class LiquidFrame(ctk.CTkFrame):
    """简化版半透明/发光容器 (之前版本残留引用)"""
    def __init__(self, parent, **kwargs):
        base = {
            'corner_radius': 16,
            'fg_color': Colors.SURFACE_LIGHT,
            'border_width': 1,
            'border_color': Colors.BORDER_GLOW
        }
        base.update(kwargs)
        super().__init__(parent, **base)

class HelpButton(ctk.CTkButton):
    """统一的帮助按钮 (点击显示说明对话框)"""
    def __init__(self, parent, help_text: str, **kwargs):
        style = {
            'width': 26,
            'height': 26,
            'text': 'ℹ',
            'fg_color': Colors.SURFACE_LIGHT,
            'hover_color': Colors.SURFACE_HOVER,
            'border_width': 1,
            'border_color': Colors.BORDER,
            'text_color': Colors.TEXT_SECONDARY,
            'corner_radius': 6,
            'font': Fonts.SMALL
        }
        style.update(kwargs)
        super().__init__(parent, **style, command=self._show)
        self._help_text = help_text

    def _show(self):
        try:
            messagebox.showinfo("说明", self._help_text)
        except Exception:
            pass

class NeonSectionFrame(LiquidFrame):
    """带左侧窄霓虹条的 Section 容器，可自定义强调色"""
    _title_label: _Any  # 允许后续赋值为 CTkLabel
    def __init__(self, parent, accent_color: str | None = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.accent_color = accent_color or Colors.PRIMARY
        self._neutral_color = getattr(Colors, 'N300', Colors.SURFACE_HOVER)
        # 更窄的竖条 (现在 2px)
        self.neon_bar = ctk.CTkFrame(
            self,
            width=2,
            fg_color=self._neutral_color,
            corner_radius=2
        )
        self.neon_bar.pack(side='left', fill='y', padx=(0, 2))
        # 收紧内边距
        self.inner = ctk.CTkFrame(self, fg_color='transparent')
        self.inner.pack(side='left', fill='both', expand=True, padx=0, pady=2)
        self.content = ctk.CTkFrame(self.inner, fg_color='transparent')
        self.content.pack(fill='both', expand=True, padx=0, pady=0)
        # 标题引用占位（动态设置，不做强类型）
        self._title_label = None  # runtime assigned

    def set_glow_color(self, color: str):
        try:
            self.accent_color = color
            self.configure(border_color=self._neutral_color)
            # 实际激活时在外部调用 restore()
        except Exception:
            pass

    def weaken(self):
        """折叠时弱化表现 (降低亮度)"""
        try:
            import colorsys
            # 将 hex 转为更暗版本
            hex_color = self.accent_color.lstrip('#')
            r = int(hex_color[0:2], 16) / 255
            g = int(hex_color[2:4], 16) / 255
            b = int(hex_color[4:6], 16) / 255
            h, l, s = colorsys.rgb_to_hls(r, g, b)
            l = max(0, l * 0.55)
            weakened = colorsys.hls_to_rgb(h, l, s * 0.85)
            wr, wg, wb = [int(x * 255) for x in weakened]
            dim_hex = f"#{wr:02X}{wg:02X}{wb:02X}"
            self.neon_bar.configure(fg_color=dim_hex)
            self.configure(border_color=dim_hex)
            lbl = getattr(self, '_title_label', None)
            if lbl is not None:
                try:
                    lbl.configure(text_color=dim_hex)
                except Exception:
                    pass
        except Exception:
            pass

    def restore(self):
        try:
            self.neon_bar.configure(fg_color=self.accent_color)
            self.configure(border_color=self.accent_color)
        except Exception:
            pass

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
        
    def _on_enter(self, event=None):
        """悬停时的发光效果"""
        self._is_hovering = True
        self.configure(
            border_color=self.glow_color,
            border_width=2
        )
        # 启动发光动画
        self._start_hover_glow()
        
    def _on_leave(self, event=None):
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
        
        # 移除持续闪烁动画，保留悬停反馈
        
    def _start_continuous_glow(self):  # 保留兼容空实现
        return

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
        
        # 移除发光动画 (降低 CPU)
        
    def _start_glow_animation(self):  # 兼容空实现
        return
    
    def set_glow_color(self, color: str):
        """更新边框颜色以模拟发光色切换"""
        try:
            self.configure(border_color=color)
        except Exception:
            pass


class EnhancedEntry(ctk.CTkEntry):
    """增强的输入框组件 - 带聚焦动画和发光效果"""
    
    def __init__(self, parent, **kwargs):
        # 默认的现代化输入框样式
        enhanced_kwargs = {
            'corner_radius': 10,
            'border_width': 1,
            'border_color': Colors.BORDER,
            'fg_color': Colors.SURFACE_LIGHT,
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
            fg_color=Colors.SURFACE_LIGHT
        )
        
    def _on_enter(self, event=None):
        """鼠标悬停时的微妙效果"""
        if not self._is_focused:
            self.configure(
                border_color=Colors.PRIMARY_LIGHT,
                fg_color=Colors.SURFACE_HOVER
            )
            
    def _on_leave(self, event=None):
        """鼠标离开时恢复（如果未聚焦）"""
        if not self._is_focused:
            self.configure(
                border_color=self._original_border_color,
                fg_color=Colors.SURFACE_LIGHT
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
    """（已改为非折叠）统一段落容器

    之前具备展开/折叠，现在需求：全部默认展开且无折叠交互。
    保留左侧竖条与标题风格，去除箭头与事件绑定。
    """
    def __init__(self, parent, title: str, accent_color: str | None = None, **kwargs):
        kwargs.update({
            'corner_radius': 10,
            'fg_color': Colors.SURFACE_LIGHT,
            'border_width': 1,
            'border_color': Colors.BORDER_LIGHT
        })
        super().__init__(parent, **kwargs)
        self.accent_color = accent_color or Colors.PRIMARY
        self._neutral_color = getattr(Colors, 'N300', Colors.BORDER_LIGHT)
        self.is_expanded = True  # 永久展开

        # 左侧霓虹条
        self.neon_bar = ctk.CTkFrame(self, width=2, fg_color=self._neutral_color, corner_radius=2)
        self.neon_bar.pack(side='left', fill='y', padx=(0, 8))

        # 内层主体容器
        self.inner = ctk.CTkFrame(self, fg_color='transparent')
        self.inner.pack(side='left', fill='x', expand=True, padx=8, pady=8)

        # 标题栏
        self.header_frame = ctk.CTkFrame(self.inner, fg_color='transparent')
        self.header_frame.pack(fill='x', pady=(0, 8))

        # 标题文本
        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text=title,
            font=getattr(Fonts, 'H4', getattr(Fonts, 'H3', Fonts.H2)),
            text_color=Colors.TEXT_PRIMARY
        )
        self.title_label.pack(side='left')

        # 内容框架
        self.content = ctk.CTkFrame(self.inner, fg_color='transparent')
        self.content.pack(fill='x', expand=True)

        # 激活状态
        try:
            self.neon_bar.configure(fg_color=self.accent_color)
        except Exception:
            pass

    def add_content(self, setup_func):
        """添加内容（直接展现，无折叠逻辑）"""
        # 清理旧内容
        for w in self.content.winfo_children():
            try: w.destroy()
            except Exception: pass
        # 添加新内容
        setup_func(self.content)
        return self.content


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
        """添加按钮 (支持 variant: primary|secondary|accent|danger|outline)"""
        style_map = {
            'primary': Style.BUTTON_PRIMARY,
            'secondary': Style.BUTTON_SECONDARY,
            'accent': Style.BUTTON_ACCENT,
            'danger': Style.BUTTON_DANGER,
            'outline': Style.BUTTON_OUTLINE,
            'silver': getattr(Style, 'BUTTON_SILVER', Style.BUTTON_SECONDARY),
        }
        # 'accent_alt' is deprecated, fallback to 'accent'
        if variant == 'accent_alt':
            variant = 'accent'
        
        style = style_map.get(variant, Style.BUTTON_PRIMARY).copy()
        # 对比度自动校正
        fg = style.get('fg_color', Colors.PRIMARY)
        # 统一使用 ensure_contrast
        try:
            style['text_color'] = ensure_contrast(fg)
        except Exception:
            style['text_color'] = Colors.TEXT_LIGHT
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
