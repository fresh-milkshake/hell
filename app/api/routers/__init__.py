from fastapi import APIRouter

from .access import router as access_router
from .daemons import router as daemons_router
from .hell import router as hell_router

api = APIRouter(prefix="/api")
api.include_router(daemons_router)
api.include_router(hell_router)
api.include_router(access_router)
