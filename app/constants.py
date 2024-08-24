""" Global constants for the project. """

from pathlib import Path


class LogLevel:
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


ENCODING = "utf-8"
WATCHER_SLEEP_TIME = 60 * 20  # in seconds

PROJECT_PATH = Path(__file__).resolve().parent.parent
DAEMONS_CONFIG_PATH = PROJECT_PATH / "daemons.yaml"
DAEMONS_PATH = PROJECT_PATH / "daemons"

DEFAULT_REQUIREMENTS_PATH = "requirements.txt"
DEFAULT_TARGET_PATH = "main.py"
DEFAULT_AUTO_RESTART = False
DEFAULT_USE_VIRTUAL_ENV = False
DEFAULT_VIRTUAL_ENV_NAME = "venv"
DEFAULT_ARGUMENTS = ""
IGNORE_REQUIREMENTS_SETTING = "-"

LOG_LEVEL = LogLevel.DEBUG
LOG_FORMAT_STRING = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | "
    "<cyan>{file: <10}</cyan>:<cyan>{line: <4}</cyan> | <cyan>{function: <20}</cyan> | "
    "<level>{message}</level>"
)
LOG_FILE_NAME = "hell.log"
LOG_FILE_PATH = PROJECT_PATH / LOG_FILE_NAME

CMD_TO_DEV_NULL = [">", "/dev/null"]
CMD_DAEMON = "&"
CMD_PIP = "pip3"
CMD_PYTHON = "python3"
CMD_VENV_PYTHON_PATH = Path("bin") / "python"
CMD_VENV_PIP_PATH = Path("bin") / "pip"
CMD_VENV_PIP_INSTALL = ["install", "-r"]
