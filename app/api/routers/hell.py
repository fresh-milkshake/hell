from fastapi import APIRouter, Request, Depends

from app.api.dependencies import hell_is_running, verify_token
from app.manager import Hell

router = APIRouter(prefix="/hell", dependencies=[Depends(verify_token)])


@router.post("/start")
async def start(request: Request):
    if Hell().running:
        return {"success": False, "msg": "Hell is already running"}

    success, msg = await Hell().start()
    return {"success": success, "msg": msg}


@router.post("/stop", dependencies=[Depends(hell_is_running)])
async def stop(request: Request):
    success, msg = await Hell().stop()
    return {"success": success, "msg": msg}


@router.post("/restart", dependencies=[Depends(hell_is_running)])
async def restart(request: Request):
    success, msg = await Hell().restart()
    return {"success": success, "msg": msg}
