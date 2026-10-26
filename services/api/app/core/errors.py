# CulturalWalk API · 统一错误
"""错误包格式唯一定义处：{"error": {code, message, request_id, details[]}}。

约定见 docs/03-接口契约规范.md §1.4。前端按 code 分支，不按 message 文案。
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """业务错误基类。code 用大写下划线，http_status 决定状态码。"""

    http_status: int = 400
    code: str = "BAD_REQUEST"

    def __init__(
        self,
        message: str = "请求无法处理",
        *,
        details: list[dict[str, Any]] | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or []
        if code:
            self.code = code


class Unauthorized(AppError):
    http_status = 401
    code = "UNAUTHORIZED"


class Forbidden(AppError):
    http_status = 403
    code = "FORBIDDEN"


class NotFound(AppError):
    http_status = 404
    code = "NOT_FOUND"


class Conflict(AppError):
    http_status = 409
    code = "CONFLICT"


class PreconditionFailed(AppError):
    http_status = 412
    code = "PRECONDITION_FAILED"


class ValidationFailed(AppError):
    http_status = 422
    code = "VALIDATION_FAILED"


def _payload(code: str, message: str, details: list[dict[str, Any]], request_id: str) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "details": details,
        }
    }


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or f"req_{uuid.uuid4().hex[:16]}"
    return JSONResponse(
        status_code=exc.http_status,
        content=_payload(exc.code, exc.message, exc.details, request_id),
    )


async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or f"req_{uuid.uuid4().hex[:16]}"
    # 生产环境不外泄堆栈，只记录工单号
    return JSONResponse(
        status_code=500,
        content=_payload("INTERNAL_ERROR", "服务暂时不可用", [], request_id),
    )
