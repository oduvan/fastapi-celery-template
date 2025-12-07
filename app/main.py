"""Main application module."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.celery_tasks.router import router as celery_router
from app.core.config import settings
from app.files.router import router as files_router
from app.items.router import router as items_router
from app.pages.router import router as pages_router
from app.tasks.router import router as tasks_router
from app.websocket.router import router as websocket_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan events."""
    # Startup
    redis = aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")

    yield

    # Shutdown
    await redis.close()


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Include domain routers
app.include_router(items_router, prefix="/items", tags=["items"])
app.include_router(files_router, prefix="/files", tags=["files"])
app.include_router(websocket_router, prefix="/ws", tags=["websocket"])
app.include_router(tasks_router, prefix="/tasks", tags=["background-tasks"])
app.include_router(celery_router, prefix="/celery", tags=["celery-tasks"])
app.include_router(pages_router, prefix="/pages", tags=["pages"], include_in_schema=False)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to FastAPI Basic Template",
        "docs": "/docs",
        "redoc": "/redoc",
        "version": settings.APP_VERSION,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
