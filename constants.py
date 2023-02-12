''' Global constants for the project. '''


import os
from dataclasses import dataclass


@dataclass
class LogLevel:
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


ENCODING = 'utf-8'
WATCHER_SLEEP_TIME = 60 * 20  # in seconds

PROJECT_PATH = os.path.dirname(os.path.realpath(__file__))
DAEMONS_CONFIG_PATH = os.path.join(PROJECT_PATH, "daemons.yaml")
DAEMONS_PATH = os.path.join(PROJECT_PATH, "daemons")

DEFAULT_REQUIREMENTS_PATH = 'requirements.txt'
DEFAULT_TARGET_PATH = 'main.py'
DEFAULT_AUTO_RESTART = False
DEFAULT_USE_VIRTUAL_ENV = False
DEFAULT_VIRTUAL_ENV_NAME = 'venv'
DEFAULT_ARGUMENTS = ''

LOG_LEVEL = LogLevel.DEBUG
LOG_FORMAT_STRING = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | " \
                    "<cyan>{file}</cyan>:<cyan>{line: <3}</cyan> | <cyan>{function: <20}</cyan> | " \
                    "<level>{message}</level>"
LOG_FILE_NAME = 'hell.log'

CMD_TO_DEV_NULL = ['>', '/dev/null']
CMD_DAEMON = '&'
CMD_PIP = 'pip3'
CMD_PYTHON = 'python3'
CMD_VENV_PYTHON_PATH = os.path.join('bin', 'python')
CMD_VENV_PIP_PATH = os.path.join('bin', 'pip')
CMD_VENV_PIP_INSTALL = ['install', '-r']