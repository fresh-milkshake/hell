''' a '''

import os
import time
from typing import List, Tuple

import psutil
import yaml
from loguru import logger

import constants

logger.add(sink=os.path.join(constants.PROJECT_PATH, "hell.log"),
           format="{time} {level} {message}",
           level="DEBUG",
           rotation="1 week",
           compression="zip",
           retention="10 days")


def get_hell_pids(path_prefix: str = constants.DAEMONS_PATH,
                  only_pids=False) -> Tuple[int, str] or List[int] or List:
    ''' Return list of "hell" pids '''
    pids = []
    for proc in psutil.process_iter(attrs=['pid', 'name', 'cmdline']):
        try:
            pinfo = proc.info
        except psutil.NoSuchProcess:
            return []

        if pinfo['name'] == 'python3':
            file = pinfo['cmdline'][1]
            if file.startswith(path_prefix):
                pids.append(pinfo['pid'] if only_pids else (pinfo['pid'],
                                                            file))
    return pids


class Daemon:
    ''' Class for running the daemon '''
    requirements_command = 'pip3 install -r '
    python_command = 'python3'

    def __init__(self,
                 name: str,
                 target_path: str,
                 daemon_dir: str,
                 requirements_path: str) -> None:

        self.name = name
        self.target_path = target_path
        self.daemon_dir = daemon_dir
        self.requirements_path = requirements_path

        self.dependancies_installed = False
        self.deploy_time = 0
        self.pid = -1

        self.deploy_time = 0
        self.deployed_once = False

    def get_dependencies(self) -> List[str]:
        ''' Return a list of dependencies for the daemon '''
        logger.debug(
            f"Opening {self.requirements_path.split('/daemons/')[-1]} to get dependencies..."
        )
        if os.path.exists(self.requirements_path):
            with open(self.requirements_path, 'r', encoding=constants.ENCODING) as file:
                return file.read().splitlines()
        else:
            return 'No requirements found for this daemon'

    def install_dependancies(self) -> bool:
        ''' Install dependancies for the daemon, and return True if successful '''
        logger.info(f"Installing dependancies for {self.name}...")
        if not os.path.exists(self.requirements_path):
            logger.warning(
                f"Failed to install dependancies for {self.name} because no requirements.txt was found"
            )
            return False

        if os.system(
                f'{self.requirements_command} "{self.requirements_path}" > /dev/null'
        ) != 0:
            logger.error(f"Failed to install dependancies for {self.name}")
            return False

        dependencies = self.get_dependencies()
        logger.success(f"Daemon dependancies: {', '.join(dependencies)}")
        self.dependancies_installed = True
        return True

    def kill(self) -> bool:
        ''' Kill the daemon, and return True if successful '''
        if self.pid == -1:
            logger.error(
                f"Failed to kill {self.name} because it is not running")
            return False

        os.system(f"kill -9 {self.pid}")
        logger.success(f"Successfully killed {self.name} with PID {self.pid}")
        self.pid = -1
        return True

    def deploy(self) -> bool:
        ''' Deploy the daemon, and return True if successful '''
        logger.info(f"Deploying {self.name}...")
        if not self.dependancies_installed:
            self.dependancies_installed = self.install_dependancies()
            if not self.dependancies_installed:
                logger.error(
                    f"Failed to deploy {self.name} [dependancies not installed]"
                )
                return False

        command = f'{self.python_command} "{self.target_path}" & > /dev/null'
        code = os.system(command)
        if code != 0:
            logger.error(
                f"Failed to deploy {self.name} [daemon returned code {code}]")
            return False

        for pid, path in get_hell_pids():
            if path == self.target_path:
                self.pid = pid
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
        self.autostart_enabled = autostart_enabled
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
            available_daemons = get_hell_pids(only_pids=True)
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
        ''' Updates global constants like DAEMONS_PATH and other based on config dict '''
        constants.DAEMONS_PATH = config.get('daemonspath')
        logger.debug(constants.DAEMONS_PATH)

    def load_config(self) -> dict:
        ''' Load the config file '''
        if not os.path.exists(constants.DAEMONS_CONFIG_PATH):
            logger.critical(
                f"Config file not found at {constants.DAEMONS_CONFIG_PATH}")
            return {}

        with open(constants.DAEMONS_CONFIG_PATH, "r", encoding=constants.ENCODING) as file:
            config = yaml.load(file, Loader=yaml.FullLoader)

        if config in [None, {}]:
            logger.critical("Config file is empty")
            return {}

        return config

    def load_daemons(self, config: dict, daemons_path: str = constants.DAEMONS_PATH) -> None:
        ''' Load daemons from a given path '''

        autostart = []
        for daemon_name in config["daemons"]:
            daemon_config = config["daemons"][daemon_name]

            daemon_directory = os.path.join(daemons_path, daemon_config["dir"])
            target_path = os.path.join(
                daemon_directory, daemon_config["target"])

            requirements_path = constants.DEFAULT_REQUIREMENTS_PATH
            if daemon_config.get('requirements'):
                requirements_path = os.path.join(daemon_directory, )

            daemon = Daemon(daemon_name, target_path,
                            daemon_directory, requirements_path)
            self.add_daemon(daemon)

            if daemon_config.get("autostart") == 'true':
                autostart.append(daemon_name)
        logger.success(f"Successfully loaded {len(self.daemons)} daemons")

        if self.autostart_enabled:
            logger.info("Autostarting daemons")
            for name in autostart:
                self.init_daemon(name)

    def add_daemon(self, daemon: Daemon) -> None:
        ''' Add a daemon to the list of daemons '''
        if daemon.target_path in [d.target_path for d in self.daemons]:
            logger.error(f"Daemon {daemon.name} already exists")
            return

        self.daemons.append(daemon)
        logger.success(f"Successfully added daemon {daemon.name}")

    def init_daemon(self, target_name: str) -> bool:
        ''' Initialize a daemon '''
        daemon = next(filter(lambda d: d.name == target_name, self.daemons))
        success = daemon.deploy()
        if not success:
            return False

        self.deployed_daemons.append(daemon)
        return True

    def init_all(self) -> None:
        ''' Initialize all daemons '''
        for daemon in self.daemons:
            daemon.deploy()

        logger.info("System initialized all daemons")

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
