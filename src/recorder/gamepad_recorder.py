"""Основной класс для записи и воспроизведения геймпада."""

import pygame
import time
import logging
from typing import Optional, Callable
from enum import Enum
from .gamepad_state import GamepadState
from .virtual_gamepad import VirtualGamepad
from .sequence_manager import SequenceManager, RecordingEvent

logger = logging.getLogger(__name__)


class RecorderState(Enum):
    """Состояния рекордера."""
    IDLE = "idle"
    RECORDING = "recording"
    PLAYING = "playing"


class GamepadRecorder:
    """Рекордер геймпада с поддержкой записи и воспроизведения."""

    def __init__(
        self,
        record_button: int = 8,
        play_button: int = 9,
        stick_deadzone: float = 0.1,
        trigger_deadzone: float = 0.05,
        interference_threshold: float = 0.2,
        max_slots: int = 30,
        max_events: int = 100000,
        recordings_dir: str = "recordings",
        invert_left_stick_y: bool = True,
        quantize_sticks: bool = True,
        auto_save: bool = True
    ):
        """
        Initialize recorder.

        Args:
            record_button: Button for recording (default L3)
            play_button: Button for playback (default R3)
            stick_deadzone: Stick deadzone
            trigger_deadzone: Trigger deadzone
            interference_threshold: Interference detection threshold
            max_slots: Maximum number of slots
            max_events: Maximum events per slot
            recordings_dir: Directory for recordings
            invert_left_stick_y: Invert left stick Y axis
            quantize_sticks: Quantize stick values
            auto_save: Auto-save recordings when updated
        """
        # Pygame
        pygame.init()
        pygame.joystick.init()

        # Components
        self.joystick: Optional[pygame.joystick.Joystick] = None
        self.virtual_gamepad = VirtualGamepad(invert_left_stick_y=invert_left_stick_y)
        self.sequence_manager = SequenceManager(
            max_slots=max_slots,
            max_events_per_slot=max_events,
            recordings_dir=recordings_dir,
            auto_save=auto_save
        )

        # Настройки
        self.record_button = record_button
        self.play_button = play_button
        self.stick_deadzone = stick_deadzone
        self.trigger_deadzone = trigger_deadzone
        self.interference_threshold = interference_threshold
        self.invert_left_stick_y = invert_left_stick_y
        self.quantize_sticks = quantize_sticks

        # Состояние
        self.state = RecorderState.IDLE
        self.current_slot = 1
        self.max_slots = max_slots

        # Данные записи
        self.recording_data: list[RecordingEvent] = []
        self.recording_start_time: float = 0.0
        self.recording_last_state: Optional[GamepadState] = None

        # Данные воспроизведения
        self.playback_index: int = 0
        self.playback_start_time: float = 0.0
        self.playback_initial_state: Optional[GamepadState] = None
        self.playback_loop: bool = False
        self.playback_loop_count: int = 0
        self.playback_max_loops: int = -1  # -1 = бесконечно
        self.playback_delays: list[float] = []  # Задержки для анализа

        # Debounce для кнопок
        self.button_states: dict[int, bool] = {}

        # Callback для обновления UI
        self.on_state_change: Optional[Callable] = None
        self.on_slot_change: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

    def initialize_joystick(self) -> bool:
        """
        Инициализировать физический геймпад.

        Returns:
            True если успешно
        """
        try:
            if pygame.joystick.get_count() == 0:
                logger.error("Геймпад не найден")
                if self.on_error:
                    self.on_error("Геймпад не найден")
                return False

            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()

            logger.info(
                f"Подключен геймпад: {self.joystick.get_name()}, "
                f"кнопок: {self.joystick.get_numbuttons()}, "
                f"осей: {self.joystick.get_numaxes()}"
            )
            return True

        except Exception as e:
            logger.error(f"Ошибка инициализации геймпада: {e}")
            if self.on_error:
                self.on_error(f"Ошибка геймпада: {e}")
            return False

    def get_current_state(self) -> Optional[GamepadState]:
        """
        Получить текущее состояние геймпада.

        Returns:
            Состояние геймпада или None при ошибке
        """
        if not self.joystick:
            return None

        try:
            state = GamepadState(
                buttons=[
                    self.joystick.get_button(i)
                    for i in range(self.joystick.get_numbuttons())
                ],
                axes=[
                    round(self.joystick.get_axis(i), 3)
                    for i in range(self.joystick.get_numaxes())
                ],
                hats=[
                    self.joystick.get_hat(i)
                    for i in range(self.joystick.get_numhats())
                ] if self.joystick.get_numhats() > 0 else []
            )

            # Применение dead zone
            return state.apply_deadzone(
                self.stick_deadzone,
                self.trigger_deadzone,
                self.quantize_sticks
            )

        except Exception as e:
            logger.error(f"Ошибка чтения состояния геймпада: {e}")
            return None

    def is_button_just_pressed(self, button_id: int) -> bool:
        """
        Проверить, была ли кнопка только что нажата (с debounce).

        Args:
            button_id: ID кнопки

        Returns:
            True если кнопка только что нажата
        """
        if not self.joystick:
            return False

        try:
            is_pressed = self.joystick.get_button(button_id)
            was_pressed = self.button_states.get(button_id, False)
            self.button_states[button_id] = is_pressed

            return is_pressed and not was_pressed

        except Exception as e:
            logger.error(f"Ошибка проверки кнопки {button_id}: {e}")
            return False

    def check_interference(self, initial_state: GamepadState) -> bool:
        """
        Проверить вмешательство пользователя.

        Args:
            initial_state: Начальное состояние для сравнения

        Returns:
            True если обнаружено вмешательство
        """
        current = self.get_current_state()
        if not current:
            return False

        try:
            # Проверка кнопок (кроме управляющих)
            for i, (initial_btn, current_btn) in enumerate(zip(initial_state.buttons, current.buttons)):
                if i in [self.record_button, self.play_button]:
                    continue

                if not initial_btn and current_btn:
                    logger.debug(f"Вмешательство: кнопка {i}")
                    return True

            # Проверка осей
            for i, (initial_axis, current_axis) in enumerate(zip(initial_state.axes, current.axes)):
                if abs(current_axis - initial_axis) > self.interference_threshold:
                    logger.debug(f"Вмешательство: ось {i}")
                    return True

            # Проверка hat-ов
            if initial_state.hats != current.hats:
                logger.debug("Вмешательство: D-pad")
                return True

            return False

        except Exception as e:
            logger.error(f"Ошибка проверки вмешательства: {e}")
            return False

    # === ЗАПИСЬ ===

    def start_recording(self) -> bool:
        """Начать запись."""
        if self.state != RecorderState.IDLE:
            logger.warning(f"Невозможно начать запись в состоянии {self.state}")
            return False

        self.state = RecorderState.RECORDING
        self.recording_data = []
        self.recording_last_state = None
        self.recording_start_time = time.time()

        logger.info(f"Начата запись в слот {self.current_slot}")

        if self.on_state_change:
            self.on_state_change(self.state, self.current_slot, 0)

        return True

    def update_recording(self) -> None:
        """Обновление записи (вызывается каждый кадр)."""
        if self.state != RecorderState.RECORDING:
            return

        current_state = self.get_current_state()
        if not current_state:
            return

        current_time = time.time() - self.recording_start_time

        # Записываем ВСЕ изменения без порога для максимальной точности
        # Критично для быстрых комбинаций (прыжок + вниз + атака за 10-20ms)
        if self.recording_last_state is None or current_state != self.recording_last_state:
            event = RecordingEvent(time=current_time, state=current_state)
            self.recording_data.append(event)

            # DEBUG: логируем изменения для диагностики (только в DEBUG режиме)
            if logger.isEnabledFor(logging.DEBUG) and self.recording_last_state:
                # Логируем только значимые изменения кнопок и осей
                for i, (old, new) in enumerate(zip(self.recording_last_state.buttons, current_state.buttons)):
                    if old != new:
                        logger.debug(f"[{current_time:.4f}s] BUTTON {i}: {old} -> {new}")
                for i, (old, new) in enumerate(zip(self.recording_last_state.axes, current_state.axes)):
                    if abs(old - new) > 0.01:
                        logger.debug(f"[{current_time:.4f}s] AXIS {i}: {old:.3f} -> {new:.3f}")

            self.recording_last_state = current_state

            # Периодически уведомляем UI
            if len(self.recording_data) % 10 == 0 and self.on_state_change:
                self.on_state_change(self.state, self.current_slot, len(self.recording_data))

            # Проверка переполнения
            if len(self.recording_data) >= self.sequence_manager.max_events_per_slot:
                logger.warning("Достигнут лимит событий, остановка записи")
                self.stop_recording()

    def stop_recording(self) -> bool:
        """Остановить запись."""
        if self.state != RecorderState.RECORDING:
            return False

        count = len(self.recording_data)
        success = self.sequence_manager.set_sequence(
            self.current_slot,
            self.recording_data
        )

        if success:
            logger.info(f"Запись остановлена: {count} событий")
        else:
            logger.error("Ошибка сохранения записи")

        self.state = RecorderState.IDLE

        if self.on_state_change:
            self.on_state_change(self.state, self.current_slot, count)

        return success

    def continue_recording(self, events_before: list[RecordingEvent], time_offset: float) -> None:
        """
        Продолжить запись после вмешательства.

        Args:
            events_before: События до вмешательства
            time_offset: Смещение времени
        """
        self.state = RecorderState.RECORDING
        self.recording_data = list(events_before)
        self.recording_last_state = events_before[-1].state if events_before else None
        self.recording_start_time = time.time() - time_offset

        logger.info(f"Продолжение записи (было {len(events_before)} событий)")

        if self.on_state_change:
            self.on_state_change(self.state, self.current_slot, len(events_before))

    # === ВОСПРОИЗВЕДЕНИЕ ===

    def start_playback(self, loop: bool = False, loop_count: int = -1) -> bool:
        """
        Начать воспроизведение.

        Args:
            loop: Включить зацикливание
            loop_count: Количество повторов (-1 = бесконечно)

        Returns:
            True если успешно
        """
        if self.state != RecorderState.IDLE:
            logger.warning(f"Невозможно начать воспроизведение в состоянии {self.state}")
            return False

        sequence = self.sequence_manager.get_sequence(self.current_slot)

        if not sequence:
            logger.warning(f"Слот {self.current_slot} пуст")
            if self.on_error:
                self.on_error("Нет записи в слоте")
            return False

        if not self.virtual_gamepad.available:
            logger.error("Виртуальный геймпад недоступен")
            if self.on_error:
                self.on_error("Виртуальный геймпад недоступен")
            return False

        # Разогрев виртуального геймпада для снижения начальной задержки
        # Сбрасываем геймпад несколько раз для "пробуждения" драйвера
        for _ in range(5):
            self.virtual_gamepad.reset()
            time.sleep(0.002)  # 2ms между сбросами

        # Дополнительная задержка перед началом воспроизведения
        # Это даёт драйверу время на стабилизацию и снижает задержку первого события
        time.sleep(0.05)  # 50ms задержка для стабилизации

        self.state = RecorderState.PLAYING
        self.playback_index = 0
        self.playback_start_time = time.time()
        self.playback_initial_state = self.get_current_state()
        self.playback_loop = loop
        self.playback_loop_count = 0
        self.playback_max_loops = loop_count
        self.playback_delays = []  # Сброс статистики

        logger.info(
            f"Начато воспроизведение слота {self.current_slot} "
            f"({len(sequence)} событий, зацикливание: {loop})"
        )

        if self.on_state_change:
            self.on_state_change(self.state, self.current_slot, len(sequence))

        return True

    def update_playback(self) -> None:
        """Обновление воспроизведения (вызывается каждый кадр)."""
        if self.state != RecorderState.PLAYING:
            return

        sequence = self.sequence_manager.get_sequence(self.current_slot)
        if not sequence:
            self.stop_playback()
            return

        current_time = time.time() - self.playback_start_time

        # Применяем все события, которые должны произойти
        # ВАЖНО: применяем ВСЕ пропущенные события сразу, чтобы сохранить интервалы
        events_applied = 0
        while self.playback_index < len(sequence):
            event = sequence[self.playback_index]

            # Если событие ещё не должно произойти, ждём
            if event.time > current_time:
                break

            # Собираем статистику задержек (всегда)
            delay_ms = (current_time - event.time) * 1000
            self.playback_delays.append(delay_ms)

            self.virtual_gamepad.apply_state(event.state)
            self.playback_index += 1
            events_applied += 1

        # Если применили несколько событий за один кадр, это нормально
        # Это сохраняет быстрые комбинации (например, нажатие и отпускание за 10ms)

        # Проверка завершения
        if self.playback_index >= len(sequence):
            # Добавляем задержку 0.2с после последнего события, чтобы персонаж успел завершить движение
            last_event_time = sequence[-1].time if sequence else 0
            time_since_last_event = current_time - last_event_time

            if time_since_last_event < 0.2:
                # Ждём завершения последнего движения
                return

            if self.playback_loop and (self.playback_max_loops == -1 or self.playback_loop_count < self.playback_max_loops):
                # Перезапуск
                self.playback_index = 0
                self.playback_start_time = time.time()
                self.playback_loop_count += 1
                logger.debug(f"Повтор #{self.playback_loop_count}")
            else:
                self.stop_playback("Завершено")
                return

        # Проверка остановки вручную (после 0.5 сек)
        if current_time > 0.5 and self.is_button_just_pressed(self.play_button):
            self.stop_playback("Остановлено вручную")
            return

        # Проверка вмешательства
        if self.playback_initial_state and self.check_interference(self.playback_initial_state):
            events_before = sequence[:self.playback_index]
            time_offset = current_time

            logger.info("Обнаружено вмешательство, переход к дозаписи")
            self.virtual_gamepad.reset()
            self.continue_recording(events_before, time_offset)

    def stop_playback(self, message: str = "Остановлено") -> None:
        """Остановить воспроизведение."""
        if self.state != RecorderState.PLAYING:
            return

        self.virtual_gamepad.reset()
        self.state = RecorderState.IDLE

        logger.info(f"Воспроизведение остановлено: {message}")

        # Статистика задержек (только в DEBUG режиме)
        if self.playback_delays and logger.isEnabledFor(logging.DEBUG):
            avg_delay = sum(self.playback_delays) / len(self.playback_delays)
            max_delay = max(self.playback_delays)
            min_delay = min(self.playback_delays)
            logger.debug(
                f"Timing stats: events={len(self.playback_delays)} "
                f"avg={avg_delay:+.2f}ms max={max_delay:+.2f}ms min={min_delay:+.2f}ms"
            )

        if self.on_state_change:
            count = len(self.sequence_manager.get_sequence(self.current_slot))
            self.on_state_change(self.state, self.current_slot, count)

    # === УПРАВЛЕНИЕ СЛОТАМИ ===

    def change_slot(self, delta: int) -> bool:
        """
        Изменить текущий слот.

        Args:
            delta: Смещение (+1 или -1)

        Returns:
            True если успешно
        """
        if self.state != RecorderState.IDLE:
            logger.debug("Смена слота возможна только в режиме IDLE")
            return False

        new_slot = self.current_slot + delta
        if new_slot < 1 or new_slot > self.max_slots:
            logger.debug(f"Слот {new_slot} вне диапазона")
            return False

        self.current_slot = new_slot
        logger.info(f"Переключение на слот {self.current_slot}")

        if self.on_slot_change:
            count = len(self.sequence_manager.get_sequence(self.current_slot))
            self.on_slot_change(self.current_slot, count)

        return True

    def goto_slot(self, slot: int) -> bool:
        """Перейти к конкретному слоту."""
        if slot < 1 or slot > self.max_slots:
            return False

        self.current_slot = slot
        logger.info(f"Переход к слоту {self.current_slot}")

        if self.on_slot_change:
            count = len(self.sequence_manager.get_sequence(self.current_slot))
            self.on_slot_change(self.current_slot, count)

        return True

    # === УПРАВЛЕНИЕ ===

    def process_input(self) -> None:
        """Обработка ввода (вызывается каждый кадр)."""
        if not self.joystick:
            return

        try:
            pygame.event.pump()

            if self.state == RecorderState.IDLE:
                self._process_idle_input()
            elif self.state == RecorderState.RECORDING:
                self._process_recording_input()
            elif self.state == RecorderState.PLAYING:
                self._process_playing_input()

        except Exception as e:
            logger.error(f"Ошибка обработки ввода: {e}")

    def _process_idle_input(self) -> None:
        """Обработка ввода в режиме IDLE."""
        # Запись
        if self.is_button_just_pressed(self.record_button):
            self.start_recording()

        # Воспроизведение
        elif self.is_button_just_pressed(self.play_button):
            self.start_playback()

        # Переключение слотов через D-pad
        if self.joystick and self.joystick.get_numhats() > 0:
            hat = self.joystick.get_hat(0)

            # Вверх
            if hat[1] == 1:
                if not self.button_states.get('hat_up', False):
                    self.change_slot(1)
                    self.button_states['hat_up'] = True
            else:
                self.button_states['hat_up'] = False

            # Вниз
            if hat[1] == -1:
                if not self.button_states.get('hat_down', False):
                    self.change_slot(-1)
                    self.button_states['hat_down'] = True
            else:
                self.button_states['hat_down'] = False

    def _process_recording_input(self) -> None:
        """Обработка ввода в режиме RECORDING."""
        if self.is_button_just_pressed(self.record_button):
            self.stop_recording()
        else:
            self.update_recording()

    def _process_playing_input(self) -> None:
        """Обработка ввода в режиме PLAYING."""
        self.update_playback()

    def cleanup(self) -> None:
        """Очистка ресурсов."""
        logger.info("Очистка ресурсов рекордера")

        if self.state == RecorderState.PLAYING:
            self.virtual_gamepad.reset()

        pygame.quit()
