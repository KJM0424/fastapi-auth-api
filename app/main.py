from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401  테이블 생성 전에 모델을 등록한다
from app.core.errors import register_exception_handlers
from app.db.session import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    create_tables()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="fastapi-auth-api", lifespan=lifespan)
    register_exception_handlers(app)
    return app


app = create_app()
