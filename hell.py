''' Main file for the Hell daemon manager. '''

import os
import subprocess
import sys
import time
from typing import List, Tuple

import yaml
from loguru import logger

import constants
import utils

logger.remove()
logger.add(sink=sys.stdout,
           format=constants.LOG_FORMAT_STRING,
           level=constants.LOG_LEVEL,
           colorize=True)
logger.add(sink=os.path.join(constants.PROJECT_PATH, constants.LOG_FILE_NAME),
           format=constants.LOG_FORMAT_STRING,
           level=constants.LOG_LEVEL,
           rotation="1 week",
           compression="zip",
           retention="10 days")


class Daemon:
    ''' Class for running the daemon '''
    requirements_command = 'pip3 install -r '
    python_command = 'python3'

    def __init__(self,
                 name: str,
                 target_path: str,
                 daemon_dir: str,
                 requirements_path: str,
                 arguments: str = '',
                 auto_restart: bool = False,
                 use_virtualenv: bool = True) -> None:
        ''' Initialize Daemon object

        :param name: name of the daemon
        :param target_path: path to the target file
        :param daemon_dir: path to the daemon directory
        :param requirements_path: path to the requirements file
        '''

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

        self.virtualenv_path = os.path.join(self.daemon_dir,
                                            constants.DEFAULT_VIRTUAL_ENV_NAME)

        self._process: subprocess.Popen = None

    @property
    def pid(self) -> int:
        ''' Return the pid of the daemon '''
        if self._process is None:
            return -1
        return self._process.pid

    def get_dependencies(self) -> List[str]:
        ''' Return a list of dependencies for the daemon '''
        logger.debug(
            f'Opening "{self.requirements_path.split(constants.DAEMONS_PATH)[-1]}" to get dependencies...'
        )
        if os.path.exists(self.requirements_path):
            with open(self.requirements_path, 'r',
                      encoding=constants.ENCODING) as file:
                return file.read().splitlines()
        else:
            return 'No requirements found for this daemon'

    def create_virtualenv(self) -> bool:
        ''' Create a virtualenv for the daemon, and return True if successful '''
        logger.info(f"Creating virtualenv for {self.name}...")

        if os.path.exists(self.virtualenv_path):
            logger.warning(
                f"Virtualenv for {self.name} already exists, skipping creation")
            return True
        command = [constants.CMD_PYTHON, '-m', 'venv', self.virtualenv_path]
        code, _ = utils.execute(command)
        if code != 0:
            logger.error(
                f"Failed to create virtual environment for {self.name}")
            return False

        logger.success(f"Created virtual environment for {self.name}")
        return True

    def install_dependancies(self) -> bool:
        ''' Install dependancies for the daemon, and return True if successful '''
        logger.info(f"Installing dependancies for {self.name}...")
        if not os.path.exists(self.requirements_path):
            logger.warning(
                f"Failed to install dependancies for {self.name} because no requirements.txt was found"
            )
            return False

        dependencies = self.get_dependencies()

        if self.use_virtualenv and not self.create_virtualenv():
            return False
        
        pip_command = [os.path.join(self.virtualenv_path, constants.CMD_VENV_PIP_PATH),
                       *constants.CMD_VENV_PIP_INSTALL, self.requirements_path]
        code, _ = utils.execute(pip_command)
        if code != 0:
            logger.error(
                f"Failed to install dependancies for {self.name} [pip returned code {code}]"
            )
            return False

        logger.success(f"Installed dependencies: {', '.join(dependencies)}")
        return True

    def kill(self) -> bool:
        ''' Kill the daemon, and return True if successful '''
        if self.pid == -1:
            logger.error(
                f"Failed to kill {self.name} because it is not running")
            return False

        self._process.terminate()
        # if self._process.poll():
        #     self._process.kill()
        logger.success(f"Successfully killed {self.name} with PID {self.pid}")
        return True

    def deploy(self) -> bool:
        ''' Deploy the daemon, and return True if successful '''
        logger.info(f"Deploying {self.name}...")
        if self.requirements_path is not None and not self.dependancies_installed:
            self.dependancies_installed = self.install_dependancies()
            if not self.dependancies_installed:
                logger.error(
                    f"Failed to deploy {self.name} [dependancies not installed]"
                )
                return False

        python_command = os.path.join(self.virtualenv_path, constants.CMD_VENV_PYTHON_PATH)
        command = [python_command, self.target_path, constants.CMD_DAEMON, *constants.CMD_TO_DEV_NULL]
        self._process = subprocess.Popen(command)
        if self._process.poll():
            logger.error(
                f"Failed to deploy {self.name} [daemon returned code {self._process.returncode}]")
            return False

        for pid, path in utils.get_hell_pids():
            if path == self.target_path and pid == self.pid:
                logger.success(
                    f"Successfully deployed {self.name} with PID {self.pid}")
                self.deploy_time = time.time()
                self.deployed_once = True
                return True

        logger.error(f"Failed to deploy {self.name}")
        return False

    def log_information(self):
        ''' Logs information about Daemon object like pid, name, target path, etc. '''

        logger.debug(f"Daemon: {self.name} [PID: {self.pid}]")
        logger.debug(f"Target: {self.target_path}")

        requirements = 'No requirements'
        if self.dependancies_installed:
            requirements = ', '.join(self.get_dependencies())
            logger.debug(f"Requirements path : {self.requirements_path}")
        logger.debug(f"Requirements: {requirements}")

        timestamp = 'Never'
        if self.deployed_once:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S',
                                      time.localtime(self.deploy_time))
        logger.debug(f"Deploiement timestamp: {timestamp}")


