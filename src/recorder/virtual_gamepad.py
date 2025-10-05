"""Управление виртуальным геймпадом через vgamepad."""

import logging
from typing import Optional
from .gamepad_state import GamepadState

logger = logging.getLogger(__name__)

try:
    import vgamepad as vg
    VGAMEPAD_AVAILABLE = True
except ImportError:
    VGAMEPAD_AVAILABLE = False
    logger.warning("vgamepad не установлен - воспроизведение недоступно")


class VirtualGamepad:
    """Обертка над vgamepad с обработкой ошибок."""

    # Маппинг кнопок pygame -> Xbox
    BUTTON_MAP = {
        0: 'XUSB_GAMEPAD_A',
        1: 'XUSB_GAMEPAD_B',
        2: 'XUSB_GAMEPAD_X',
        3: 'XUSB_GAMEPAD_Y',
        4: 'XUSB_GAMEPAD_LEFT_SHOULDER',
        5: 'XUSB_GAMEPAD_RIGHT_SHOULDER',
        6: 'XUSB_GAMEPAD_BACK',
        7: 'XUSB_GAMEPAD_START',
        8: 'XUSB_GAMEPAD_LEFT_THUMB',
        9: 'XUSB_GAMEPAD_RIGHT_THUMB',
    }

    def __init__(self, invert_left_stick_y: bool = True):
        self.gamepad: Optional[vg.VX360Gamepad] = None
        self.available = VGAMEPAD_AVAILABLE
        self.invert_left_stick_y = invert_left_stick_y
        self._initialize()

    def _initialize(self) -> None:
        """Инициализировать виртуальный геймпад."""
        if not self.available:
            logger.error("vgamepad недоступен")
            return

        try:
            self.gamepad = vg.VX360Gamepad()
            logger.info("Виртуальный геймпад создан успешно")
        except Exception as e:
            logger.error(f"Ошибка создания виртуального геймпада: {e}")
            self.available = False
            self.gamepad = None

    def apply_state(self, state: GamepadState) -> bool:
        """
        Применить состояние к виртуальному геймпаду.

        Args:
            state: Состояние для применения

        Returns:
            True если успешно
        """
        if not self.available or not self.gamepad:
            return False

        try:
            # Сброс всех кнопок
            for button_name in self.BUTTON_MAP.values():
                button = getattr(vg.XUSB_BUTTON, button_name)
                self.gamepad.release_button(button=button)

            # Установка нажатых кнопок
            for i, pressed in enumerate(state.buttons):
                if pressed and i in self.BUTTON_MAP:
                    button = getattr(vg.XUSB_BUTTON, self.BUTTON_MAP[i])
                    self.gamepad.press_button(button=button)

            # Левый стик
            if len(state.axes) >= 2:
                y_value = state.axes[1]
                # Инвертируем Y если нужно (для совместимости с разными геймпадами)
                if self.invert_left_stick_y:
                    y_value = -y_value
                self.gamepad.left_joystick(
                    x_value=int(state.axes[0] * 32767),
                    y_value=int(y_value * 32767)
                )

            # Правый стик
            if len(state.axes) >= 4:
                self.gamepad.right_joystick(
                    x_value=int(state.axes[2] * 32767),
                    y_value=int(state.axes[3] * 32767)
                )

            # Триггеры (значения от -1 до 1, преобразуем в 0-255)
            if len(state.axes) >= 5:
                self.gamepad.left_trigger(value=int((state.axes[4] + 1) * 127.5))
            if len(state.axes) >= 6:
                self.gamepad.right_trigger(value=int((state.axes[5] + 1) * 127.5))

            # D-pad
            if state.hats and len(state.hats) > 0:
                hat_x, hat_y = state.hats[0]
                if hat_y == 1:
                    self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
                elif hat_y == -1:
                    self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
                if hat_x == -1:
                    self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
                elif hat_x == 1:
                    self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)

            # Отправка обновления
            self.gamepad.update()
            return True

        except Exception as e:
            logger.error(f"Ошибка применения состояния: {e}")
            return False

    def reset(self) -> bool:
        """
        Сбросить виртуальный геймпад в нейтральное состояние.

        Returns:
            True если успешно
        """
        if not self.available or not self.gamepad:
            return False

        try:
            self.gamepad.reset()
            self.gamepad.update()
            logger.debug("Виртуальный геймпад сброшен")
            return True
        except Exception as e:
            logger.error(f"Ошибка сброса виртуального геймпада: {e}")
            return False

    def __del__(self):
        """Очистка при удалении объекта."""
        if self.gamepad:
            try:
                self.reset()
            except:
                pass
