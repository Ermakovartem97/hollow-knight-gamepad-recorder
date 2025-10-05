"""Менеджер конфигурации приложения."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from copy import deepcopy

logger = logging.getLogger(__name__)


class ConfigManager:
    """Управление конфигурацией с поддержкой валидации и слияния настроек."""

    DEFAULT_CONFIG_PATH = Path("config/default_config.json")
    USER_CONFIG_PATH = Path("config/user_config.json")

    def __init__(self, user_config_path: Optional[Path] = None):
        self.user_config_path = user_config_path or self.USER_CONFIG_PATH
        self._config: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Загрузить конфигурацию (default + user override)."""
        try:
            # Загрузка дефолтной конфигурации
            with open(self.DEFAULT_CONFIG_PATH, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
            logger.info(f"Loaded default config from {self.DEFAULT_CONFIG_PATH}")

            # Загрузка пользовательской конфигурации (если есть)
            if self.user_config_path.exists():
                with open(self.user_config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                self._merge_config(user_config)
                logger.info(f"Loaded user config from {self.user_config_path}")
        except FileNotFoundError:
            logger.warning(f"Config file not found, using defaults")
            self._config = self._get_fallback_config()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config: {e}")
            self._config = self._get_fallback_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self._config = self._get_fallback_config()

    def save_user_config(self) -> bool:
        """Сохранить текущую конфигурацию как пользовательскую."""
        try:
            self.user_config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.user_config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved user config to {self.user_config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save user config: {e}")
            return False

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Получить значение по пути (например, 'gamepad.record_button').

        Args:
            key_path: Путь к значению через точку
            default: Значение по умолчанию
        """
        keys = key_path.split('.')
        value = self._config

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key_path: str, value: Any) -> None:
        """Установить значение по пути."""
        keys = key_path.split('.')
        config = self._config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value

    def _merge_config(self, user_config: Dict[str, Any]) -> None:
        """Рекурсивное слияние пользовательской конфигурации с дефолтной."""
        def merge_dict(base: Dict, override: Dict) -> Dict:
            result = deepcopy(base)
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = merge_dict(result[key], value)
                else:
                    result[key] = value
            return result

        self._config = merge_dict(self._config, user_config)

    def _get_fallback_config(self) -> Dict[str, Any]:
        """Минимальная конфигурация на случай ошибок."""
        return {
            "version": "1.0.0",
            "gamepad": {
                "record_button": 8,
                "play_button": 9,
                "polling_rate": 100,
                "stick_deadzone": 0.1,
                "trigger_deadzone": 0.05,
                "interference_threshold": 0.2
            },
            "recording": {
                "max_slots": 30,
                "max_events_per_slot": 100000,
                "auto_save": True,
                "backup_on_save": True,
                "recordings_dir": "recordings"
            },
            "ui": {
                "overlay_enabled": True,
                "overlay_alpha": 0.92,
                "always_on_top": True,
                "update_rate": 10
            },
            "playback": {
                "enable_looping": False,
                "loop_count": -1
            },
            "logging": {
                "level": "INFO",
                "console": True
            }
        }

    @property
    def config(self) -> Dict[str, Any]:
        """Получить всю конфигурацию."""
        return deepcopy(self._config)
