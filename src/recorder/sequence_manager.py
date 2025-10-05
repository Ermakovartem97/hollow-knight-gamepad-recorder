"""Sequence recording management."""

import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from .gamepad_state import GamepadState

logger = logging.getLogger(__name__)


@dataclass
class RecordingEvent:
    """Recording event with timestamp."""
    time: float
    state: GamepadState

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'time': self.time,
            'state': self.state.to_dict()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'RecordingEvent':
        """Create from dictionary."""
        return cls(
            time=data['time'],
            state=GamepadState.from_dict(data['state'])
        )


@dataclass
class SlotMetadata:
    """Slot metadata."""
    name: str = ""
    created_at: Optional[str] = None
    modified_at: Optional[str] = None
    event_count: int = 0
    duration: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'SlotMetadata':
        return cls(**data)


class SequenceManager:
    """Sequence recording management with save/load support."""

    FILE_VERSION = "2.0.0"

    def __init__(
        self,
        max_slots: int = 30,
        max_events_per_slot: int = 100000,
        recordings_dir: str = "recordings",
        auto_save: bool = True
    ):
        self.max_slots = max_slots
        self.max_events_per_slot = max_events_per_slot
        self.recordings_dir = Path(recordings_dir)
        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        self.auto_save = auto_save

        # Sequences: {slot_id: List[RecordingEvent]}
        self.sequences: Dict[int, List[RecordingEvent]] = {
            i: [] for i in range(1, max_slots + 1)
        }

        # Slot metadata
        self.metadata: Dict[int, SlotMetadata] = {
            i: SlotMetadata() for i in range(1, max_slots + 1)
        }

    def get_sequence(self, slot: int) -> List[RecordingEvent]:
        """Get sequence for slot."""
        if slot not in self.sequences:
            logger.warning(f"Attempt to get non-existent slot {slot}")
            return []
        return self.sequences[slot]

    def set_sequence(
        self,
        slot: int,
        events: List[RecordingEvent],
        name: str = ""
    ) -> bool:
        """
        Set sequence for slot.

        Args:
            slot: Slot number
            events: Events
            name: Recording name

        Returns:
            True if successful
        """
        if slot not in self.sequences:
            logger.error(f"Invalid slot number: {slot}")
            return False

        if len(events) > self.max_events_per_slot:
            logger.error(f"Too many events: {len(events)} > {self.max_events_per_slot}")
            return False

        self.sequences[slot] = events

        # Update metadata
        now = datetime.now().isoformat()
        duration = events[-1].time if events else 0.0

        if not self.metadata[slot].created_at:
            self.metadata[slot].created_at = now

        self.metadata[slot].name = name or self.metadata[slot].name
        self.metadata[slot].modified_at = now
        self.metadata[slot].event_count = len(events)
        self.metadata[slot].duration = duration

        logger.info(f"Slot {slot} updated: {len(events)} events, {duration:.2f}s")

        # Auto-save immediately when recording is updated
        if self.auto_save and events:
            self.save_to_file(backup=False)

        return True

    def clear_slot(self, slot: int) -> bool:
        """Clear slot."""
        if slot not in self.sequences:
            return False

        self.sequences[slot] = []
        self.metadata[slot] = SlotMetadata()
        logger.info(f"Slot {slot} cleared")
        return True

    def get_metadata(self, slot: int) -> Optional[SlotMetadata]:
        """Get slot metadata."""
        return self.metadata.get(slot)

    def rename_slot(self, slot: int, name: str) -> bool:
        """Rename slot."""
        if slot not in self.metadata:
            return False

        self.metadata[slot].name = name
        logger.info(f"Slot {slot} renamed to '{name}'")
        return True

    def save_to_file(self, filename: str = "sequences.json", backup: bool = True) -> bool:
        """
        Save all sequences to file.

        Args:
            filename: File name
            backup: Create backup copy

        Returns:
            True if successful
        """
        filepath = self.recordings_dir / filename

        try:
            # Create backup
            if backup and filepath.exists():
                backup_path = self.recordings_dir / f"{filename}.backup"
                shutil.copy2(filepath, backup_path)
                logger.info(f"Backup created: {backup_path}")

            # Prepare data
            data = {
                'version': self.FILE_VERSION,
                'saved_at': datetime.now().isoformat(),
                'slots': {}
            }

            for slot_id, events in self.sequences.items():
                if events:  # Save only non-empty slots
                    data['slots'][str(slot_id)] = {
                        'metadata': self.metadata[slot_id].to_dict(),
                        'events': [event.to_dict() for event in events]
                    }

            # Save
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Sequences saved to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Save error: {e}")
            return False

    def load_from_file(self, filename: str = "sequences.json") -> bool:
        """
        Load sequences from file.

        Args:
            filename: File name

        Returns:
            True if successful
        """
        filepath = self.recordings_dir / filename

        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            return False

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Version validation
            file_version = data.get('version', '1.0.0')
            if not self._is_compatible_version(file_version):
                logger.error(f"Incompatible file version: {file_version}")
                return False

            # Load slots
            slots_data = data.get('slots', {})
            loaded_count = 0

            for slot_str, slot_data in slots_data.items():
                slot_id = int(slot_str)

                if slot_id not in self.sequences:
                    logger.warning(f"Skipping slot {slot_id} (out of range)")
                    continue

                # Load events
                events = [
                    RecordingEvent.from_dict(event_data)
                    for event_data in slot_data.get('events', [])
                ]

                # Validate event count
                if len(events) > self.max_events_per_slot:
                    logger.warning(f"Slot {slot_id}: too many events ({len(events)}), truncated")
                    events = events[:self.max_events_per_slot]

                self.sequences[slot_id] = events

                # Load metadata
                if 'metadata' in slot_data:
                    self.metadata[slot_id] = SlotMetadata.from_dict(slot_data['metadata'])

                loaded_count += 1

            logger.info(f"Loaded {loaded_count} slots from {filepath}")
            return True

        except json.JSONDecodeError as e:
            logger.error(f"JSON error: {e}")
            return False
        except Exception as e:
            logger.error(f"Load error: {e}")
            return False

    def export_slot(self, slot: int, filename: str) -> bool:
        """Export single slot."""
        if slot not in self.sequences or not self.sequences[slot]:
            logger.error(f"Slot {slot} is empty or doesn't exist")
            return False

        try:
            filepath = self.recordings_dir / filename
            data = {
                'version': self.FILE_VERSION,
                'exported_at': datetime.now().isoformat(),
                'slot': slot,
                'metadata': self.metadata[slot].to_dict(),
                'events': [event.to_dict() for event in self.sequences[slot]]
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Slot {slot} exported to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Export error: {e}")
            return False

    def import_slot(self, filename: str, target_slot: int) -> bool:
        """Import slot from file."""
        if target_slot not in self.sequences:
            logger.error(f"Invalid target slot: {target_slot}")
            return False

        try:
            filepath = self.recordings_dir / filename

            if not filepath.exists():
                logger.error(f"File not found: {filepath}")
                return False

            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validation
            if 'events' not in data:
                logger.error("Invalid file format")
                return False

            events = [RecordingEvent.from_dict(e) for e in data['events']]

            if len(events) > self.max_events_per_slot:
                logger.warning(f"Too many events, truncated to {self.max_events_per_slot}")
                events = events[:self.max_events_per_slot]

            self.sequences[target_slot] = events

            # Import metadata
            if 'metadata' in data:
                self.metadata[target_slot] = SlotMetadata.from_dict(data['metadata'])

            logger.info(f"Slot imported to {target_slot}")
            return True

        except Exception as e:
            logger.error(f"Import error: {e}")
            return False

    def _is_compatible_version(self, version: str) -> bool:
        """Check file version compatibility."""
        major_version = version.split('.')[0]
        current_major = self.FILE_VERSION.split('.')[0]
        return major_version == current_major

    def get_slot_summary(self) -> List[Tuple[int, str, int, float]]:
        """
        Get summary of all slots.

        Returns:
            List[(slot_id, name, event_count, duration)]
        """
        summary = []
        for slot_id in range(1, self.max_slots + 1):
            meta = self.metadata[slot_id]
            summary.append((
                slot_id,
                meta.name or f"Slot {slot_id}",
                meta.event_count,
                meta.duration
            ))
        return summary
