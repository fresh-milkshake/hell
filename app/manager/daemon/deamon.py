import asyncio
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, List

from loguru import logger
from psutil import Popen

from .exceptions import (DaemonIsNotRunningError,
                         DaemonIsRunningError)
from .structures import Config, State
from .. import constants
from ..executor import Cmd
from ..isolation import IsolationProvider
from ..updater import VersionControl


class Daemon:
    def __init__(self, config: Config, parent_folder: Path) -> None:
        self.config = config
        self._process: Popen | None = None
        self._isolation_provider: IsolationProvider | None = None
        self._vc = VersionControl()

        self._parent_folder = parent_folder
        self._venv_path = self._parent_folder / 'venv'
        self._installed_requirements = []
        self._venv_created = False

        self._started_at = None
        self._starts_count = 0
        self._start_attempts = 0
        self._failed_starts = 0

    def prepare_environment(self):
        if self.config.create_venv:
            self._install_requirements()

    @staticmethod
    def running_required(running: bool):
        def decorator(func: Callable):
            def wrapper(self: 'Daemon', *args, **kwargs):
                if self.is_running() == running:
                    return func(self, *args, **kwargs)

                message = f"Call to '{func.__name__}' is invalid."
                if not self.is_running():
                    raise DaemonIsNotRunningError(message)
                else:
                    raise DaemonIsRunningError(message)

            return wrapper

        return decorator

    @running_required(False)
    async def start(self) -> bool:
        """Deploy the daemon, and return True if successful"""
        logger.info(f"Starting {self.config.name}...")
        self._start_attempts += 1

        if (
                self.config.requirements_path and not self._installed_requirements
        ):
            self._install_requirements()
            if not self._installed_requirements:
                logger.error(
                    f"Failed to start {self.config.name} [requirements not installed]"
                )
                self._failed_starts += 1
                return False

        python_command = constants.CMD_PYTHON
        if self._venv_created:
            python_command = str(self._venv_path / constants.CMD_VENV_PYTHON_PATH)

        cmd = Cmd(
            python_command,
            str(self.config.main_file_path),
        )

        if platform.system() != "Windows":
            cmd += constants.CMD_TO_DEV_NULL

        self._isolation_provider = IsolationProvider(self.config)
        self._process = self._isolation_provider.run_in_sandbox(cmd)

        if not self.is_running():
            logger.error(
                f"Failed to deploy {self.config.name} [daemon returned code {self._process.returncode}]"
            )
            self._failed_starts += 1
            return False

        logger.success(f"Successfully deployed {self.config.name} with PID {self._process.pid}")
        self._started_at = datetime.now()
        self._starts_count += 1
        return True

    @running_required(True)
    async def stop(self) -> bool:
        """Kill the daemon, and return True if successful"""
        self._process.kill()
        self._process.terminate()
        logger.critical(self._process.status())  # TODO: remove after testing
        if not self.is_running():
            logger.success(f"Successfully killed {self.config.name} [PID {self._process.pid}]")
            return True

        logger.error(f"Failed to kill {self.config.name} [PID {self._process.pid}]")
        return False

    def is_running(self) -> bool:
        return self._process is not None and self._process.is_running()

    def get_state(self) -> State:
        """
        Creates and returns state object
        """
        return State(
            running=self._process.is_running(),
            pid=self._process.pid,
            memory_mb=self._process.memory_info().rss / (1024 * 1024),
            cpu_percent=self._process.cpu_percent(interval=1),
            started_at=self._started_at,
            starts_count=self._starts_count,
            start_attempts=self._start_attempts,
            failed_starts=self._failed_starts,
            venv_created=self._venv_created,
            installed_requirements=self._installed_requirements,
        )

    def get_pid(self):
        return self._process.pid

    def get_failed_starts(self):
        return self._failed_starts

    def _create_venv(self) -> bool:
        if self._venv_path.exists():
            logger.warning(
                f"Virtualenv for {self.config.name} already exists at '{self._venv_path}'"
            )
            return True

        logger.debug(f"Creating virtualenv for {self.config.name}...")

        cmd = Cmd(
            sys.executable,
            "-m",
            "venv",
            str(self._venv_path),
        )

        if not cmd.verify():
            return False

        code, _ = cmd.execute_blocking()

        if code != 0:
            logger.error(f"Failed to create virtual environment for {self.config.name}")
            return False

        logger.success(f"Created virtual environment for {self.config.name}")
        self._venv_created = True
        return True

    @logger.catch
    def _install_requirements(self) -> bool:
        logger.debug("Searching for requirements...")

        if not self.config.requirements_path:
            logger.warning(
                f"Called _install_requirements() but requirements_path is not set (daemon {self.config.name})"
            )
            return False

        if not self.config.requirements_path.exists():
            logger.warning(
                f'Failed to install requirements for "{self.config.name}" because file "{self.config.requirements_path}" was not found'
            )
            return False

        if self.config.create_venv and not self._create_venv():
            return False

        cmd = Cmd(
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            str(self.config.requirements_path),
        )

        code, _ = cmd.execute_blocking()
        if code != 0:
            logger.error(
                f"Failed to install requirements for {self.config.name} [pip returned code {code}]"
            )
            return False

        self._installed_requirements: List[str] = self._read_requirements_file()
        logger.success(f"Installed requirements: {', '.join(self._installed_requirements)}")
        return True

    def _read_requirements_file(self) -> List[str]:
        if not self.config.requirements_path.exists():
            raise FileNotFoundError("Requirements file does not exist")

        return self.config.requirements_path.read_text().strip().splitlines()


async def test():
    config = Config(
        name="test",
        daemon_parent_folder=Path('.'),
        requirements_path=Path("requirements.txt"),
        keep_running=True,
        create_venv=True,
        main_file_path=Path("main.py"),
        main_file_arguments=(),
        git_repo_url=''
    )

    daemon = Daemon(config, Path('../../../daemons'))
    await daemon.start()

    print(sys.getsizeof(daemon), await daemon.get_state())


if __name__ == '__main__':
    asyncio.run(test())
