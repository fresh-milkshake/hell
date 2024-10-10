from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler

from app.api.limiter import limiter
from app.api.routers import api

app = FastAPI(title="Hell API", description="idk")
app.include_router(api)

app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)
