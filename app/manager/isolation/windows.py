import os
from pathlib import Path

from loguru import logger
from psutil import Popen

from ..constants import WSB_TEMPLATE_PATH
from ..daemon.structures import Config
from ..executor import Cmd


class WindowsIsolationProvider:
    SANDBOX_EXE_PATH = Path(r"C:\Windows\system32\WindowsSandbox.exe")

    def __init__(self, config: Config):
        self.config = config

    @staticmethod
    def _check_windows_sandbox():
        if WindowsIsolationProvider.SANDBOX_EXE_PATH.exists():
            return True

        for path in os.environ["PATH"].split(";"):
            if os.path.isfile(os.path.join(path, "WindowsSandbox.exe")):
                return True

        return False

    def _create_sandbox(self, command: Cmd):
        config_file = self.config.daemon_parent_folder / "config.wsb"

        if not WSB_TEMPLATE_PATH.exists():
            raise FileNotFoundError("WSB template not found")

        template = WSB_TEMPLATE_PATH.read_text()
        template = template.replace("{{HOST_FOLDER}}", str(self.config.daemon_folder))
        template = template.replace("{{SANDBOX_FOLDER}}", r"C:\sandbox")
        template = template.replace("{{COMMAND}}", str(command))

        config_file.touch(exist_ok=True)
        config_file.write_text(template)

        process = Cmd(
            "start",
            "WindowsSandbox",
            str(config_file)
        ).execute_in_process()

        if not process.is_running():
            raise RuntimeError("Failed to start sandbox")

        return process

    def run_cmd(self, command: Cmd) -> Popen:
        if not self._check_windows_sandbox():
            logger.warning("Attention! WindowsSandbox not found, process isolation will be disabled")
            return command.execute_in_process()

        return self._create_sandbox(command)
