import sys
from loguru import logger

from app.local import constants
from app.api.routes import router as api_router

from fastapi import FastAPI

from app.local.hell import Hell

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

hell = Hell()
app = FastAPI()
app.include_router(api_router, prefix="/api")
