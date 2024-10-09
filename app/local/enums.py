from enum import Enum


class DaemonStatus(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    PENDING = "pending"
    ERROR = "error"


class DaemonAction(Enum):
    START = "start"
    STOP = "stop"
    RESTART = "restart"
