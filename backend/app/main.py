"""FastAPI application entry point.

Mounts the versioned API under /api/v1. CORS is opened for the Vite dev
server (localhost:5173). DB migrations auto-run on startup (alembic upgrade
head) so a clean checkout never hits a schema-less SQLite file.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as api_v1_router
from app.db.migrate import run_migrations


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()  # alembic upgrade head
    yield


app = FastAPI(title="Poker Trainer API", version="0.1.0", lifespan=lifespan)

# Dev: Vite (5173) -> FastAPI (8008) is cross-origin. In prod the SPA is
# served same-origin and this is a no-op.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api/v1")
