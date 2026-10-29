# CulturalWalk API · 应用入口
"""只做三件事：注册中间件、注册路由、注册异常处理。业务逻辑一行都不许写在这里。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import (
    AppError,
    app_error_handler,
    request_validation_handler,
    unhandled_handler,
)

# 模块路由。骨架阶段全部为空 router（只有 tag 和 TODO 注释），
# 谁认领哪张卡，谁就往自己模块的 router.py 里填端点。
from app.modules.audit.router import router as audit_router
from app.modules.catalog.router import router as catalog_router
from app.modules.community.router import router as community_router
from app.modules.discovery.router import router as discovery_router
from app.modules.identity.router import router as identity_router
from app.modules.media.router import router as media_router
from app.modules.moderation.router import router as moderation_router
from app.modules.notifications.router import router as notifications_router
from app.modules.planner.router import router as planner_router
from app.modules.routes.router import router as routes_router

MODULE_ROUTERS = [
    identity_router,
    catalog_router,
    routes_router,
    discovery_router,
    moderation_router,
    community_router,
    planner_router,
    media_router,
    notifications_router,
    audit_router,
]


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):  # type: ignore[no-untyped-def]
        request.state.request_id = request.headers.get(
            "X-Request-Id", f"req_{uuid.uuid4().hex[:16]}"
        )
        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_id
        return response

    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    # 请求体/查询参数校验失败也走统一信封，契约要求所有非 2xx 都是 {"error": {...}}。
    app.add_exception_handler(RequestValidationError, request_validation_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_handler)

    api = APIRouter(prefix=settings.api_prefix)

    @api.get("/health", tags=["system"], summary="健康检查")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    for module_router in MODULE_ROUTERS:
        api.include_router(module_router)

    app.include_router(api)
    return app


app = create_app()
