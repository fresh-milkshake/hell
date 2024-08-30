import os
from pathlib import Path
import subprocess
import time
from typing import List

from loguru import logger

from app import utils, constants


class Daemon:
    """Class for running the daemon"""

    requirements_command = f"{constants.CMD_PIP} install -r "
    python_command = constants.CMD_PYTHON

    def __init__(
        self,
        name: str,
        target_path: Path,
        daemon_dir: Path,
        requirements_needed: bool,
        requirements_path: Path,
        arguments: str = "",
        auto_restart: bool = False,
        use_virtualenv: bool = True,
    ) -> None:
        """Initialize Daemon object

        :param name: name of the daemon
        :param target_path: path to the target file
        :param daemon_dir: path to the daemon directory
        :param requirements_path: path to the requirements file
        """

        assert isinstance(daemon_dir, Path)
        assert isinstance(target_path, Path)
        if requirements_needed:
            assert isinstance(requirements_path, Path)

        self.name = name
        self.target_path = target_path
        self.daemon_dir = daemon_dir
        self.requirements_path = requirements_path
        self.auto_restart = auto_restart
        self.arguments = arguments
        self.use_virtualenv = use_virtualenv

        self.dependancies_installed = False
        self.deployed_once = False
        self.deploy_time = 0

        self.virtualenv_path = self.daemon_dir / constants.DEFAULT_VIRTUAL_ENV_NAME

        self._process: subprocess.Popen | None = None
        self.failed_starts = 0

    @property
    def PID(self) -> int:
        """Return the pid of the daemon"""
        if self._process is None:
            return -1
        return self._process.pid

    def get_dependencies(self) -> List[str] | str:
        """Return a list of dependencies for the daemon"""
        logger.debug(f'Opening "{self.requirements_path.name}" to get dependencies...')

        if not self.requirements_path.exists():
            logger.exception(
                f'Requirements file not found at "{self.requirements_path}"'
            )
            return []

        with open(self.requirements_path, "r", encoding=constants.ENCODING) as file:
            deps = file.read().splitlines()

            if not deps:
                logger.debug("No requirements for this daemon")

            return deps

    def create_virtualenv(self) -> bool:
        """Create a virtualenv for the daemon, and return True if successful"""
        if self.virtualenv_path.exists():
            logger.warning(
                f"Virtualenv for {self.name} already exists, skipping creation"
            )
            return True

        logger.info(f"Creating virtualenv for {self.name}...")
        command = [constants.CMD_PYTHON, "-m", "venv", self.virtualenv_path]
        code, _ = utils.execute_command(command)
        if code != 0:
            logger.error(f"Failed to create virtual environment for {self.name}")
            return False

        logger.success(f"Created virtual environment for {self.name}")
        return True

    def install_dependancies(self) -> bool:
        """Install dependancies for the daemon, and return True if successful"""
        logger.debug(f"Searching for dependancies...")

        if not os.path.exists(self.requirements_path):
            logger.warning(
                f'Failed to install dependancies for "{self.name}" because file "{self.requirements_path}" was found'
            )
            return False

        dependencies = self.get_dependencies()

        if dependencies and self.use_virtualenv and not self.create_virtualenv():
            return False

        pip_command = [
            os.path.join(self.virtualenv_path, constants.CMD_VENV_PIP_PATH),
            *constants.CMD_VENV_PIP_INSTALL,
            self.requirements_path,
        ]
        code, _ = utils.execute_command(pip_command)
        if code != 0:
            logger.error(
                f"Failed to install dependancies for {self.name} [pip returned code {code}]"
            )
            return False

        logger.success(f"Installed dependencies: {', '.join(dependencies)}")
        return True

    def kill(self) -> bool:
        """Kill the daemon, and return True if successful"""
        if self.PID == -1:
            logger.error(f"Daemon {self.name} is not running")
            return False

        self._process.terminate()

        logger.success(f"Successfully killed {self.name} with PID {self.PID}")
        return True

    @logger.catch
    def deploy(self) -> bool:
        """Deploy the daemon, and return True if successful"""
        logger.info(f"Deploying {self.name}...")

        if (
            self.requirements_path != constants.IGNORE_REQUIREMENTS_SETTING
            and not self.dependancies_installed
        ):
            self.dependancies_installed = self.install_dependancies()
            if not self.dependancies_installed:
                logger.error(
                    f"Failed to deploy {self.name} [dependancies not installed]"
                )
                return False

        python_command = self.virtualenv_path / constants.CMD_VENV_PYTHON_PATH
        command = [
            python_command,
            self.target_path,
            constants.CMD_DAEMON,
            *constants.CMD_TO_DEV_NULL,
        ]

        try:
            self._process = subprocess.Popen(command)
        except FileNotFoundError as e:
            logger.error(
                f"Failed to deploy '{self.name}' because python3 can't be found on this device"
            )
            return False
        except Exception as e:
            logger.critical(f"System encountered unknown error")
            logger.exception(e)
            return False

        if self._process.poll():
            logger.error(
                f"Failed to deploy {self.name} [daemon returned code {self._process.returncode}]"
            )
            return False

        target = self.target_path.as_posix()
        for pid, path in utils.get_hell_pids():
            if path == target and pid == self.PID:
                logger.success(f"Successfully deployed {self.name} with PID {self.PID}")
                self.deploy_time = time.time()
                self.deployed_once = True
                return True

        logger.error(f"Failed to deploy {self.name}")
        return False

    def log_information(self):
        """Logs information about Daemon object like pid, name, target path, etc."""

        logger.debug(f"Daemon: {self.name} [PID: {self.PID}]")
        logger.debug(f"Target: {self.target_path}")

        requirements = "No requirements"
        if self.dependancies_installed:
            requirements = ", ".join(self.get_dependencies())
            logger.debug(f"Requirements path : {self.requirements_path}")
        logger.debug(f"Requirements: {requirements}")

        timestamp = "Never"
        if self.deployed_once:
            timestamp = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(self.deploy_time)
            )
        logger.debug(f"Deploiement timestamp: {timestamp}")
