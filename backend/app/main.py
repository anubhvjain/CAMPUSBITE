import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, engine
from app.middleware import RequestLoggingMiddleware
from app.routers import ai, auth, delivery, orders, owner, restaurants
from app.tasks import reminder_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    stop_event = asyncio.Event()
    task = asyncio.create_task(reminder_loop(stop_event)) if settings.enable_background_tasks else None
    yield
    stop_event.set()
    if task:
        await task


app = FastAPI(
    title="CampusBite API",
    description="Restaurant ordering & delivery platform for customers, restaurant owners and delivery partners.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time", "X-Request-ID"],
)

for r in (auth, restaurants, orders, owner, delivery, ai):
    app.include_router(r.router, prefix="/api")


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
