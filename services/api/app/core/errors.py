# CulturalWalk API · 统一错误
"""错误包格式唯一定义处：{"error": {code, message, request_id, details[]}}。

约定见 docs/03-接口契约规范.md §1.4。前端按 code 分支，不按 message 文案。
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
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


# ===== 参数校验失败 =====
# FastAPI 默认返回 {"detail": [{loc: ["body","days"], msg: "Field required"}]}，
# 既不符合契约的统一信封（docs/03 §1.4），也没法让前端"按字段名提示"——
# 缺哪个字段藏在 loc 数组里，还得自己拼。这里翻成 details: [{field, reason}]。
#
# pydantic 的错误类型是稳定标识（missing / int_parsing / enum ...），
# 按 type 翻译而不是按 msg 文案，pydantic 改一下措辞也不会把提示改乱。
_PARAM_REASONS: dict[str, str] = {
    "missing": "缺少必填字段",
    "extra_forbidden": "不支持这个字段",
    "int_parsing": "需要一个整数",
    "int_type": "需要一个整数",
    "float_parsing": "需要一个数字",
    "float_type": "需要一个数字",
    "bool_parsing": "需要 true 或 false",
    "bool_type": "需要 true 或 false",
    "string_type": "需要一个字符串",
    "string_too_short": "内容太短",
    "string_too_long": "内容太长",
    "too_short": "数量少于下限",
    "too_long": "数量超过上限",
    "greater_than": "数值太小",
    "greater_than_equal": "数值太小",
    "less_than": "数值太大",
    "less_than_equal": "数值太大",
    "enum": "不在允许的取值范围内",
    "literal_error": "不在允许的取值范围内",
    "json_invalid": "请求体不是合法的 JSON",
    "model_type": "请求体应该是一个对象",
    "value_error": "取值不合法",
}

# loc 的第一段是错误发生的"来源"，不是字段名，拼进 field 会让前端对不上表单。
_LOCATION_PREFIXES = frozenset({"body", "query", "path", "header", "cookie"})


def _expected_values(raw: Any) -> list[str] | None:
    """把 pydantic 给的"允许值"整理成字符串列表。

    pydantic v2 的 ctx["expected"] 有时是列表，枚举这里却是一句给人看的话
    （"'walk', 'metro', 'bus', 'taxi' or 'bike'"）。前端想要的是能直接
    填进下拉框的数组，所以在服务端拆一次，别让前端去正则抠文案。
    """
    if isinstance(raw, (list, tuple, set)):
        return [str(item) for item in raw] or None
    if not isinstance(raw, str):
        return None
    parts = [part.strip().strip("'\"") for part in raw.replace(" or ", ", ").split(",")]
    values = [part for part in parts if part and "'" not in part]
    return values or None


def _validation_detail(error: dict[str, Any]) -> dict[str, Any]:
    loc = [str(part) for part in error.get("loc", ())]
    if loc and loc[0] in _LOCATION_PREFIXES:
        loc = loc[1:]
    error_type = str(error.get("type", ""))
    detail: dict[str, Any] = {
        "field": ".".join(loc) or None,
        "reason": _PARAM_REASONS.get(error_type, "取值不合法"),
    }
    # 枚举/字面量错误把允许值带回去，前端不用再翻文档猜能填什么。
    expected = _expected_values((error.get("ctx") or {}).get("expected"))
    if expected:
        detail["expected"] = expected
    return detail


async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or f"req_{uuid.uuid4().hex[:16]}"
    details = [_validation_detail(error) for error in exc.errors()]
    missing = [item["field"] for item in details if item["reason"] == "缺少必填字段"]
    if len(details) == 1:
        message = f"参数校验未通过：{details[0]['field']}（{details[0]['reason']}）"
    elif missing:
        message = "参数校验未通过，缺少必填字段：" + "、".join(str(name) for name in missing)
    else:
        message = "参数校验未通过"
    return JSONResponse(
        status_code=ValidationFailed.http_status,
        content=_payload(ValidationFailed.code, message, details, request_id),
    )
