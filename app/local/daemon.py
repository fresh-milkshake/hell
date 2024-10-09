import os
import platform
from pathlib import Path
import subprocess
import time
from typing import List, Optional, Tuple

from loguru import logger

from app.local import utils, constants
from app.local.enums import DaemonStatus
from app.local.executor import Cmd


class Daemon:
    """Class for running the daemon"""

    requirements_command = f"{constants.CMD_PIP} install -r "

    def __init__(
        self,
        name: str,
        project_folder: Path,
        main_file: Path,
        main_file_arguments: str = "",
        requirements_needed: bool = False,
        requirements_path: Optional[Path] = None,
        restart_if_stopped: bool = False,
        use_virtualenv: bool = True,
    ) -> None:
        if not isinstance(project_folder, Path):
            logger.error(f"project_folder is not a valid path: {project_folder}")

        if not isinstance(main_file, Path):
            logger.error(f"main_file is not a valid path: {main_file}")

        if requirements_needed:
            if not isinstance(requirements_path, Path):
                logger.error(
                    f"requirements_path is not a valid path: {requirements_path}"
                )

        self.name = name
        self.project_folder = project_folder
        self.requirements_path = requirements_path
        self.requirements_needed = requirements_needed
        self.main_file = main_file
        self.main_file_arguments = main_file_arguments
        self.restart_if_stopped = restart_if_stopped
        self.use_virtualenv = use_virtualenv

        self.dependencies_installed = False
        self.deployed_once = False
        self.deployed_at = 0.0

        self.virtualenv_path = self.project_folder / constants.DEFAULT_VIRTUAL_ENV_NAME

        self._process: Optional[subprocess.Popen] = None
        self.failed_starts = 0

        self._status: Optional[DaemonStatus] = None

    @property
    def PID(self) -> int:
        """Return the pid of the daemon"""
        if self._process is None:
            return -1
        return self._process.pid

    @property
    def status(self) -> DaemonStatus:
        """Return the status of the daemon"""
        if self._status is not None:
            return self._status

        if self.is_running():
            self._status = DaemonStatus.RUNNING
        else:
            self._status = DaemonStatus.STOPPED

        return self._status

    @status.setter
    def status(self, status: DaemonStatus):
        self._status = status

    def create_virtualenv(self) -> bool:
        """Create a virtualenv for the daemon, and return True if successful"""
        if self.virtualenv_path.exists():
            logger.warning(
                f"Virtualenv for {self.name} already exists, skipping creation"
            )
            return True

        logger.info(f"Creating virtualenv for {self.name}...")

        cmd = Cmd(
            constants.CMD_PYTHON,
            "-m",
            "venv",
            str(self.virtualenv_path),
        )

        if cmd.verify():
            code, _ = cmd.execute_blocking()
        else:
            return False

        if code != 0:
            logger.error(f"Failed to create virtual environment for {self.name}")
            return False

        logger.success(f"Created virtual environment for {self.name}")
        return True

    def get_dependencies(self) -> List[str] | str:
        """Return a list of dependencies for the daemon"""
        if not self.requirements_path:
            logger.error(
                f"Called get_dependencies() but requirements_path is not set (daemon {self.name})"
            )
            return []

        logger.debug(f'Opening "{self.requirements_path.name}" to get dependencies...')

        if not self.requirements_path.exists():
            logger.exception(
                f'Requirements file not found at "{self.requirements_path}"'
            )
            return []

        with open(
            self.requirements_path, "r", encoding=constants.GLOBAL_ENCODING
        ) as file:
            deps = file.read().splitlines()

            if not deps:
                logger.debug("No requirements for this daemon")

            return deps

    def install_dependancies(self) -> bool:
        """Install dependancies for the daemon, and return True if successful"""
        logger.debug("Searching for dependancies...")

        if not self.requirements_path:
            logger.warning(
                f"Called install_dependancies() but requirements_path is not set (daemon {self.name})"
            )
            return False

        if not self.requirements_path.exists():
            logger.warning(
                f'Failed to install dependancies for "{self.name}" because file "{self.requirements_path}" was not found'
            )
            return False

        dependencies = self.get_dependencies()

        if dependencies and self.use_virtualenv and not self.create_virtualenv():
            return False

        cmd = Cmd(
            str(self.virtualenv_path / constants.CMD_VENV_PIP_PATH),
            *constants.CMD_VENV_PIP_INSTALL,
            str(self.requirements_path),
        )

        code, _ = cmd.execute_blocking()
        if code != 0:
            logger.error(
                f"Failed to install dependancies for {self.name} [pip returned code {code}]"
            )
            return False

        logger.success(f"Installed dependencies: {', '.join(dependencies)}")
        return True

    def kill(self) -> bool:
        """Kill the daemon, and return True if successful"""
        if self._process is None or self.status == DaemonStatus.STOPPED:
            logger.error(f"Daemon {self.name} is not running")
            return False

        self._process.terminate()
        if self._process.poll() is None:
            logger.success(f"Successfully killed {self.name} with PID {self.PID}")
            return True

        self._process.kill()
        if self._process.poll() is None:
            logger.error(f"Successfully killed {self.name} with PID {self.PID}")
            return True

        logger.error(f"Failed to kill {self.name} with PID {self.PID}")
        return False

    def is_running(self) -> bool:
        """Check if the daemon is running"""
        return self._process.poll() is None if self._process else False

    @logger.catch
    def deploy(self) -> bool:
        """Deploy the daemon, and return True if successful"""
        logger.info(f"Deploying {self.name}...")

        if (
            self.requirements_path != constants.IGNORE_REQUIREMENTS_SETTING
            and not self.dependencies_installed
        ):
            self.dependencies_installed = self.install_dependancies()
            if not self.dependencies_installed:
                logger.error(
                    f"Failed to deploy {self.name} [dependancies not installed]"
                )
                return False

        python_command = constants.CMD_PYTHON
        if self.use_virtualenv:
            python_command = str(self.virtualenv_path / constants.CMD_VENV_PYTHON_PATH)

        cmd = Cmd(
            python_command,
            str(self.main_file),
        )

        if platform.system() != "Windows":
            cmd += constants.CMD_TO_DEV_NULL

        try:
            self._process = cmd.execute_in_process()
        except FileNotFoundError:
            logger.error(
                f"Failed to deploy '{self.name}' because '{python_command}' can't be found"
            )
            return False
        except Exception as e:
            logger.critical("System encountered unknown error")
            logger.exception(e)
            return False

        if self._process.poll() is not None:
            logger.error(
                f"Failed to deploy {self.name} [daemon returned code {self._process.returncode}]"
            )
            return False

        logger.success(f"Successfully deployed {self.name} with PID {self.PID}")
        self.deployed_at = time.time()
        self.deployed_once = True
        return True

    def log_information(self):
        """Logs information about Daemon object like pid, name, target path, etc."""

        logger.debug(f"Daemon: {self.name} [PID: {self.PID}]")
        logger.debug(f"Target: {self.main_file}")

        requirements = "No requirements"
        if self.dependencies_installed:
            requirements = ", ".join(self.get_dependencies())
            logger.debug(f"Requirements path: {self.requirements_path}")
        logger.debug(f"Requirements: {requirements}")

        timestamp = "Never"
        if self.deployed_once:
            timestamp = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(self.deployed_at)
            )
        logger.debug(f"Deployment timestamp: {timestamp}")
