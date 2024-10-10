import os
import signal
import time
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
        self.daemons: List[Daemon] = []
        self.auto_restart_list: List[Daemon] = []
        self.pending_for_restart: List[Daemon] = []
        self.running_daemons: List[Daemon] = []
        self._running = False
        self.start_time = None

    def stop(self):
        self._running = False

    def start(self):
        self._running = True
        self.start_time = time.time()

        config = self.load_config()
        self.update_constants(config)
        if not self.run_daemons(config):
            logger.info("Shutting down...")
            return

        self.wait_and_watch()
        self.log_daemons_data()
        self.kill_all()

    def get_running_daemons(self) -> List[Daemon]:
        """Return a list of currently running daemons"""
        return [d for d in self.daemons if d.status == DaemonStatus.RUNNING]

    def get_stopped_daemons(self) -> List[Daemon]:
        """Return a list of daemons that are not running already"""
        return [d for d in self.daemons if d.status == DaemonStatus.STOPPED]

    def wait_and_watch(self):
        """Watch for currently running daemons and check their state"""

        if not self.daemons:
            logger.info("No daemons loaded")
            return

        while self._running:
            try:
                self.check_daemons_state()
            except KeyboardInterrupt:
                logger.info("System paused manually [CTRL+C]")
                if input(">>> Are you sure you want to exit? [y/N]") == "y":
                    break
            except Exception as err:
                logger.exception(err)

        working_time = time.time() - self.start_time
        logger.info(
            f"Ending session...Working time: {time.strftime('%H:%M:%S', time.gmtime(working_time))}"
        )

    def check_daemons_state(self):
        """Check the state of currently running daemons"""
        pending_for_restart = []
        for daemon in self.daemons:
            if not daemon.is_running():
                logger.warning(f"Daemon {daemon.name} no longer running...")
                if daemon.restart_if_stopped:
                    daemon.status = DaemonStatus.PENDING
                    pending_for_restart.append(daemon)

        for daemon in pending_for_restart:
            if daemon.failed_starts < constants.MAX_FAILED_STARTS:
                logger.info(f"Restarting daemon '{daemon.name}'...")
                self.deploy_daemon(daemon)

        if not self.get_running_daemons():
            logger.warning("No daemons running...")
            return

        time.sleep(constants.WATCHER_SLEEP_TIME.total_seconds())

    def log_daemons_data(self) -> None:
        """Log a list of daemons"""
        for daemon in self.daemons:
            daemon.log_information()

    @staticmethod
    def find_daemons_processes(path_prefix: str = str(constants.DAEMONS_PATH), only_pids: bool = True) -> List[int] | \
                                                                                                          List[Tuple[
                                                                                                              int, str]]:
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
    def update_constants(config: dict) -> None:
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
    def load_config() -> dict:
        """Load the config file"""
        if not os.path.exists(constants.DAEMONS_CONFIG_PATH):
            logger.critical(f"Config file not found at {constants.DAEMONS_CONFIG_PATH}")
            exit(1)

        with open(
                constants.DAEMONS_CONFIG_PATH, "r", encoding=constants.GLOBAL_ENCODING
        ) as file:
            config = yaml.safe_load(file)  # yaml.load(file, Loader=yaml.FullLoader)

        if config in [None, {}]:
            logger.critical("Config file is empty")
            return {}

        return config

    @staticmethod
    def create_daemon(name: str, config: dict) -> Daemon | None:
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

    def run_daemons(self, config: dict) -> bool:
        """Load daemons from a given path"""

        if not config["daemons"]:
            logger.warning("No daemons configs found")
            return False

        for daemon_name in config["daemons"]:
            daemon_config = config["daemons"][daemon_name]
            daemon = self.create_daemon(daemon_name, daemon_config)
            if daemon is not None:
                self.add_daemon(daemon)
                if daemon.restart_if_stopped:
                    self.auto_restart_list.append(daemon)

        count = len(self.daemons)

        if not count:
            logger.warning("System encountered problems while checking daemons data")
            return False

        logger.info(f"Loaded {count} daemons")

        return self.deploy_all()

    def add_daemon(self, daemon: Daemon) -> None:
        """Add a daemon to the list of daemons"""
        if daemon.main_file in [d.main_file for d in self.daemons]:
            logger.error(f"Daemon {daemon.name} already exists")
            return

        self.daemons.append(daemon)
        logger.success(f'Loaded "{daemon.name}" daemon')

    def deploy_daemon(self, daemon: Daemon) -> bool:
        """Initialize a daemon"""
        success = daemon.deploy()
        if not success:
            return False

        self.running_daemons.append(daemon)
        return True

    def deploy_all(self) -> bool:
        """Deploy all daemons"""
        if not self.daemons:
            logger.critical("No daemons loaded for deploing")
            return False

        errors = 0

        for daemon in self.daemons:
            error = not daemon.deploy()
            if not error:
                self.running_daemons.append(daemon)
            errors += error

        errors = abs(errors)

        if not errors:
            logger.success(
                f"System initialized and deployed all daemons ({len(self.daemons)})"
            )
        else:
            logger.info(
                f"System encountered {errors} failure(s) and deployed {len(self.daemons) - errors} daemon(s)"
            )

        if errors == len(self.daemons):
            return False

        return True

    def search_daemon_by_pid(self, pid: int) -> Daemon | None:
        """Search a daemon by pid"""
        for daemon in self.daemons:
            if daemon.PID == pid:
                return daemon
        return None

    def search_daemon_by_file(self, file: Path) -> Daemon | None:
        """Search a daemon by file"""
        for daemon in self.daemons:
            if daemon.main_file == file:
                return daemon
        return None

    def search_daemon_by_name(self, name: str) -> Daemon | None:
        """Search a daemon by name"""
        for daemon in self.daemons:
            if daemon.name == name:
                return daemon
        return None

    def kill_daemon(self, daemon: Daemon) -> bool:
        """Kill a daemon"""
        daemon = next(
            filter(lambda d: d.name == daemon.name, self.get_running_daemons())
        )
        if not daemon.is_running():
            logger.warning(f"Daemon {daemon.name} [PID {daemon.PID}] is not running")
            return False

        success = daemon.kill()
        if not success:
            return False

        self.running_daemons.remove(daemon)
        return True

    def kill_all(self) -> None:
        """Kill all running daemons"""
        for daemon in self.get_running_daemons():
            self.kill_daemon(daemon)

        if not self.get_running_daemons():
            logger.info("System killed all daemons")
        else:
            logger.warning(
                f"System failed to kill {len(self.get_running_daemons())} daemon(s):"
            )
            for daemon in self.get_running_daemons():
                logger.error(
                    f"| Daemon {daemon.name} [PID {daemon.PID}] failed to kill"
                )

                if utils.send_signal(daemon.PID, signal.SIGTERM):
                    logger.success(
                        f"| Daemon {daemon.name} [PID {daemon.PID}] killed by SIGTERM"
                    )
                else:
                    logger.error(
                        f"| Daemon {daemon.name} [PID {daemon.PID}] failed to kill by SIGTERM"
                    )


if __name__ == "__main__":
    hell = Hell()
