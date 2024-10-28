from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.api import dependencies, schemas
from app.api.dependencies import verify_token
from app.manager.daemon import Daemon
from app.manager.hell import Hell

router = APIRouter(
    prefix="/daemons",
    dependencies=[Depends(verify_token), Depends(dependencies.hell_is_running)],
)


def schema_from_daemon(daemon: Daemon):
    return schemas.DaemonData.from_daemon(daemon)


@router.get("/", response_model=schemas.DaemonList)
async def list_daemons(
        hell: Hell = Depends(dependencies.get_hell_instance),
):
    """List all daemons and their statuses"""
    daemons = hell.get_all_daemons()
    return schemas.DaemonList(
        daemons=[schema_from_daemon(daemon) for daemon in daemons],
        count=len(daemons),
        timestamp=datetime.now().timestamp(),
    )


@router.post("/{daemon_name}/start")
async def start_daemon(
        daemon: Daemon = Depends(dependencies.get_daemon),
):
    """Start a specific daemon"""
    if daemon.start():
        return {"success": True, "message": "Daemon started"}
    else:
        raise HTTPException(status_code=500, detail="Failed to start daemon")


@router.post("/{daemon_name}/stop")
async def stop_daemon(
        daemon: Daemon = Depends(dependencies.get_daemon),
):
    """Stop a specific daemon"""
    if daemon.stop():
        return {"success": True, "message": "Daemon stopped"}
    else:
        raise HTTPException(status_code=500, detail="Failed to stop daemon")


@router.post("/{daemon_name}/restart")
async def restart_daemon(
        daemon_name: str,
):
    """Restart a specific daemon"""
    success, msg = await Hell().restart_daemon(daemon_name)
    return {"success": success, "message": msg}
