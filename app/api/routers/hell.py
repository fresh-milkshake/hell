from fastapi import APIRouter, Request

router = APIRouter(prefix="/hell")


@router.post("/start")
async def start(request: Request):
    pass


@router.post("/stop")
async def stop(request: Request):
    pass


@router.post("/restart")
async def restart(request: Request):
    pass
