from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

from app.api.constants import API_KEY_HEADER_NAME
from app.api.models import APIKey
from app.manager.daemon import Daemon
from app.manager.hell import Hell

api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)


def get_hell_instance() -> Hell:
    return Hell()


def hell_is_running(hell: Hell = Depends(get_hell_instance)) -> bool:
    if not hell.running:
        raise HTTPException(status_code=404, detail="Hell is not running")
    return True


def verify_token(api_key: str = Depends(api_key_header)):
    key: Optional[APIKey] = APIKey.select().where(APIKey.token == api_key).first()
    if not key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    key.last_used = datetime.now()
    key.save()
    return api_key


def get_daemon(
    hell: Hell = Depends(get_hell_instance),
    daemon_name: Optional[str] = None,
    daemon_pid: Optional[int] = None,
    daemon_file: Optional[Path] = None,
) -> Daemon:
    search_methods = [
        (daemon_name, hell.search_daemon_by_name),
        (daemon_pid, hell.search_daemon_by_pid),
        (daemon_file, hell.search_daemon_by_file),
    ]

    for search_param, search_method in search_methods:
        if search_param:
            daemon = search_method(search_param)
            if daemon:
                return daemon

    raise HTTPException(status_code=404, detail="Daemon not found")
