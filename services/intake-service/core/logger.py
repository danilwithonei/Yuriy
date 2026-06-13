import logging
import sys
import os

def setup_logger(name: str):
    """
    Настраивает логгер с красивым форматом для консоли.
    """
    logger = logging.getLogger(name)
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

    # Формат логов: Время - Имя - Уровень - Сообщение
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Вывод в stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(handler)

    return logger

# Дефолтный логгер для сервиса
logger = setup_logger("yuriy-app")
