from pathlib import Path
from fastapi import Depends, HTTPException
from app.local.hell import Hell
from typing import Optional, Tuple
from app.local.daemon import Daemon


def get_hell_instance() -> Hell:
    return Hell()


def get_daemon(
    hell: Hell = Depends(get_hell_instance),
    daemon_name: Optional[str] = None,
    daemon_pid: Optional[int] = None,
    daemon_file: Optional[Path] = None,
) -> Optional[Daemon]:
    search_methods = [
        (daemon_name, hell.search_daemon_by_name),
        (daemon_pid, hell.search_daemon_by_pid),
        (daemon_file, hell.search_daemon_by_file)
    ]

    for search_param, search_method in search_methods:
        if search_param:
            daemon = search_method(search_param)
            if daemon is None:
                raise HTTPException(status_code=404, detail="Daemon not found")
            return daemon
    return None


def get_hell_and_daemon(
    daemon_name: Optional[str] = None,
) -> Tuple[Hell, Optional[Daemon]]:
    hell = get_hell_instance()
    daemon = get_daemon(hell, daemon_name)
    return hell, daemon
