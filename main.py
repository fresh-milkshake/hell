import sys
from loguru import logger

from app import constants
from app.hell import Hell

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
    rotation="1 week",
    compression="zip",
    retention="10 days",
)

if __name__ == "__main__":
    Hell()
