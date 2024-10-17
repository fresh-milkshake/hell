import sys

from loguru import logger

from app import settings

logger.remove()
logger.add(
    sink=sys.stdout,
    format=settings.LOG_FORMAT_STRING,
    level=settings.LOG_LEVEL,
    colorize=True,
)
logger.add(
    sink=settings.LOG_FILE_PATH,
    format=settings.LOG_FORMAT_STRING,
    level=settings.LOG_LEVEL,
    rotation="1 day",
    compression="zip",
    retention="10 days",
)

from app.api import app