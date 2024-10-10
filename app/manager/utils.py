"""Utility functions for the 'Hell' project."""

import os
import platform
from pathlib import Path
from typing import List, Tuple, Union

import psutil
from loguru import logger

from app.manager import constants


def get_hell_pids(
        path_prefix: Path = constants.DAEMONS_PATH,  # type: ignore
        only_pids: bool = False,
) -> Union[List[int], List[Tuple[int, str]]]:
    """
    Return a list of 'Hell' process IDs and optionally their associated file paths.

    Args:
        path_prefix (Union[str, Path]): The prefix path to filter processes. Defaults to DAEMONS_PATH.
        only_pids (bool): If True, return only PIDs. If False, return tuples of (PID, file path).

    Returns:
        Union[List[int], List[Tuple[int, str]]]: A list of PIDs or (PID, file path) tuples.
    """
    pids = []
    system = platform.system()

    if system == "Windows":
        python_names = constants.WINDOWS_PYTHON_NAMES
    else:
        python_names = constants.LINUX_PYTHON_NAMES

    path_prefix: str = str(Path(path_prefix).resolve())  # type: ignore

    for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
        # {'pid': 27796, 'name': 'python.exe', 'cmdline': ['C:\\Users\\dev\\AppData\\Local\\Programs\\Python\\Python312\\python.exe', 'd:/code/projects/manager/test.py']}
        try:
            pinfo = proc.info
            cmdline = pinfo.get("cmdline") or []
            if len(cmdline) > 1:
                python_executable = Path(cmdline[0]).name.strip()
                script_path: str = cmdline[1]

                is_python_process = python_executable in python_names

                if is_python_process and script_path.startswith(path_prefix):
                    pid = pinfo["pid"]
                    pids.append(pid if only_pids else (pid, Path(script_path)))
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied:
            logger.warning(f"Access denied for process {pinfo.get('pid', 'unknown')}")
        except Exception as e:
            logger.error(
                f"Unexpected error processing PID {pinfo.get('pid', 'unknown')}: {str(e)}"
            )

    if not pids:
        logger.debug(f"No processes found matching path prefix: {path_prefix}")
    return pids


def send_signal(pid: int, signal: int) -> bool:
    """Send a signal to a process."""
    try:
        os.kill(pid, signal)
        return True
    except OSError as e:
        logger.error(f"Failed to send signal {signal} to process {pid}: {e}")
        return False


def singleton(cls):
    """
    A decorator to create a singleton class.
    This ensures only one instance of the class is created.
    """
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance
