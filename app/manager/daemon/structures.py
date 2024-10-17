from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Tuple, List


@dataclass
class Config:
    """
    Configuration structure for Daemon class
    """
    name: str
    daemon_parent_folder: Path
    daemon_folder: Path
    requirements_path: Path | None
    keep_running: bool
    create_venv: bool
    main_file_path: Path
    main_file_arguments: Tuple[str, ...]
    git_repo_url: str = ''


@dataclass(frozen=True)
class State:
    """
    Struct representing process state at one moment
    """
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


if __name__ == "__main__":
    config = Config(
        name="test",
        daemon_parent_folder=Path('.'),
        requirements_path=Path("requirements.txt"),
        keep_running=True,
        create_venv=True,
        main_file_path=Path("main.py"),
    )

    print(config)
