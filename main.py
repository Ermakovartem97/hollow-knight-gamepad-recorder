"""
Hollow Knight Gamepad Recorder v2.0
Приложение для записи и воспроизведения действий геймпада.
"""

import sys
import pygame
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config_manager import ConfigManager
from logger_config import setup_logging
from recorder.gamepad_recorder import GamepadRecorder, RecorderState
from ui.overlay_gui import OverlayGUI

logger = logging.getLogger(__name__)


class GamepadRecorderApp:
    """Main application."""

    def __init__(self):
        # Load configuration
        self.config = ConfigManager()

        # Setup logging
        log_config = self.config.get('logging', {})
        setup_logging(
            level=log_config.get('level', 'INFO'),
            log_file=log_config.get('file'),
            console=log_config.get('console', True),
            max_bytes=log_config.get('max_file_size', 10485760),
            backup_count=log_config.get('backup_count', 3)
        )

        logger.info("=" * 60)
        logger.info("Hollow Knight Gamepad Recorder v2.0")
        logger.info("=" * 60)

        # Create recorder
        gamepad_config = self.config.get('gamepad', {})
        recording_config = self.config.get('recording', {})

        self.recorder = GamepadRecorder(
            record_button=gamepad_config.get('record_button', 8),
            play_button=gamepad_config.get('play_button', 9),
            stick_deadzone=gamepad_config.get('stick_deadzone', 0.1),
            trigger_deadzone=gamepad_config.get('trigger_deadzone', 0.05),
            interference_threshold=gamepad_config.get('interference_threshold', 0.2),
            max_slots=recording_config.get('max_slots', 30),
            max_events=recording_config.get('max_events_per_slot', 100000),
            recordings_dir=recording_config.get('recordings_dir', 'recordings'),
            invert_left_stick_y=gamepad_config.get('invert_left_stick_y', True),
            quantize_sticks=gamepad_config.get('quantize_sticks', True),
            auto_save=recording_config.get('auto_save', True)
        )

        # GUI
        self.gui: OverlayGUI | None = None
        ui_config = self.config.get('ui', {})

        if ui_config.get('overlay_enabled', True):
            self.gui = OverlayGUI(
                position=ui_config.get('overlay_position', 'top-right'),
                alpha=ui_config.get('overlay_alpha', 0.92),
                width=ui_config.get('overlay_width', 200),
                height=ui_config.get('overlay_height', 70),
                always_on_top=ui_config.get('always_on_top', True),
                theme=ui_config.get('theme', 'dark')
            )

            # Bind callbacks
            self.recorder.on_state_change = self._on_state_change
            self.recorder.on_slot_change = self._on_slot_change
            self.recorder.on_error = self._on_error
            self.gui.on_close = self._on_gui_close

        # Settings
        self.playback_config = self.config.get('playback', {})
        self.hotkeys = self.config.get('hotkeys', {})
        self.auto_save = recording_config.get('auto_save', True)
        self.backup_on_save = recording_config.get('backup_on_save', True)

        # Flags
        self.running = True
        self.ui_update_counter = 0
        self.ui_update_rate = ui_config.get('update_rate', 10)

    def _on_state_change(self, state: RecorderState, slot: int, event_count: int) -> None:
        """State change handler."""
        if not self.gui:
            return

        status_map = {
            RecorderState.IDLE: "idle",
            RecorderState.RECORDING: "recording",
            RecorderState.PLAYING: "playing"
        }

        # Get slot name
        meta = self.recorder.sequence_manager.get_metadata(slot)
        slot_name = meta.name if meta else ""

        self.gui.update_status(
            status=status_map.get(state, "idle"),
            slot=slot,
            event_count=event_count,
            slot_name=slot_name
        )

        # Messages
        if state == RecorderState.IDLE and event_count > 0:
            self.gui.show_message(f"💾 {event_count} events")
        elif state == RecorderState.RECORDING:
            self.gui.show_message("🔴 Recording...")
        elif state == RecorderState.PLAYING:
            self.gui.show_message("▶️ Playing...")

    def _on_slot_change(self, slot: int, event_count: int) -> None:
        """Slot change handler."""
        if not self.gui:
            return

        meta = self.recorder.sequence_manager.get_metadata(slot)
        slot_name = meta.name if meta else ""

        self.gui.update_status(
            status="idle",
            slot=slot,
            event_count=event_count,
            slot_name=slot_name
        )

    def _on_error(self, message: str) -> None:
        """Error handler."""
        logger.error(message)
        if self.gui:
            self.gui.show_message(f"❌ {message}")

    def _on_gui_close(self) -> None:
        """GUI close handler."""
        self.running = False

    def _process_keyboard_input(self) -> None:
        """Process keyboard input."""
        for event in pygame.event.get():
            if event.type != pygame.KEYDOWN:
                continue

            key = pygame.key.name(event.key)

            # Save
            if key == self.hotkeys.get('save', 's'):
                self._save_sequences()

            # Load
            elif key == self.hotkeys.get('load', 'l'):
                self._load_sequences()

            # Quit
            elif key == self.hotkeys.get('quit', 'q'):
                self.running = False

            # Toggle overlay
            elif key == self.hotkeys.get('toggle_overlay', 'o') and self.gui:
                # Hide/show (change alpha)
                new_alpha = 0.0 if self.gui.alpha > 0.1 else 0.92
                self.gui.set_alpha(new_alpha)
                logger.info(f"Overlay alpha: {new_alpha}")

            # Toggle topmost
            elif key == self.hotkeys.get('toggle_topmost', 't') and self.gui:
                self.gui.toggle_topmost()

            # Quick slot select (1-9)
            elif key.isdigit():
                slot = int(key)
                if 1 <= slot <= 9:
                    self.recorder.goto_slot(slot)

    def _save_sequences(self) -> None:
        """Save sequences."""
        success = self.recorder.sequence_manager.save_to_file(
            backup=self.backup_on_save
        )

        if success:
            logger.info("Sequences saved")
            if self.gui:
                self.gui.show_message("💾 Saved!")
        else:
            logger.error("Save failed")
            if self.gui:
                self.gui.show_message("❌ Save failed")

    def _load_sequences(self) -> None:
        """Load sequences."""
        success = self.recorder.sequence_manager.load_from_file()

        if success:
            logger.info("Sequences loaded")
            if self.gui:
                # Update current slot display
                count = len(self.recorder.sequence_manager.get_sequence(self.recorder.current_slot))
                meta = self.recorder.sequence_manager.get_metadata(self.recorder.current_slot)

                self.gui.update_status(
                    status="idle",
                    slot=self.recorder.current_slot,
                    event_count=count,
                    slot_name=meta.name if meta else ""
                )
                self.gui.show_message("📂 Loaded!")
        else:
            logger.error("Load failed")
            if self.gui:
                self.gui.show_message("❌ Load failed")

    def run(self) -> int:
        """
        Start application.

        Returns:
            Exit code (0 = success)
        """
        # Initialize gamepad
        if not self.recorder.initialize_joystick():
            logger.error("Failed to initialize gamepad")
            return 1

        # Auto-load
        if self.auto_save:
            if self.recorder.sequence_manager.load_from_file():
                # Update GUI with loaded data
                if self.gui:
                    count = len(self.recorder.sequence_manager.get_sequence(self.recorder.current_slot))
                    meta = self.recorder.sequence_manager.get_metadata(self.recorder.current_slot)
                    self.gui.update_status(
                        status="idle",
                        slot=self.recorder.current_slot,
                        event_count=count,
                        slot_name=meta.name if meta else ""
                    )

        # Print info
        logger.info("")
        logger.info("📋 Controls:")
        logger.info(f"  🔴 Record: L3 (button {self.recorder.record_button})")
        logger.info(f"  ▶️  Playback: R3 (button {self.recorder.play_button})")
        logger.info(f"  ⬆️⬇️  Slots: D-pad")
        logger.info(f"  💾 Save: '{self.hotkeys.get('save', 's')}'")
        logger.info(f"  📂 Load: '{self.hotkeys.get('load', 'l')}'")
        logger.info(f"  👁️  Toggle overlay: '{self.hotkeys.get('toggle_overlay', 'o')}'")
        logger.info(f"  📌 Toggle topmost: '{self.hotkeys.get('toggle_topmost', 't')}'")
        logger.info(f"  1-9: Quick slot select")
        logger.info(f"  ❌ Quit: '{self.hotkeys.get('quit', 'q')}' or double-click")
        logger.info("")
        logger.info(f"Current slot: {self.recorder.current_slot}")
        logger.info("Application started!")

        # Main loop
        clock = pygame.time.Clock()
        polling_rate = self.config.get('gamepad.polling_rate', 100)

        while self.running:
            # Process input
            self.recorder.process_input()
            self._process_keyboard_input()

            # Update GUI (at lower rate)
            if self.gui:
                self.ui_update_counter += 1
                if self.ui_update_counter >= polling_rate // self.ui_update_rate:
                    self.gui.update()
                    self.ui_update_counter = 0

                if self.gui.close_requested:
                    self.running = False

            # FPS limit
            clock.tick(polling_rate)

        # Cleanup
        logger.info("Shutting down...")

        # Stop recording/playback if active
        if self.recorder.state == RecorderState.RECORDING:
            self.recorder.stop_recording()
        elif self.recorder.state == RecorderState.PLAYING:
            self.recorder.stop_playback()

        # Auto-save
        if self.auto_save:
            self._save_sequences()

        self.recorder.cleanup()

        if self.gui:
            self.gui.destroy()

        logger.info("Application closed")
        return 0


def main() -> int:
    """Entry point."""
    try:
        app = GamepadRecorderApp()
        return app.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.exception(f"Critical error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
