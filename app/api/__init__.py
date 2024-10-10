from fastapi import FastAPI

from app.api.routers import api

app = FastAPI(title="Hell API", description="idk")
app.include_router(api)
