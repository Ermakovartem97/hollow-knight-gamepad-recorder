"""Работа с состоянием геймпада."""

from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class GamepadState:
    """Состояние геймпада в определенный момент времени."""

    buttons: List[bool] = field(default_factory=list)
    axes: List[float] = field(default_factory=list)
    hats: List[Tuple[int, int]] = field(default_factory=list)

    def __eq__(self, other: object) -> bool:
        """Сравнение состояний с учетом округления осей."""
        if not isinstance(other, GamepadState):
            return False

        # Сравнение кнопок
        if self.buttons != other.buttons:
            return False

        # Сравнение осей с порогом 0.08 (8% от диапазона)
        # Это фильтрует мелкие дрожания стика при записи
        if len(self.axes) != len(other.axes):
            return False
        for a, b in zip(self.axes, other.axes):
            if abs(a - b) > 0.08:
                return False

        # Сравнение hat-ов
        if self.hats != other.hats:
            return False

        return True

    def apply_deadzone(
        self,
        stick_deadzone: float = 0.1,
        trigger_deadzone: float = 0.05,
        quantize_sticks: bool = False
    ) -> 'GamepadState':
        """
        Применить dead zone к осям.

        Args:
            stick_deadzone: Мертвая зона для стиков (оси 0-3)
            trigger_deadzone: Мертвая зона для триггеров (оси 4-5)
            quantize_sticks: Квантовать стики до -1.0, 0.0, 1.0 (для точного воспроизведения)

        Returns:
            Новое состояние с примененными dead zones
        """
        new_axes = []

        for i, value in enumerate(self.axes):
            # Стики (обычно оси 0-3)
            if i < 4:
                deadzone = stick_deadzone
                # Применяем dead zone
                if abs(value) < deadzone:
                    new_axes.append(0.0)
                else:
                    # Масштабируем значение после dead zone
                    sign = 1 if value > 0 else -1
                    scaled = (abs(value) - deadzone) / (1.0 - deadzone)

                    # Квантование для детерминированного воспроизведения
                    if quantize_sticks:
                        # Порог 0.5: если стик наклонен > 50%, считаем полное нажатие
                        if scaled > 0.5:
                            new_axes.append(sign * 1.0)
                        else:
                            new_axes.append(0.0)
                    else:
                        new_axes.append(sign * scaled)
            # Триггеры (обычно оси 4-5)
            else:
                deadzone = trigger_deadzone
                # Применяем dead zone
                if abs(value) < deadzone:
                    new_axes.append(0.0)
                else:
                    # Масштабируем значение после dead zone
                    sign = 1 if value > 0 else -1
                    scaled = (abs(value) - deadzone) / (1.0 - deadzone)

                    # Квантование триггеров для детерминизма
                    if quantize_sticks:
                        # Для триггеров: 0.0 (не нажат) или 1.0/-1.0 (полностью нажат)
                        if scaled > 0.5:
                            new_axes.append(sign * 1.0)
                        else:
                            new_axes.append(0.0)
                    else:
                        new_axes.append(sign * scaled)

        return GamepadState(
            buttons=self.buttons.copy(),
            axes=new_axes,
            hats=self.hats.copy()
        )

    def has_significant_change(
        self,
        other: 'GamepadState',
        axis_threshold: float = 0.05
    ) -> bool:
        """
        Проверить, есть ли значительные изменения между состояниями.

        Args:
            other: Другое состояние для сравнения
            axis_threshold: Порог изменения осей

        Returns:
            True если есть значительные изменения
        """
        # Проверка кнопок
        if self.buttons != other.buttons:
            return True

        # Проверка осей
        if len(self.axes) != len(other.axes):
            return True

        for a, b in zip(self.axes, other.axes):
            if abs(a - b) > axis_threshold:
                return True

        # Проверка hat-ов
        if self.hats != other.hats:
            return True

        return False

    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь для сериализации."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GamepadState':
        """Создать из словаря."""
        return cls(
            buttons=data.get('buttons', []),
            axes=data.get('axes', []),
            hats=[tuple(h) for h in data.get('hats', [])]
        )

    def copy(self) -> 'GamepadState':
        """Создать копию состояния."""
        return GamepadState(
            buttons=self.buttons.copy(),
            axes=self.axes.copy(),
            hats=self.hats.copy()
        )
