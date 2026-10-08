from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401  테이블 생성 전에 모델을 등록한다
from app.core.errors import register_exception_handlers
from app.core.security import prepare_dummy_password_hash
from app.db.session import create_tables
from app.routers import auth


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    create_tables()
    prepare_dummy_password_hash()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="fastapi-auth-api", lifespan=lifespan)
    register_exception_handlers(app)
    app.include_router(auth.router, prefix="/api/v1")
    return app


app = create_app()
