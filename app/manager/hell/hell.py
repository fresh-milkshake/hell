import asyncio
import os
import signal
from pathlib import Path
from typing import List, Tuple, Dict

import yaml
from loguru import logger

from app import settings
from app.manager import utils, constants
from ..daemon import Daemon, Config


@utils.singleton
class Hell:
    """Class "Manager" for daemons deployment and killing"""

    def __init__(self) -> None:
        self._daemons_mapping: Dict[str, Daemon] = {}
        self._config = None
        self._pending_for_restart: List[Daemon] = []
        self.running = False
        self.start_time = None

        self._watcher_task = None

    async def stop(self) -> Tuple[bool, str]:
        """
        Stops daemons polling task and all running daemons

        Returns:
            Tuple[bool, str]: True if success, False if failed
        """

        if not self.running:
            return False, "System is not running"

        self.running = False
        if self._watcher_task:
            logger.info("Stopping daemons polling task...")
            self._watcher_task.cancel()
            await self._watcher_task

        logger.info("Stopping all running daemons...")
        await self._stop_all()

        return True, "System stopped"

    async def _stop_all(self) -> None:
        """Kill all running daemons"""
        for daemon in self.get_running_daemons():
            await daemon.stop()

        if not self.get_running_daemons():
            logger.success("System killed all daemons")
        else:
            logger.warning(
                f"System failed to kill {len(self.get_running_daemons())} daemon(s)"
            )

            for daemon in self.get_running_daemons():
                logger.error(
                    f"| Daemon {daemon.config.name} [PID {daemon.get_pid()}] failed to kill"
                )

                utils.kill_by_signal(daemon.get_pid(), signal.SIGTERM)

                if daemon.is_running():
                    logger.error(
                        f"| Daemon {daemon.config.name} [PID {daemon.get_pid()}] failed to stop"
                    )
                else:
                    logger.success(f"| Daemon {daemon.config.name} [PID {daemon.get_pid()}] stopped")

    async def start(self) -> tuple[bool, str]:
        """
        Starts daemons polling task and all daemons

        Returns:
            Tuple[bool, str]: True if success, False if failed
        """
        self.__init__()

        self.running = True
        self._config = self._load_config()
        self._update_constants(self._config)
        self._load_daemons(self._config)

        logger.info("Starting daemons...")
        if not await self._start_all():
            return False, "Can't start any daemon"

        try:
            task = asyncio.create_task(self.__check_daemons_state())
            self._watcher_task = task
        except Exception as e:
            logger.error(e)
            return False, "Can't start watcher"

        return True, "Successfully started system"

    async def restart(self, delay_sec: int = 0) -> Tuple[bool, str]:
        """
        Restarts daemons polling task and all daemons

        Returns:
            Tuple[bool, str]: True if success, False if failed
        """
        logger.info("Restarting system...")
        success, msg = await self.stop()
        if not success:
            return False, msg

        await asyncio.sleep(delay_sec)
        return await self.start()

    async def stop_daemon(self, daemon_name: str) -> bool:
        """Stops a daemon by name"""
        daemon = self._daemons_mapping[daemon_name]

        if not daemon:
            logger.error(f"Daemon {daemon_name} not found")
            return False

        return await daemon.stop()

    async def start_daemon(self, daemon_name: str) -> bool:
        """Starts a daemon by name"""
        daemon = self._daemons_mapping[daemon_name]
        if not daemon:
            logger.error(f"Daemon {daemon_name} not found")
            return False
        return await daemon.start()

    async def restart_daemon(self, daemon_name: str) -> bool:
        """Restarts a daemon by name"""
        daemon = self.search_daemon_by_name(daemon_name)
        if not daemon:
            logger.error(f"Daemon {daemon_name} not found")
            return False
        return await daemon.stop() and await daemon.start()

    def get_running_daemons(self) -> List[Daemon]:
        return [daemon for daemon in self._daemons_mapping.values() if daemon.is_running()]

    def get_stopped_daemons(self) -> List[Daemon]:
        return [daemon for daemon in self._daemons_mapping.values() if not daemon.is_running()]

    def get_all_daemons(self) -> list[Daemon]:
        return list(self._daemons_mapping.values())

    async def __check_daemons_state(self):
        """Check the state of currently running daemons"""
        try:
            while True:
                pending_for_restart = []
                for daemon in self._daemons_mapping.values():
                    if not daemon.is_running():
                        logger.warning(f"Daemon {daemon.config.name} no longer running...")
                        if daemon.config.keep_running:
                            pending_for_restart.append(daemon)

                for daemon in pending_for_restart:
                    if daemon.get_failed_starts() < constants.MAX_FAILED_STARTS:
                        logger.info(f"Restarting daemon '{daemon.config.name}'...")
                        await daemon.start()

                if not self.get_running_daemons():
                    logger.warning("No daemons running...")
                    return

                await asyncio.sleep(constants.WATCHER_SLEEP_TIME.total_seconds())
        except asyncio.CancelledError:
            return

    def _log_daemons_data(self) -> None:
        """Log a list of daemons"""
        for daemon in self._daemons_mapping.values():
            state = daemon.get_state()
            message = str(state)
            logger.debug(message)

    @staticmethod
    def _update_constants(config: dict) -> None:
        """Updates global constants like DAEMONS_PATH and other based on config dict.

        Parameters for a global setting are:

        # By default, daemons are stored in the same folder as the main script
        # in a subfolder named "daemons"
        daemons-path: <path-to-folder-with-daemons>
        # Default arguments to pass to every entry point
        default-args: <string-with-arguments>
        # Value of virtual environment to use or not for every daemon by default,
        # Default value is False
        default-venv: <true/false/True/False>
        # Default value for auto-restart for every daemon,
        # Default value is False
        default-auto-restart: <true/false/True/False>
        """
        constants.DAEMONS_PATH = config.get("daemons-path", constants.DAEMONS_FOLDER_PATH)
        constants.DEFAULT_ARGUMENTS = config.get(
            "default-args", constants.DEFAULT_ARGUMENTS
        )
        constants.DEFAULT_USE_VIRTUAL_ENV = config.get(
            "default-venv", constants.DEFAULT_USE_VIRTUAL_ENV
        )
        constants.DEFAULT_AUTO_RESTART = config.get(
            "default-auto-restart", constants.DEFAULT_AUTO_RESTART
        )

    @staticmethod
    def _load_config() -> dict:
        """Load the config file"""
        if not constants.DAEMONS_CONFIG_PATH.exists():
            logger.critical(f"Config file not found at {constants.DAEMONS_CONFIG_PATH}")
            exit(1)

        with open(
                constants.DAEMONS_CONFIG_PATH, "r", encoding=settings.GLOBAL_ENCODING
        ) as file:
            config = yaml.safe_load(file)

        if config in [None, {}]:
            logger.critical("Config file is empty")
            return {}

        return config

    @staticmethod
    def _create_daemon(name: str, yaml_config: dict) -> Daemon | None:
        """Create a daemon from a given config dict.

        Parameters for a daemon in YAML format:

        <name>:
            # Name of daemon directory in DAEMONS_PATH,
            # by default its <name>
            dir: <daemon-directory>
            # Path to file with entry point, by default its
            # "<DAEMONS_PATH>/<daemon-directory>/main.py"
            target: <path-to-main-python-file>
            # Arguments to pass to target file
            arguments: <arguments-to-pass-to-target>
            # Path to requirements.txt file for dependencies, by default its
            # "<DAEMONS_PATH>/<daemon-directory>/requirements.txt"
            requirements: <path-to-requirements.txt or "-">
            # Whether to restart the daemon if it crashes, or not
            # by default its False
            auto-restart: <True/False/true/false>
            # Whether to use virtual environment for dependencies, or
            # use global dependencies, by default its False
            virtualenv: <True/False/true/false>
        """

        daemon_directory = yaml_config.get("dir", Path(name))
        daemon_directory: Path = constants.DAEMONS_FOLDER_PATH / daemon_directory
        if not daemon_directory.exists():
            logger.warning(f'Daemon directory "{daemon_directory}" not found')
            return None

        target = yaml_config.get("target", constants.DEFAULT_TARGET_PATH)
        target: Path = daemon_directory / target
        if not target.exists():
            logger.critical(f"Target file {target} not found")
            return None

        requirements = yaml_config.get(
            "requirements", constants.IGNORE_REQUIREMENTS_SETTING
        )
        if requirements == "default":
            requirements = (
                constants.DAEMONS_FOLDER_PATH
                / daemon_directory
                / constants.DEFAULT_REQUIREMENTS_PATH
            )
        elif requirements == constants.IGNORE_REQUIREMENTS_SETTING:
            requirements = None
        else:
            requirements = constants.DAEMONS_FOLDER_PATH / daemon_directory / requirements

        if requirements and not requirements.exists():
            logger.warning(f'Requirements file "{requirements}" not found')
            return None

        arguments = yaml_config.get("arguments", constants.DEFAULT_ARGUMENTS)
        auto_restart = yaml_config.get("auto-restart", constants.DEFAULT_AUTO_RESTART)
        use_venv = yaml_config.get("virtualenv", constants.DEFAULT_USE_VIRTUAL_ENV)

        config_obj = Config(
            name=name,
            daemon_parent_folder=constants.DAEMONS_FOLDER_PATH,
            daemon_folder=daemon_directory,
            requirements_path=requirements,
            keep_running=auto_restart,
            create_venv=use_venv,
            main_file_path=target,
            main_file_arguments=tuple(arguments)
        )

        daemon = Daemon(config_obj, constants.DAEMONS_FOLDER_PATH)
        return daemon

    def _load_daemons(self, config: dict) -> bool:
        """Load daemons from a given path"""

        if not config["daemons"]:
            logger.warning("No daemons configs found")
            return False

        for daemon_name in config["daemons"]:
            daemon_config = config["daemons"][daemon_name]
            daemon = self._create_daemon(daemon_name, daemon_config)
            if daemon is not None:
                self._add_daemon(daemon)

        count = len(self._daemons_mapping)

        if not count:
            logger.warning("System encountered problems while checking daemons data")
            return False

        logger.info(f"Loaded {count} daemons")
        return True

    async def _start_all(self) -> bool:
        """
        Start all daemons asynchronously
        """
        if not self._daemons_mapping:
            logger.critical("No daemons loaded for deploying")
            return False

        errors = 0

        async def start_daemon(daemon: Daemon):
            nonlocal errors
            try:
                if not await daemon.start():
                    errors += 1
            except Exception as e:
                errors += 1
                logger.error(f"Error starting daemon {daemon}: {e}")

        tasks = [start_daemon(daemon) for daemon in self._daemons_mapping.values()]
        await asyncio.gather(*tasks)

        if errors == 0:
            logger.success(
                f"System initialized and deployed all daemons ({len(self._daemons_mapping)})"
            )
        else:
            logger.info(
                f"System encountered {errors} failure(s) and deployed {len(self._daemons_mapping) - errors} daemon(s)"
            )

        return errors < len(self._daemons_mapping)

    def _add_daemon(self, daemon: Daemon) -> bool:
        if daemon.config.main_file_path in [d.config.main_file_path for d in self._daemons_mapping.values()]:
            logger.error(f"Daemon {daemon.config.name} already exists")
            return False

        self._daemons_mapping[daemon.config.name] = daemon
        logger.success(f'Loaded "{daemon.config.name}" daemon')
        return True

    def search_daemon_by_name(self, name: str) -> Daemon | None:
        return self._daemons_mapping[name]
