"""Global constants for the project."""

from datetime import timedelta
from pathlib import Path

from loguru import logger


class LogLevel:
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# General settings
GLOBAL_ENCODING = "utf-8"
WATCHER_SLEEP_TIME = timedelta(seconds=1)
MAX_FAILED_STARTS = 3

if WATCHER_SLEEP_TIME < timedelta(minutes=1):
    log_message_size = 300
    messages_per_second = 1 / WATCHER_SLEEP_TIME.total_seconds()
    bytes_per_second = log_message_size * messages_per_second
    mb_per_hour = bytes_per_second * 3600 / 1024 / 1024
    logger.warning(
        f"Watcher sleep time is less than 1 minute. This potentially may cause a large log file size (>= {mb_per_hour:.2f} MB per hour)."
    )

# Project paths
PROJECT_PATH = Path(__file__).resolve().parent.parent.parent
DAEMONS_CONFIG_PATH = PROJECT_PATH / "daemons.yaml"
DAEMONS_PATH = PROJECT_PATH / "daemons"

# Default settings
DEFAULT_REQUIREMENTS_PATH = Path("requirements.txt")
DEFAULT_TARGET_PATH = Path("main.py")
DEFAULT_AUTO_RESTART = False
DEFAULT_USE_VIRTUAL_ENV = False
DEFAULT_VIRTUAL_ENV_NAME = Path("venv")
DEFAULT_ARGUMENTS = ""
IGNORE_REQUIREMENTS_SETTING = "-"

# Logging settings
LOG_LEVEL = LogLevel.DEBUG
LOG_FORMAT_STRING = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | "
    "<cyan>{file: <15}</cyan>:<cyan>{line: <5}</cyan> | <cyan>{function: <20}</cyan> | "
    "<level>{message}</level>"
)
LOG_FILE_NAME = "manager.log"
LOG_FILE_PATH = PROJECT_PATH / LOG_FILE_NAME

# Command settings
CMD_TO_DEV_NULL = [">", "/dev/null"]
CMD_DAEMON = "&"
CMD_PYTHON = "python"
CMD_PIP = f"{CMD_PYTHON} -m pip"
CMD_VENV_PYTHON_PATH = Path("bin") / "python"
CMD_VENV_PIP_PATH = Path("bin") / "pip"
CMD_VENV_PIP_INSTALL = ["install", "-r"]

WINDOWS_PYTHON_NAMES = ["python.exe", "python3.exe", "pythonw.exe", "python"]
LINUX_PYTHON_NAMES = ["python3", "python"]
