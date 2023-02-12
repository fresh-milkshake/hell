''' Utility functions for the "Hell" project. '''

import subprocess
from typing import List, Tuple

import psutil

import constants


def execute(command_sequence, show_output=False, exception_on_error=False) -> Tuple[int, str]:
    ''' Execute a command sequence and return the exit code and the output. '''
    if not isinstance(command_sequence, list):
        raise Exception(
            f"Command sequence must be a list, not {type(command_sequence)}")
    process = subprocess.Popen(command_sequence,
                               stdout=subprocess.PIPE if show_output else subprocess.DEVNULL,
                               stderr=subprocess.STDOUT if show_output else subprocess.DEVNULL)

    code, output = 0, ''
    while process.poll() is None:
        if show_output:
            output = process.stdout.readline().decode(constants.ENCODING).strip()
            if output:
                print(output)

    code = process.returncode
    
    if exception_on_error and code != 0:
        raise Exception(
            f"Command {command_sequence} failed with exit code {code} and output {output}"
        )
    return (code, output)


def get_hell_pids(path_prefix: str = constants.DAEMONS_PATH,
                  only_pids=False) -> Tuple[int, str] or List[int] or List:
    ''' Return list of "Hell" pids '''
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