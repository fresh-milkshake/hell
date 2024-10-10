from typing import List

from pydantic import BaseModel

from app.manager.enums import DaemonStatus


class DaemonData(BaseModel):
    name: str
    main_file: str
    directory: str
    requirements_path: str
    auto_restart: bool
    arguments: str
    use_virtualenv: bool
    dependencies_installed: bool
    deployed_once: bool
    deployed_at: float
    virtualenv_path: str
    pid: int
    status: DaemonStatus


class DaemonList(BaseModel):
    daemons: List[DaemonData]
    count: int
    timestamp: float


class ErrorResponse(BaseModel):
    detail: str
