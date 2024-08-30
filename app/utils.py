""" Utility functions for the 'Hell' project. """

import os
import subprocess
from typing import List, Tuple, Union
from loguru import logger
import psutil
from app import constants


def execute_command(
    command_sequence: List[str],
    show_output: bool = False,
    exception_on_error: bool = False,
) -> Tuple[int, str]:
    """Execute a command sequence and return the exit code and the output."""
    if not isinstance(command_sequence, list):
        raise TypeError(
            f"Command sequence must be a list, not {type(command_sequence).__name__}"
        )

    process = subprocess.Popen(
        command_sequence,
        stdout=subprocess.PIPE if show_output else subprocess.DEVNULL,
        stderr=subprocess.STDOUT if show_output else subprocess.DEVNULL,
        text=True,  # Automatically decodes output as text
    )

    output = []
    if show_output and process.stdout:
        for line in iter(process.stdout.readline, ""):
            output.append(line.strip())
            print(line.strip())

    process.wait()
    code = process.returncode
    full_output = "\n".join(output)

    if exception_on_error and code != 0:
        raise RuntimeError(
            f"Command {command_sequence} failed with exit code {code} and output:\n{full_output}"
        )
    return code, full_output


def get_hell_pids(
    path_prefix: str = str(constants.DAEMONS_PATH), only_pids: bool = False
) -> Union[List[int], List[Tuple[int, str]]]:
    """Return list of 'Hell' pids."""
    pids = []
    for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
        try:
            pinfo = proc.info
        except psutil.NoSuchProcess:
            continue

        if pinfo["name"] == constants.CMD_PYTHON and len(pinfo["cmdline"]) > 1:
            file = pinfo["cmdline"][1]
            if file.startswith(path_prefix):
                pids.append(pinfo["pid"] if only_pids else (pinfo["pid"], file))
    return pids


def send_signal(pid: int, signal: int) -> bool:
    """Send a signal to a process."""
    try:
        os.kill(pid, signal)
        return True
    except OSError as e:
        logger.error(f"Failed to send signal {signal} to process {pid}: {e}")
        return False