import os
import time
import yaml
import psutil
from loguru import logger
from typing import List, Tuple

PROJECT_PATH = os.path.dirname(os.path.realpath(__file__))

logger.add(sink=os.path.join(PROJECT_PATH, "hell.log"),
           format="{time} {level} {message}",
           level="DEBUG",
           rotation="1 week",
           compression="zip",
           retention="10 days")


def get_hell_pids(only_pids=False) -> Tuple[int, str] or List[int] or List:
    ''' return list of "hell" pids '''
    pids = []
    for proc in psutil.process_iter(attrs=['pid', 'name', 'cmdline']):
        try:
            pinfo = proc.info
        except psutil.NoSuchProcess:
            return []

        if pinfo['name'] == 'python3':
            file = pinfo['cmdline'][1]
            if file.startswith('/home/pi/hell/daemons/'):
                pids.append(pinfo['pid'] if only_pids else (pinfo['pid'],
                                                            file))
    return pids


class Daemon:
    ''' Class for running the daemon '''
    requirements_command = 'pip3 install -r '
    python_command = 'python3'

    def __init__(self, name: str, target_path: str, daemon_dir: str) -> None:
        self.name = name
        self.target_path = target_path
        self.daemon_dir = daemon_dir
        self.requirements_path = daemon_dir + "/requirements.txt"

        self.dependancies_installed = False
        self.pid = -1
        self.deploy_time = 0

    def get_dependencies(self) -> List[str]:
        ''' Return a list of dependencies for the daemon '''
        logger.debug(
            f"Opening {self.requirements_path.split('/daemons/')[-1]} to get dependencies..."
        )
        if os.path.exists(self.requirements_path):
            with open(self.requirements_path, 'r') as f:
                return f.read().splitlines()
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
                return True
        else:
            logger.error(f"Failed to deploy {self.name}")
            return False


class Hell:
    ''' Class "Manager" for daemons deployment and killing '''
    DAEMONS_PATH = os.path.join(PROJECT_PATH, "daemons")
    CONFIG_PATH = os.path.join(PROJECT_PATH, "daemons.yaml")
    SLEEP_TIME = 60 * 20

    def __init__(self, autostart_enabled=False) -> None:
        self.daemons: List[Daemon] = []
        self.deployed_daemons: List[Daemon] = []
        self.autostart_enabled = autostart_enabled
        self.start_time = time.time()

        try:
            self.load_daemons()
            if len(self.daemons) == 0:
                logger.critical("No daemons loaded")
                return
            self.watch()
        except KeyboardInterrupt as e:
            pass
        except Exception as e:
            logger.exception(e)
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
        ''' Return a list of daemons that are not running '''
        return [d for d in self.daemons if d.pid == -1]

    def watch(self):
        ''' watach for currently running daemons '''
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
                        f"Daemon {deployed_daemon.name} with PID {deployed_daemon.pid} is not longer running..."
                    )

            self.deployed_daemons = deployed_daemons
            if len(deployed_daemons) > 0:
                for daemon in self.stale_daemons:
                    if daemon not in self.deployed_daemons:
                        logger.debug(
                            f"Daemon {daemon.name} still not running...")
                    else:
                        logger.warning(
                            f"Daemon {daemon.name} is not longer running...")
                        
            if len(self.running_daemons) == 0:
                logger.warning("No daemons running...")
                return

            time.sleep(Hell.SLEEP_TIME)

    def log_daemons(self) -> None:
        ''' Log a list of daemons '''
        for daemon in self.daemons:
            logger.debug(f"Daemon: {daemon.name} [PID: {daemon.pid}]")
            logger.debug(f"Target: {daemon.target_path}")
            logger.debug(
                f"Requirements: {', '.join(daemon.get_dependencies()) if daemon.dependancies_installed else 'No requirements'}")
            logger.debug(
                f"Deploiement time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(daemon.deploy_time))}"
            )
            # running_time = time.time() - daemon.deploy_time
            # logger.debug(f"Running time: {time.strftime('%H:%M:%S', time.gmtime(running_time))}")

    def load_config(self) -> dict:
        ''' Load the config file '''
        if not os.path.exists(Hell.CONFIG_PATH):
            logger.critical(f"Config file not found at {Hell.CONFIG_PATH}")
            return {}
        
        with open(Hell.CONFIG_PATH, "r") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
            
        if config in [None, {}]:
            logger.critical(f"Config file is empty")
            return {}
        
        return config

    def load_daemons(self, path: str = DAEMONS_PATH) -> None:
        ''' Load daemons from a given path '''
        config = self.load_config()
        if config == {}:
            return
        
        autostart = []
        for daemon_name in config["daemons"]:
            daemon = config["daemons"][daemon_name]
            ddir = path + daemon["dir"]
            target_path = ddir + daemon["target"]
            self.add_daemon(Daemon(daemon['name'], target_path, ddir))
            if daemon["autostart"]:
                autostart.append(daemon["name"])
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
