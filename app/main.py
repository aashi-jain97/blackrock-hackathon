from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.security import ApiKeyMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware
from app.repositories.factory import create_metrics_repository


@asynccontextmanager
async def lifespan(app: FastAPI):
    repo = create_metrics_repository()
    repo.initialize()
    app.state.metrics_repo = repo
    yield


app = FastAPI(
    title="Save For Your Retirement",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(ApiKeyMiddleware)

app.include_router(router)
