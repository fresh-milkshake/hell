import shutil
import subprocess
from loguru import logger
import platform
from subprocess import Popen, PIPE, TimeoutExpired
from typing import Optional, Tuple, Union
from app.local.utils import singleton


class Cmd:
    """Class for building commands out of strings"""

    def __init__(self, *subcommands: str):
        self.subcommands = list(subcommands)

    def __str__(self):
        return " ".join(subcommand for subcommand in self.subcommands)

    def __add__(self, other: "Cmd") -> "Cmd":
        return Cmd(*self.subcommands, *other.subcommands)

    def __iadd__(self, other: Union["Cmd", list["Cmd"], str, list[str]]) -> "Cmd":
        if isinstance(other, Cmd):
            self.subcommands.extend(other.subcommands)
        elif isinstance(other, str):
            self.subcommands.append(other)
        elif isinstance(other, list):
            for item in other:
                if isinstance(item, Cmd):
                    self.subcommands.extend(item.subcommands)
                elif isinstance(item, str):
                    self.subcommands.append(item)
                else:
                    raise ValueError(f"Unsupported type: {type(other)}")
        else:
            raise ValueError(f"Unsupported type: {type(other)}")
        return self

    def concat(self, *others: "Cmd") -> "Cmd":
        new_subcommands = list(self.subcommands)
        for other in others:
            new_subcommands.extend(other.subcommands)
        return Cmd(*new_subcommands)

    def verify(self) -> bool:
        """
        Verify if the command is valid and executable.

        Returns:
            bool: True if the command is valid, False otherwise.
        """
        command_sequence = str(self)
        logger.debug(f"Verifying command: {command_sequence}")
        if not self.subcommands:
            logger.error("No command provided to verify.")
            return False

        executable = (
            self.subcommands[0]
            if platform.system() == "Windows"
            else shutil.which(self.subcommands[0])
        )
        if not executable:
            logger.error(f"Executable '{executable}' not found.")
            return False

        return True

    def execute_blocking(
        self, show_output: bool = False, timeout: int = 0
    ) -> Tuple[int, str]:
        """
        Execute the command represented by this Cmd instance.

        Args:
            show_output (bool): Whether to print the output in real-time.
            timeout (int): Maximum time in seconds for the command to complete.

        Returns:
            Tuple[int, str]: A tuple containing the exit code and the full output.
        """
        return Executor().execute(
            self, show_output=show_output, timeout=timeout, blocking=True
        )  # type: ignore

    def execute_in_process(self, show_output: bool = False, timeout: int = 0) -> Popen:
        """
        Execute the command represented by this Cmd instance.

        Args:
            show_output (bool): Whether to print the output in real-time.
            timeout (int): Maximum time in seconds for the command to complete.

        Returns:
            subprocess.Popen: A Popen object representing the process running a command.
        """
        return Executor().execute(
            self, show_output=show_output, timeout=timeout, blocking=False
        )  # type: ignore


@singleton
class Executor:
    """Primary executor for Cmd objects"""

    def __init__(self):
        self.history = []

    def execute(
        self,
        cmd: Cmd,
        show_output: bool = False,
        timeout: Optional[float] = None,
        blocking: bool = True,
    ) -> Tuple[int, str] | Popen:
        """
        Execute a Cmd object and return the exit code and output.

        Args:
            cmd (Cmd): The command to execute.
            show_output (bool): Whether to print the output in real-time.
            timeout (int): Maximum time in seconds for the command to complete.

        Returns:
            Tuple[int, str]: A tuple containing the exit code and the full output.
        """
        command_sequence = str(cmd)
        self.history.append(command_sequence)

        if blocking:
            return self._execute_command(
                command_sequence, show_output=show_output, timeout=timeout
            )
        else:
            return self._return_process(command_sequence)

    def _execute_command(
        self,
        command_sequence: str,
        show_output: bool = False,
        timeout: Optional[float] = None,
    ) -> Tuple[int, str]:
        logger.debug(f"Running command: {command_sequence}")

        use_shell = platform.system() == "Windows"

        process = Popen(
            command_sequence,
            stdout=PIPE,
            stderr=PIPE,
            text=True,
            shell=use_shell,
        )

        output = []
        try:
            for line in iter(process.stdout.readline, ""):  # type: ignore
                line = line.strip()
                output.append(line)
                if show_output:
                    print(line, flush=True)

            process.wait(timeout=timeout)
        except TimeoutExpired:
            process.kill()
            logger.error(f"Command '{command_sequence}' timed out.")
            raise
        finally:
            if process.stdout:
                process.stdout.close()
            if process.stderr:
                process.stderr.close()

        code = process.returncode
        full_output = "\n".join(output)

        if code != 0:
            logger.error(
                f"Command '{command_sequence}' failed with exit code {code} and output:\n{full_output}"
            )
        else:
            logger.debug(f"Command '{command_sequence}' executed successfully.")

        return code, full_output

    def _return_process(
        self,
        command_sequence: str,
    ) -> Popen:
        CMD = command_sequence.split(" ")
        try:
            process = Popen(
                CMD,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                close_fds=True,
                shell=False,
            )
            return process
        except Exception as e:
            logger.exception(e)
            raise

    def get_history(self) -> Tuple[str, ...]:
        """Return the history of executed commands."""
        return tuple(self.history)
