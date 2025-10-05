"""Минималистичный оверлей 2025."""

import tkinter as tk
from tkinter import font as tkfont
from typing import Optional, Callable
from enum import Enum
import logging
import math

logger = logging.getLogger(__name__)


class OverlayPosition(Enum):
    """Позиции оверлея."""
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"


class OverlayGUI:
    """Минималистичный оверлей с анимациями."""

    def __init__(
        self,
        position: str = "top-right",
        alpha: float = 0.95,
        width: int = 300,
        height: int = 130,
        always_on_top: bool = True,
        theme: str = "dark"
    ):
        """
        Инициализация оверлея.

        Args:
            position: Позиция на экране
            alpha: Прозрачность (0.0-1.0)
            width: Ширина окна
            height: Высота окна
            always_on_top: Всегда поверх других окон
            theme: Тема оформления
        """
        self.root = tk.Tk()
        self.width = width
        self.height = height
        self.alpha = alpha
        self.always_on_top = always_on_top

        # Настройка окна
        self.root.title("Gamepad Recorder")
        self.root.attributes('-alpha', alpha)
        self.root.overrideredirect(True)

        if always_on_top:
            self.root.attributes('-topmost', True)

        # Позиционирование
        self._set_position(position)

        # Цветовая схема
        self._load_theme(theme)

        # Canvas для рисования
        self.canvas = tk.Canvas(
            self.root,
            width=width,
            height=height,
            bg=self.card_bg,
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Современные шрифты
        self.title_font = tkfont.Font(family="Segoe UI", size=14, weight="bold")
        self.slot_font = tkfont.Font(family="Segoe UI", size=22, weight="bold")
        self.label_font = tkfont.Font(family="Segoe UI", size=9)
        self.status_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        self.count_font = tkfont.Font(family="Segoe UI", size=18, weight="bold")
        self.hint_font = tkfont.Font(family="Segoe UI", size=7)

        # Состояние
        self.current_status = "idle"
        self.current_slot = 1
        self.event_count = 0
        self.slot_name = ""
        self.close_requested = False

        # Анимация
        self.animation_frame = 0
        self.pulse_alpha = 0.0

        # Оптимизация обновлений
        self._update_scheduled = False
        self._last_update_data = None

        # Временное сообщение
        self._message_id: Optional[int] = None
        self._message_after_id: Optional[str] = None

        # Перетаскивание
        self.canvas.bind('<Button-1>', self._start_move)
        self.canvas.bind('<B1-Motion>', self._do_move)
        self.canvas.bind('<Double-Button-1>', self._on_close)
        self.canvas.bind('<Button-3>', self._show_context_menu)
        self.offset_x = 0
        self.offset_y = 0

        # Callback
        self.on_close: Optional[Callable] = None

        # Начальная отрисовка
        self.draw_ui()
        self._start_animation()

    def _set_position(self, position: str) -> None:
        """Установить позицию окна."""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        margin = 20

        positions = {
            "top-right": (screen_width - self.width - margin, margin),
            "top-left": (margin, margin),
            "bottom-right": (screen_width - self.width - margin, screen_height - self.height - margin),
            "bottom-left": (margin, screen_height - self.height - margin)
        }

        x, y = positions.get(position, positions["top-right"])
        self.root.geometry(f'{self.width}x{self.height}+{x}+{y}')

    def _load_theme(self, theme: str) -> None:
        """Загрузить цветовую схему."""
        themes = {
            "dark": {
                "card_bg": "#1a1a1a",
                "text": "#ffffff",
                "text_secondary": "#a0a0a0",
                "text_dim": "#6b6b6b",
                "accent_idle": "#60a5fa",
                "accent_recording": "#f87171",
                "accent_playing": "#34d399",
                "accent_message": "#fbbf24",
                "border": "#2a2a2a"
            },
            "light": {
                "card_bg": "#ffffff",
                "text": "#1a1a1a",
                "text_secondary": "#525252",
                "text_dim": "#a3a3a3",
                "accent_idle": "#3b82f6",
                "accent_recording": "#ef4444",
                "accent_playing": "#10b981",
                "accent_message": "#f59e0b",
                "border": "#d4d4d4"
            }
        }

        colors = themes.get(theme, themes["dark"])
        self.card_bg = colors["card_bg"]
        self.text_color = colors["text"]
        self.text_secondary = colors["text_secondary"]
        self.text_dim = colors["text_dim"]
        self.accent_idle = colors["accent_idle"]
        self.accent_recording = colors["accent_recording"]
        self.accent_playing = colors["accent_playing"]
        self.accent_message = colors["accent_message"]
        self.border_color = colors["border"]

    def _start_animation(self) -> None:
        """Запустить анимацию."""
        def animate():
            if self.current_status in ["recording", "playing"]:
                self.animation_frame = (self.animation_frame + 1) % 60
                self.pulse_alpha = (math.sin(self.animation_frame * 0.1) + 1) / 2
                self.draw_ui()

            self.root.after(50, animate)

        animate()

    def draw_ui(self) -> None:
        """Отрисовать минималистичный интерфейс."""
        self.canvas.delete("ui")

        # Определение цвета и текста статуса
        status_map = {
            "recording": (self.accent_recording, "RECORDING", "🔴"),
            "playing": (self.accent_playing, "PLAYING", "▶️"),
            "idle": (self.accent_idle, "READY", "⏸️")
        }
        accent, status_text, icon = status_map.get(self.current_status, (self.accent_idle, "READY", "⏸️"))

        # Фон
        self.canvas.create_rectangle(
            0, 0, self.width, self.height,
            fill=self.card_bg,
            outline="",
            tags="ui"
        )

        # Рамка
        border_width = 2
        if self.current_status in ["recording", "playing"]:
            # Пульсирующая рамка
            border_width = int(2 + self.pulse_alpha * 1)
            border_color = self._blend_color(accent, self.card_bg, 0.6 + self.pulse_alpha * 0.4)
        else:
            border_color = self.border_color

        self.canvas.create_rectangle(
            0, 0, self.width, self.height,
            fill="",
            outline=border_color,
            width=border_width,
            tags="ui"
        )

        # Цветная полоска сверху
        bar_height = 3
        if self.current_status in ["recording", "playing"]:
            alpha_factor = 0.7 + (self.pulse_alpha * 0.3)
            bar_color = self._blend_color(accent, self.card_bg, alpha_factor)
        else:
            bar_color = accent

        self.canvas.create_rectangle(
            0, 0, self.width, bar_height,
            fill=bar_color,
            outline="",
            tags="ui"
        )

        # Отступы
        padding = 15

        # === ВЕРХНЯЯ СЕКЦИЯ: Статус ===
        header_y = 22

        # Иконка + статус
        self.canvas.create_text(
            padding, header_y,
            text=f"{icon} {status_text}",
            font=self.status_font,
            fill=accent,
            anchor="w",
            tags="ui"
        )

        # === СРЕДНЯЯ СЕКЦИЯ: Слот и События ===
        middle_y = 60

        # SLOT
        self.canvas.create_text(
            padding, middle_y - 10,
            text="SLOT",
            font=self.hint_font,
            fill=self.text_dim,
            anchor="w",
            tags="ui"
        )

        slot_text = f"#{self.current_slot}"
        if self.slot_name:
            display_name = self.slot_name[:15] + "..." if len(self.slot_name) > 15 else self.slot_name
            slot_text += f" {display_name}"

        self.canvas.create_text(
            padding, middle_y + 8,
            text=slot_text,
            font=self.slot_font,
            fill=self.text_color,
            anchor="w",
            tags="ui"
        )

        # EVENTS (справа)
        self.canvas.create_text(
            self.width - padding, middle_y - 10,
            text="EVENTS",
            font=self.hint_font,
            fill=self.text_dim,
            anchor="e",
            tags="ui"
        )

        self.canvas.create_text(
            self.width - padding, middle_y + 8,
            text=str(self.event_count),
            font=self.count_font,
            fill=accent,
            anchor="e",
            tags="ui"
        )

        # === НИЖНЯЯ СЕКЦИЯ ===
        footer_y = self.height - 12

        # Разделитель
        self.canvas.create_line(
            padding, footer_y - 10,
            self.width - padding, footer_y - 10,
            fill=self.border_color,
            width=1,
            tags="ui"
        )

        # Подсказка
        hint_text = "Double-click to close • Right-click menu"
        self.canvas.create_text(
            self.width // 2, footer_y,
            text=hint_text,
            font=self.hint_font,
            fill=self.text_dim,
            anchor="center",
            tags="ui"
        )

    def _blend_color(self, color1: str, color2: str, alpha: float) -> str:
        """Смешать два цвета."""
        try:
            r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
            r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)

            r = int(r1 * alpha + r2 * (1 - alpha))
            g = int(g1 * alpha + g2 * (1 - alpha))
            b = int(b1 * alpha + b2 * (1 - alpha))

            return f'#{r:02x}{g:02x}{b:02x}'
        except:
            return color1

    def update_status(
        self,
        status: str,
        slot: Optional[int] = None,
        event_count: Optional[int] = None,
        slot_name: Optional[str] = None
    ) -> None:
        """Обновить статус."""
        if status is not None:
            self.current_status = status
        if slot is not None:
            self.current_slot = slot
        if event_count is not None:
            self.event_count = event_count
        if slot_name is not None:
            self.slot_name = slot_name

        current_data = (self.current_status, self.current_slot, self.event_count, self.slot_name)
        if current_data == self._last_update_data:
            return

        self._last_update_data = current_data

        if not self._update_scheduled:
            self._update_scheduled = True
            self.root.after(0, self._do_update)

    def _do_update(self) -> None:
        """Выполнить отложенное обновление."""
        self._update_scheduled = False
        self.draw_ui()

    def show_message(self, message: str, duration: int = 2000) -> None:
        """Показать уведомление."""
        if self._message_after_id:
            self.root.after_cancel(self._message_after_id)

        if self._message_id:
            self.canvas.delete(self._message_id)

        # Фон
        bg_id = self.canvas.create_rectangle(
            15, self.height // 2 - 18,
            self.width - 15, self.height // 2 + 18,
            fill=self.card_bg,
            outline=self.accent_message,
            width=2,
            tags="message"
        )

        # Текст
        self._message_id = self.canvas.create_text(
            self.width // 2, self.height // 2,
            text=message,
            font=tkfont.Font(family="Segoe UI", size=11, weight="bold"),
            fill=self.accent_message,
            anchor="center",
            tags="message"
        )

        def hide_message():
            self.canvas.delete("message")
            self._message_id = None
            self._message_after_id = None

        self._message_after_id = self.root.after(duration, hide_message)

    def _show_context_menu(self, event: tk.Event) -> None:
        """Контекстное меню."""
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Toggle Always On Top", command=self.toggle_topmost)
        menu.add_separator()
        menu.add_command(label="Close", command=self._on_close)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def toggle_topmost(self) -> None:
        """Переключить 'всегда поверх'."""
        self.always_on_top = not self.always_on_top
        self.root.attributes('-topmost', self.always_on_top)

        status = "enabled" if self.always_on_top else "disabled"
        self.show_message(f"Always on top {status}")
        logger.info(f"Always on top: {self.always_on_top}")

    def set_alpha(self, alpha: float) -> None:
        """Установить прозрачность."""
        self.alpha = max(0.0, min(1.0, alpha))
        self.root.attributes('-alpha', self.alpha)

    def _start_move(self, event: tk.Event) -> None:
        """Начать перетаскивание."""
        self.offset_x = event.x
        self.offset_y = event.y

    def _do_move(self, event: tk.Event) -> None:
        """Перетащить окно."""
        x = self.root.winfo_x() + event.x - self.offset_x
        y = self.root.winfo_y() + event.y - self.offset_y
        self.root.geometry(f'+{x}+{y}')

    def _on_close(self, event: Optional[tk.Event] = None) -> None:
        """Обработать закрытие."""
        self.close_requested = True
        if self.on_close:
            self.on_close()
        self.root.quit()

    def update(self) -> None:
        """Обновить окно."""
        try:
            self.root.update()
        except tk.TclError:
            pass

    def destroy(self) -> None:
        """Уничтожить окно."""
        try:
            self.root.destroy()
        except:
            pass
