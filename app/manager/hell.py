import asyncio
import os
import signal
from pathlib import Path
from typing import List, Tuple

import psutil
import yaml
from loguru import logger

from app.manager import utils, constants
from app.manager.daemon import Daemon
from app.manager.enums import DaemonStatus


@utils.singleton
class Hell:
    """Class "Manager" for daemons deployment and killing"""

    def __init__(self) -> None:
        self.__config = None
        self.__daemons: List[Daemon] = []
        self.__auto_restart_list: List[Daemon] = []
        self.__pending_for_restart: List[Daemon] = []
        self.__running_daemons: List[Daemon] = []
        self.running = False
        self.start_time = None

        self.__watcher_task = None

    async def stop(self) -> Tuple[bool, str]:
        """
        Stops daemons polling task and all running daemons

        Returns:
            Tuple[bool, str]: True if success, False if failed
        """

        if not self.running:
            return False, "System is not running"

        self.running = False
        if self.__watcher_task:
            logger.info("Stopping daemons polling task...")
            self.__watcher_task.cancel()
            await self.__watcher_task

        logger.info("Stopping all running daemons...")
        await self.__stop_all()

        return True, "System stopped"

    async def __stop_all(self) -> None:
        """Kill all running daemons"""
        for daemon in self.get_running_daemons():
            await self.__stop_daemon(daemon)

        if not self.get_running_daemons():
            logger.info("System killed all daemons")
        else:
            logger.warning(
                f"System failed to kill {len(self.get_running_daemons())} daemon(s)"
            )

            for daemon in self.get_running_daemons():
                logger.error(
                    f"| Daemon {daemon.name} [PID {daemon.PID}] failed to kill"
                )

                utils.kill_by_signal(daemon.PID, signal.SIGTERM)

                if daemon.is_running():
                    logger.error(
                        f"| Daemon {daemon.name} [PID {daemon.PID}] failed to stop"
                    )
                else:
                    logger.success(f"| Daemon {daemon.name} [PID {daemon.PID}] stopped")

    async def start(self) -> tuple[bool, str]:
        """
        Starts daemons polling task and all daemons

        Returns:
            Tuple[bool, str]: True if success, False if failed
        """
        self.__init__()

        self.running = True
        self.__config = self.__load_config()
        self.__update_constants(self.__config)
        self.__load_daemons(self.__config)

        logger.info("Starting daemons...")
        if not await self.__start_all():
            return False, "Can't start any daemon"

        try:
            task = asyncio.create_task(self.__check_daemons_state())
            self.__watcher_task = task
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
        daemon = self.search_daemon_by_name(daemon_name)
        if not daemon:
            logger.error(f"Daemon {daemon_name} not found")
            return False
        return await self.__stop_daemon(daemon)

    @staticmethod
    async def __stop_daemon(daemon: Daemon) -> bool:
        if not daemon.is_running():
            logger.warning(f"Daemon {daemon.name} [PID {daemon.PID}] is not running")
            return False
        return await daemon.stop()

    async def start_daemon(self, daemon_name: str) -> bool:
        """Starts a daemon by name"""
        daemon = self.search_daemon_by_name(daemon_name)
        if not daemon:
            logger.error(f"Daemon {daemon_name} not found")
            return False
        return await self.__start_daemon(daemon)

    @staticmethod
    async def __start_daemon(daemon: Daemon) -> bool:
        if daemon.is_running():
            logger.warning(
                f"Daemon {daemon.name} [PID {daemon.PID}] is already running"
            )
            return False
        return await daemon.start()

    async def restart_daemon(self, daemon_name: str) -> bool:
        """Restarts a daemon by name"""
        daemon = self.search_daemon_by_name(daemon_name)
        if not daemon:
            logger.error(f"Daemon {daemon_name} not found")
            return False
        return await self.__restart_daemon(daemon)

    async def __restart_daemon(self, daemon: Daemon) -> bool:
        return await self.__stop_daemon(daemon) and await self.__start_daemon(daemon)

    def get_running_daemons(self) -> List[Daemon]:
        return [daemon for daemon in self.__daemons if daemon.is_running()]

    def get_stopped_daemons(self) -> List[Daemon]:
        return [daemon for daemon in self.__daemons if not daemon.is_running()]

    def get_all_daemons(self) -> List[Daemon]:
        return self.__daemons

    async def __check_daemons_state(self):
        """Check the state of currently running daemons"""
        try:
            while True:
                pending_for_restart = []
                for daemon in self.__daemons:
                    if not daemon.is_running():
                        logger.warning(f"Daemon {daemon.name} no longer running...")
                        if daemon.restart_if_stopped:
                            daemon.status = DaemonStatus.PENDING
                            pending_for_restart.append(daemon)

                for daemon in pending_for_restart:
                    if daemon.failed_starts < constants.MAX_FAILED_STARTS:
                        logger.info(f"Restarting daemon '{daemon.name}'...")
                        await self.__start_daemon(daemon)

                if not self.get_running_daemons():
                    logger.warning("No daemons running...")
                    return

                await asyncio.sleep(constants.WATCHER_SLEEP_TIME.total_seconds())
        except asyncio.CancelledError:
            return

    def __log_daemons_data(self) -> None:
        """Log a list of daemons"""
        for daemon in self.__daemons:
            daemon.log_information()

    @staticmethod
    def __find_daemons_processes(
        path_prefix: str = str(constants.DAEMONS_PATH), only_pids: bool = True
    ) -> List[int] | List[Tuple[int, str]]:
        pids = []
        for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
            pinfo = proc.info
            try:
                if (
                    pinfo["name"] == constants.CMD_PYTHON
                    and len(pinfo["cmdline"]) > 1
                    and pinfo["cmdline"][1].startswith(path_prefix)
                ):
                    pid = pinfo["pid"]
                    file_path = pinfo["cmdline"][1]
                    pids.append(pid if only_pids else (pid, file_path))
            except psutil.NoSuchProcess:
                continue
            except psutil.AccessDenied:
                logger.warning(f"Access denied for process {pinfo['pid']}")
            except Exception as e:
                logger.error(
                    f"Unexpected error processing PID {pinfo['pid']}: {str(e)}"
                )

        return pids

    @staticmethod
    def __update_constants(config: dict) -> None:
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
        constants.DAEMONS_PATH = config.get("daemons-path", constants.DAEMONS_PATH)
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
    def __load_config() -> dict:
        """Load the config file"""
        if not os.path.exists(constants.DAEMONS_CONFIG_PATH):
            logger.critical(f"Config file not found at {constants.DAEMONS_CONFIG_PATH}")
            exit(1)

        with open(
            constants.DAEMONS_CONFIG_PATH, "r", encoding=constants.GLOBAL_ENCODING
        ) as file:
            config = yaml.safe_load(file)

        if config in [None, {}]:
            logger.critical("Config file is empty")
            return {}

        return config

    @staticmethod
    def __create_daemon(name: str, config: dict) -> Daemon | None:
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

        daemon_directory = config.get("dir", Path(name))
        daemon_directory: Path = constants.DAEMONS_PATH / daemon_directory
        if not daemon_directory.exists():
            logger.warning(f'Daemon directory "{daemon_directory}" not found')
            return None

        target = config.get("target", constants.DEFAULT_TARGET_PATH)
        target: Path = daemon_directory / target
        if not target.exists():
            logger.critical(f"Target file {target} not found")
            return None

        requirements: Path | str = config.get(
            "requirements", constants.IGNORE_REQUIREMENTS_SETTING
        )
        requirements_needed = True
        if requirements != constants.IGNORE_REQUIREMENTS_SETTING:
            if requirements == "default":
                requirements = (
                    constants.DAEMONS_PATH
                    / daemon_directory
                    / constants.DEFAULT_REQUIREMENTS_PATH
                )
            else:
                requirements = constants.DAEMONS_PATH / daemon_directory / requirements

            if not requirements.exists():
                logger.warning(f'Requirements file "{requirements}" not found')
                return None
        else:
            requirements_needed = False

        arguments = config.get("arguments", constants.DEFAULT_ARGUMENTS)
        auto_restart = config.get("auto-restart", constants.DEFAULT_AUTO_RESTART)
        use_venv = config.get("use-venv", constants.DEFAULT_USE_VIRTUAL_ENV)

        daemon = Daemon(
            name=name,
            project_folder=daemon_directory,
            main_file=target,
            main_file_arguments=arguments,
            requirements_needed=requirements_needed,
            requirements_path=requirements,  # type: ignore
            restart_if_stopped=auto_restart,
            use_virtualenv=use_venv,
        )

        return daemon

    def __load_daemons(self, config: dict) -> bool:
        """Load daemons from a given path"""

        if not config["daemons"]:
            logger.warning("No daemons configs found")
            return False

        for daemon_name in config["daemons"]:
            daemon_config = config["daemons"][daemon_name]
            daemon = self.__create_daemon(daemon_name, daemon_config)
            if daemon is not None:
                if self.__add_daemon(daemon) and daemon.restart_if_stopped:
                    self.__auto_restart_list.append(daemon)

        count = len(self.__daemons)

        if not count:
            logger.warning("System encountered problems while checking daemons data")
            return False

        logger.info(f"Loaded {count} daemons")
        return True

    async def __start_all(self) -> bool:
        """
        Start all daemons asynchronously
        """
        if not self.__daemons:
            logger.critical("No daemons loaded for deploying")
            return False

        errors = 0

        async def start_daemon(daemon: Daemon):
            nonlocal errors
            try:
                if await daemon.start():
                    self.__running_daemons.append(daemon)
                else:
                    errors += 1
            except Exception as e:
                errors += 1
                logger.error(f"Error starting daemon {daemon}: {e}")

        tasks = [start_daemon(daemon) for daemon in self.__daemons]
        await asyncio.gather(*tasks)

        if errors == 0:
            logger.success(
                f"System initialized and deployed all daemons ({len(self.__daemons)})"
            )
        else:
            logger.info(
                f"System encountered {errors} failure(s) and deployed {len(self.__daemons) - errors} daemon(s)"
            )

        return errors < len(self.__daemons)

    def __add_daemon(self, daemon: Daemon) -> bool:
        """Add a daemon to the list of daemons"""
        if daemon.main_file in [d.main_file for d in self.__daemons]:
            logger.error(f"Daemon {daemon.name} already exists")
            return False

        self.__daemons.append(daemon)
        logger.success(f'Loaded "{daemon.name}" daemon')
        return True

    def search_daemon_by_pid(self, pid: int) -> Daemon | None:
        """Search a daemon by pid"""
        for daemon in self.__daemons:
            if daemon.PID == pid:
                return daemon
        return None

    def search_daemon_by_file(self, file: Path) -> Daemon | None:
        """Search a daemon by file"""
        for daemon in self.__daemons:
            if daemon.main_file == file:
                return daemon
        return None

    def search_daemon_by_name(self, name: str) -> Daemon | None:
        """Search a daemon by name"""
        for daemon in self.__daemons:
            if daemon.name == name:
                return daemon
        return None
