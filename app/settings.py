from enum import Enum
from pathlib import Path

PROJECT_PATH = Path(__file__).resolve().parent.parent

DATABASE_FILE_NAME = "database.db"
DATABASE_PATH = PROJECT_PATH / DATABASE_FILE_NAME


class LogLevel(str, Enum):
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# General settings
GLOBAL_ENCODING = "utf-8"

# Logging settings
LOG_LEVEL = LogLevel.DEBUG
LOG_FORMAT_STRING = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | "
    "<cyan>{file: <15}</cyan>:<cyan>{line: <5}</cyan> | <cyan>{function: <25}</cyan> | "
    "<level>{message}</level>"
)
LOG_FILE_NAME = "manager.log"
LOG_FILE_PATH = PROJECT_PATH / LOG_FILE_NAME
