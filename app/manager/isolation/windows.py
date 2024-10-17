from psutil import Popen

from ..constants import WSB_TEMPLATE_PATH
from ..daemon.structures import Config
from ..executor import Cmd


class WindowsIsolationProvider:
    def __init__(self, config: Config):
        self.config = config

    def run_in_sandbox(self, command: Cmd) -> Popen:
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
