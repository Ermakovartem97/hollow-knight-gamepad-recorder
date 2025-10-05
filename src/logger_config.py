"""Конфигурация логирования."""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    console: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 3
) -> None:
    """
    Настроить систему логирования.

    Args:
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Путь к файлу логов (None = без файла)
        console: Выводить логи в консоль
        max_bytes: Максимальный размер файла лога
        backup_count: Количество резервных копий
    """
    # Преобразование строки уровня в константу
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Формат логов
    log_format = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(log_format, date_format)

    # Корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()  # Удаляем существующие обработчики

    # Консольный обработчик
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Файловый обработчик с ротацией
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Подавление излишне многословных библиотек
    logging.getLogger('pygame').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
