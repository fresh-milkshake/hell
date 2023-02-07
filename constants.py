import os


ENCODING = 'utf-8'
WATCHER_SLEEP_TIME = 60 * 20  # in seconds

PROJECT_PATH = os.path.dirname(os.path.realpath(__file__))
DAEMONS_PATH = os.path.join(PROJECT_PATH, "daemons")
DAEMONS_CONFIG_PATH = os.path.join(PROJECT_PATH, "daemons.yaml")
