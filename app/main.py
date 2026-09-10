from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.complaints import router as complaints_router
from app.api.auth import router as auth_router
from app.api.pages import router as pages_router
from app.db import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth_router)
app.include_router(complaints_router)
app.include_router(pages_router)


@app.get("/")
def root():
    return {"status": "ok"}