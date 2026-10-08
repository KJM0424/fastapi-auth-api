import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

# 스펙에 정의된 HTTP 예외만 공통 형식으로 바꾼다 (docs/api-spec.md 에러 코드 목록)
HTTP_ERRORS: dict[int, tuple[str, str]] = {
    status.HTTP_404_NOT_FOUND: ("NOT_FOUND", "요청한 경로를 찾을 수 없습니다"),
    status.HTTP_405_METHOD_NOT_ALLOWED: ("METHOD_NOT_ALLOWED", "허용되지 않은 메서드입니다"),
}
VALIDATION_ERROR = ("VALIDATION_ERROR", "요청 형식이 올바르지 않습니다")
INTERNAL_ERROR = ("INTERNAL_ERROR", "서버 내부 오류가 발생했습니다")


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def error_response(
    status_code: int, code: str, message: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": code, "message": message},
        headers=headers,
    )


async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return error_response(exc.status_code, exc.code, exc.message)


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    code, message = VALIDATION_ERROR
    return error_response(status.HTTP_422_UNPROCESSABLE_CONTENT, code, message)


async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if exc.status_code not in HTTP_ERRORS:
        logger.error("스펙에 없는 HTTP 예외: %s %s", exc.status_code, exc.detail)
        code, message = INTERNAL_ERROR
        return error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, code, message)
    code, message = HTTP_ERRORS[exc.status_code]
    return error_response(exc.status_code, code, message, headers=exc.headers)


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("처리되지 않은 예외", exc_info=exc)
    code, message = INTERNAL_ERROR
    return error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, code, message)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_unexpected_error)
