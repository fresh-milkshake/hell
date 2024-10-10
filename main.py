import sys

from loguru import logger
from app.manager import constants
from app.api import app

logger.remove()
logger.add(
    sink=sys.stdout,
    format=constants.LOG_FORMAT_STRING,
    level=constants.LOG_LEVEL,
    colorize=True,
)
logger.add(
    sink=constants.LOG_FILE_PATH,
    format=constants.LOG_FORMAT_STRING,
    level=constants.LOG_LEVEL,
    rotation="1 day",
    compression="zip",
    retention="10 days",
)

logger.info("Starting Hell Gate")