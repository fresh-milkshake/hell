''' b '''


import os


ENCODING = 'utf-8'
WATCHER_SLEEP_TIME = 60 * 20  # in seconds

PROJECT_PATH = os.path.dirname(os.path.realpath(__file__))
DAEMONS_PATH = os.path.join(PROJECT_PATH, "daemons")
DAEMONS_CONFIG_PATH = os.path.join(PROJECT_PATH, "daemons.yaml")

ERROR_CONFIG_FILE_NOT_FOUND = "Can't start daemon without proper instructions about target and name." \
                              "They should be in file called 'daemons.yaml' and locate somewhere on this computer."
ERROR_INCORRECT_YAML_FORMAT = ''
ERROR_NO_DAEMONS_LOADED = ''
ERROR_REQUIREMENT_NOT_FOUND = ''

DEFAULT_REQUIREMENTS_PATH = 'requirements.txt'