class Hell:
    ''' Class "Manager" for daemons deployment and killing '''

    def __init__(self, autostart_enabled=False) -> None:
        self.daemons: List[Daemon] = []
        self.deployed_daemons: List[Daemon] = []
        self.auto_restart_enabled = autostart_enabled
        self.auto_restart_list: List[Daemon] = []
        self.pending_for_restart: List[Daemon] = []
        self.start_time = time.time()

        config = self.load_config()
        if config == {}:
            return

        self.update_constants(config)
        self.load_daemons(config)

        try:
            if len(self.daemons) == 0:
                logger.critical("No daemons loaded")
                return
            self.watch()
        except KeyboardInterrupt:
            pass
        except Exception as err:
            logger.exception(err)

        working_time = time.time() - self.start_time
        logger.info(
            f"Ending session...Working time: {time.strftime('%H:%M:%S', time.gmtime(working_time))}"
        )
        self.log_daemons()
        self.kill_all()

    @property
    def running_daemons(self) -> List[Daemon]:
        ''' Return a list of currently running daemons '''
        return [d for d in self.daemons if d.pid != -1]

    @property
    def stale_daemons(self) -> List[Daemon]:
        ''' Return a list of daemons that are not running already '''
        return [d for d in self.daemons if d.pid == -1]

    def watch(self):
        ''' Watch for currently running daemons and check their state '''
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
                        logger.debug(
                            f"Daemon {daemon.name} still not running...")
                    else:
                        logger.warning(
                            f"Daemon {daemon.name} no longer running...")

            if len(self.running_daemons) == 0:
                logger.warning("No daemons running...")
                return

            time.sleep(constants.WATCHER_SLEEP_TIME)

    def log_daemons(self) -> None:
        ''' Log a list of daemons '''
        for daemon in self.daemons:
            daemon.log_information()
            # running_time = time.time() - daemon.deploy_time
            # logger.debug(f"Running time: {time.strftime('%H:%M:%S', time.gmtime(running_time))}")

    def update_constants(self, config: dict) -> None:
        ''' Updates global constants like DAEMONS_PATH and other based on config dict. 
        
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
        '''
        constants.DAEMONS_PATH = config.get('daemons-path',
                                            constants.DAEMONS_PATH)
        constants.DEFAULT_ARGUMENTS = config.get('default-args',
                                                 constants.DEFAULT_ARGUMENTS)
        constants.DEFAULT_USE_VIRTUAL_ENV = config.get(
            'default-venv', constants.DEFAULT_USE_VIRTUAL_ENV)
        constants.DEFAULT_AUTO_RESTART = config.get(
            'default-auto-restart', constants.DEFAULT_AUTO_RESTART)

    def load_config(self) -> dict:
        ''' Load the config file '''
        if not os.path.exists(constants.DAEMONS_CONFIG_PATH):
            logger.critical(
                f"Config file not found at {constants.DAEMONS_CONFIG_PATH}")
            return {}

        with open(constants.DAEMONS_CONFIG_PATH,
                  "r",
                  encoding=constants.ENCODING) as file:
            config = yaml.safe_load(
                file)  # yaml.load(file, Loader=yaml.FullLoader)

        if config in [None, {}]:
            logger.critical("Config file is empty")
            return {}

        return config

    def create_daemon(self, name: str, config: dict) -> Daemon:
        ''' Create a daemon from a given config dict.
        
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
            requirements: <path-to-requirements.txt>
            # Whether to restart the daemon if it crashes, or not
            # by default its False
            auto-restart: <True/False/true/false>
            # Whether to use virtual environment for dependencies, or
            # use global dependencies, by default its False
            virtualenv: <True/False/true/false>
        '''

        daemon_directory = config.get("dir", name)
        daemon_directory = os.path.join(constants.DAEMONS_PATH,
                                        daemon_directory)
        if not os.path.exists(daemon_directory):
            logger.critical(f"Daemon directory {daemon_directory} not found")
            return None

        target = config.get("target", constants.DEFAULT_TARGET_PATH)
        target = os.path.join(constants.DAEMONS_PATH, daemon_directory, target)
        if not os.path.exists(target):
            logger.critical(f"Target file {target} not found")
            return None

        requirements = config.get("requirements", None)
        if requirements == 'default':
            requirements = os.path.join(constants.DAEMONS_PATH,
                                        daemon_directory,
                                        constants.DEFAULT_REQUIREMENTS_PATH)
        elif not requirements is None:
            requirements = os.path.join(constants.DAEMONS_PATH,
                                        daemon_directory, requirements)
        if requirements:
            if not os.path.exists(requirements):
                logger.critical(f"Requirements file {requirements} not found")
                return None

        arguments = config.get("arguments", constants.DEFAULT_ARGUMENTS)
        auto_restart = config.get("auto-restart",
                                  constants.DEFAULT_AUTO_RESTART)
        use_venv = config.get("use-venv", constants.DEFAULT_USE_VIRTUAL_ENV)

        daemon = Daemon(name, target, daemon_directory, requirements,
                        arguments, auto_restart, use_venv)

        return daemon

    def load_daemons(self,
                     config: dict,
                     daemons_path: str = constants.DAEMONS_PATH) -> None:
        ''' Load daemons from a given path '''

        for daemon_name in config["daemons"]:
            daemon_config = config["daemons"][daemon_name]
            daemon = self.create_daemon(daemon_name, daemon_config)
            if not daemon is None:
                self.add_daemon(daemon)
                if daemon.auto_restart:
                    self.auto_restart_list.append(daemon.name)

        logger.info(f"Loaded {len(self.daemons)} daemons")
        self.deploy_all()

    def add_daemon(self, daemon: Daemon) -> None:
        ''' Add a daemon to the list of daemons '''
        if daemon.target_path in [d.target_path for d in self.daemons]:
            logger.error(f"Daemon {daemon.name} already exists")
            return

        self.daemons.append(daemon)
        logger.success(f'Loaded "{daemon.name}" daemon')

    def init_daemon(self, target_name: str) -> bool:
        ''' Initialize a daemon '''
        daemon = next(filter(lambda d: d.name == target_name, self.daemons))
        success = daemon.deploy()
        if not success:
            return False

        self.deployed_daemons.append(daemon)
        return True

    def deploy_all(self) -> None:
        ''' Deploy all daemons '''
        errors = 0

        for daemon in self.daemons:
            errors += int(~daemon.deploy())
        errors = abs(errors)

        if errors == 0:
            logger.success("System initialized and deployed all daemons")
        else:
            logger.error(
                f"System encountered {errors} failures and deployed {len(self.daemons) - errors} daemons"
            )

    def kill_daemon(self, target_name: str) -> bool:
        ''' Kill a daemon '''
        daemon = next(
            filter(lambda d: d.name == target_name, self.running_daemons))
        if daemon is None or daemon.pid == -1:
            logger.warning(f"Daemon {target_name} is not running")
            return False

        success = daemon.kill()
        if not success:
            return False

        self.deployed_daemons.remove(daemon)
        return True

    def kill_all(self) -> None:
        ''' Kill all running daemons '''
        for daemon in self.running_daemons:
            daemon.kill()

        logger.info("System killed all daemons")


if __name__ == "__main__":
    hell = Hell(autostart_enabled=True)
