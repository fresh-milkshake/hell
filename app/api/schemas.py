from datetime import datetime
from typing import List, Tuple

from pydantic import BaseModel

from app.manager.daemon import Daemon


class DaemonData(BaseModel):
    running: bool
    pid: int
    memory_mb: float
    cpu_percent: float
    started_at: datetime
    starts_count: int
    start_attempts: int
    failed_starts: int
    venv_created: bool
    installed_requirements: List[str]

    name: str
    daemon_parent_folder: str
    daemon_folder: str
    requirements_path: str | None
    keep_running: bool
    create_venv: bool
    main_file_path: str
    main_file_arguments: Tuple[str, ...]
    git_repo_url: str = ''

    @staticmethod
    def from_daemon(daemon: Daemon) -> 'DaemonData':
        state = daemon.get_state()
        return DaemonData(
            running=state.running,
            pid=state.pid,
            memory_mb=state.memory_mb,
            cpu_percent=state.cpu_percent,
            started_at=state.started_at,
            starts_count=state.starts_count,
            start_attempts=state.start_attempts,
            failed_starts=state.failed_starts,
            venv_created=state.venv_created,
            installed_requirements=state.installed_requirements,

            name=daemon.config.name,
            daemon_parent_folder=str(daemon.config.daemon_parent_folder),
            daemon_folder=str(daemon.config.daemon_folder),
            requirements_path=str(daemon.config.requirements_path)
            if daemon.config.requirements_path
            else "None",
            keep_running=daemon.config.keep_running,
            create_venv=daemon.config.create_venv,
            main_file_path=str(daemon.config.main_file_path),
            main_file_arguments=daemon.config.main_file_arguments,
            git_repo_url=daemon.config.git_repo_url,
        )


class DaemonList(BaseModel):
    daemons: List[DaemonData]
    count: int
    timestamp: float


class ErrorResponse(BaseModel):
    detail: str
