from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.api import dependencies, schemas
from app.api.dependencies import verify_api_key
from app.manager.daemon import Daemon, DaemonStatus
from app.manager.hell import Hell

router = APIRouter(prefix="/daemons")


@router.get("/daemons/", response_model=schemas.DaemonList)
async def list_daemons(
        hell: Hell = Depends(dependencies.get_hell_instance),
        _: str = Depends(verify_api_key),
):
    """List all daemons and their statuses"""
    return schemas.DaemonList(
        daemons=[
            schemas.Daemon(
                name=daemon.name,
                directory=str(daemon.project_folder),
                main_file=str(daemon.main_file),
                requirements_path=str(daemon.requirements_path)
                if daemon.requirements_path
                else "None",
                auto_restart=daemon.restart_if_stopped,
                arguments=daemon.main_file_arguments,
                use_virtualenv=daemon.use_virtualenv,
                dependancies_installed=daemon.dependencies_installed,
                deployed_once=daemon.deployed_once,
                deployed_at=daemon.deployed_at,
                virtualenv_path=str(daemon.virtualenv_path)
                if daemon.virtualenv_path
                else "None",
                pid=daemon.PID,
            )
            for daemon in hell.daemons
        ],
        count=len(hell.daemons),
        timestamp=datetime.now().timestamp(),
    )


@router.post("/daemons/{daemon_name}/start", response_model=schemas.DaemonResponse)
async def start_daemon(
        daemon: Daemon = Depends(dependencies.get_daemon),
        api_key: str = Depends(verify_api_key),
):
    """Start a specific daemon"""
    if daemon.deploy():
        return schemas.DaemonResponse(status=DaemonStatus.RUNNING, name=daemon.name)
    else:
        raise HTTPException(status_code=500, detail="Failed to start daemon")


@router.post("/daemons/{daemon_name}/stop", response_model=schemas.DaemonResponse)
async def stop_daemon(
        daemon: Daemon = Depends(dependencies.get_daemon),
        api_key: str = Depends(verify_api_key),
):
    """Stop a specific daemon"""
    if daemon.kill():
        return schemas.DaemonResponse(status=DaemonStatus.STOPPED, name=daemon.name)
    else:
        raise HTTPException(status_code=500, detail="Failed to stop daemon")
