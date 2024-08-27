import os
from pathlib import Path
import time
from typing import List

from loguru import logger

import yaml

from app import utils, constants
from app.daemon import Daemon


class Hell:
    """Class "Manager" for daemons deployment and killing"""

    def __init__(self, autostart_enabled=False) -> None:
        self.daemons: List[Daemon] = []
        self.deployed_daemons: List[Daemon] = []
        self.auto_restart_list: List[Daemon] = []
        self.pending_for_restart: List[Daemon] = []

        self.auto_restart_enabled = autostart_enabled
        self.start_time = time.time()

        config = self.load_config()
        self.update_constants(config)
        if not self.run_daemons(config):
            logger.info("Shutting down...")
            return

        self.enter_waiting_stage()
        self.log_daemons_data()
        self.kill_all()

    @property
    def running_daemons(self) -> List[Daemon]:
        """Return a list of currently running daemons"""
        return [d for d in self.daemons if d.pid != -1]

    @property
    def stale_daemons(self) -> List[Daemon]:
        """Return a list of daemons that are not running already"""
        return [d for d in self.daemons if d.pid == -1]

    @property
    def daemons_count(self) -> int:
        return len(self.daemons)

    def enter_waiting_stage(self):
        try:
            if len(self.daemons) == 0:
                logger.info("No daemons loaded")
                return
            self.watch()
        except KeyboardInterrupt:
            logger.info("System stopped manually [CTRL+C]")
        except Exception as err:
            logger.exception(err)

        working_time = time.time() - self.start_time
        logger.info(
            f"Ending session...Working time: {time.strftime('%H:%M:%S', time.gmtime(working_time))}"
        )

    def watch(self):
        """Watch for currently running daemons and check their state"""
        while 1:
            deployed_daemons = []
            available_daemons = utils.get_hell_pids(only_pids=True)
            for deployed_daemon in self.deployed_daemons:
                if deployed_daemon.pid in available_daemons:
                    deployed_daemons.append(deployed_daemon)
                    logger.success(
                        f"Daemon {deployed_daemon.name} still running with PID {deployed_daemon.pid}..."
                    )
                else:
                    deployed_daemon.pid = -1
                    logger.warning(
                        f"Daemon {deployed_daemon.name} with PID {deployed_daemon.pid} is no longer running..."
                    )

            self.deployed_daemons = deployed_daemons
            if len(deployed_daemons) > 0:
                for daemon in self.stale_daemons:
                    if daemon not in self.deployed_daemons:
                        logger.debug(f"Daemon {daemon.name} still not running...")
                    else:
                        logger.warning(f"Daemon {daemon.name} no longer running...")

            if len(self.running_daemons) == 0:
                logger.warning("No daemons running...")
                return

            time.sleep(constants.WATCHER_SLEEP_TIME.total_seconds())

    def log_daemons_data(self) -> None:
        """Log a list of daemons"""
        for daemon in self.daemons:
            daemon.log_information()
            # running_time = time.time() - daemon.deploy_time
            # logger.debug(f"Running time: {time.strftime('%H:%M:%S', time.gmtime(running_time))}")

    def update_constants(self, config: dict) -> None:
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

    def load_config(self) -> dict:
        """Load the config file"""
        if not os.path.exists(constants.DAEMONS_CONFIG_PATH):
            logger.critical(f"Config file not found at {constants.DAEMONS_CONFIG_PATH}")
            return {}

        with open(
            constants.DAEMONS_CONFIG_PATH, "r", encoding=constants.ENCODING
        ) as file:
            config = yaml.safe_load(file)  # yaml.load(file, Loader=yaml.FullLoader)

        if config in [None, {}]:
            logger.critical("Config file is empty")
            return {}

        return config

    def create_daemon(self, name: str, config: dict) -> Daemon:
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

        daemon_directory = config.get("dir", name)
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
            name,
            target,
            daemon_directory,
            requirements_needed,
            requirements,
            arguments,
            auto_restart,
            use_venv,
        )

        return daemon

    def run_daemons(self, config: dict) -> None:
        """Load daemons from a given path"""

        if not config["daemons"]:
            logger.warning("No daemons configs found")
            return False

        for daemon_name in config["daemons"]:
            daemon_config = config["daemons"][daemon_name]
            daemon = self.create_daemon(daemon_name, daemon_config)
            if not daemon is None:
                self.add_daemon(daemon)
                if daemon.auto_restart:
                    self.auto_restart_list.append(daemon.name)

        count = len(self.daemons)

        if not count:
            logger.warning("System encountered problems while checking daemons data")
            return False

        logger.info(f"Loaded {count} daemons")

        return self.deploy_all()

    def add_daemon(self, daemon: Daemon) -> None:
        """Add a daemon to the list of daemons"""
        if daemon.target_path in [d.target_path for d in self.daemons]:
            logger.error(f"Daemon {daemon.name} already exists")
            return

        self.daemons.append(daemon)
        logger.success(f'Loaded "{daemon.name}" daemon')

    def init_daemon(self, target_name: str) -> bool:
        """Initialize a daemon"""
        daemon = next(filter(lambda d: d.name == target_name, self.daemons))
        success = daemon.deploy()
        if not success:
            return False

        self.deployed_daemons.append(daemon)
        return True

    def deploy_all(self) -> None:
        """Deploy all daemons"""
        if not self.daemons:
            logger.critical("No daemons loaded for deploing")
            return

        errors = 0

        for daemon in self.daemons:
            errors += not daemon.deploy()
        errors = abs(errors)

        if not errors:
            logger.success(
                f"System initialized and deployed all daemons ({self.daemons_count})"
            )
        else:
            logger.info(
                f"System encountered {errors} failure(s) and deployed {self.daemons_count - errors} daemon(s)"
            )

        if errors == self.daemons_count:
            return False

        return True

    def kill_daemon(self, target_name: str) -> bool:
        """Kill a daemon"""
        daemon = next(filter(lambda d: d.name == target_name, self.running_daemons))
        if daemon is None or daemon.pid == -1:
            logger.warning(f"Daemon {target_name} is not running")
            return False

        success = daemon.kill()
        if not success:
            return False

        self.deployed_daemons.remove(daemon)
        return True

    def kill_all(self) -> None:
        """Kill all running daemons"""
        for daemon in self.running_daemons:
            daemon.kill()

        logger.info("System killed all daemons")


if __name__ == "__main__":
    hell = Hell(autostart_enabled=True)
