# 身份与会话 · HTTP 入口
"""只做编解码与依赖注入。业务规则一律写进 service.py。

契约以 docs/api/openapi.yaml 为准，本文件只负责把端点挂上去。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Response, status

from app.core.db import DbDep
from app.core.deps import CurrentUser, CurrentUserDep
from app.core.errors import Unauthorized
from app.modules.identity.schemas import (
    LoginIn,
    LogoutIn,
    RefreshIn,
    RegisterIn,
    TokenPairOut,
    UserOut,
    UserProfileOut,
)
from app.modules.identity.service import IdentityService, IssuedTokens

# /auth 与 /users 两个前缀的端点都属于本模块；main.py 每个模块只 include 一个 router，
# 所以下面再把它们合成一个根 router 挂出去。
auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])

router = APIRouter()
router.include_router(auth_router)
router.include_router(users_router)


def _tokens_out(issued: IssuedTokens) -> TokenPairOut:
    return TokenPairOut(
        access_token=issued.access_token,
        refresh_token=issued.refresh_token,
        expires_in=issued.expires_in,
        user=UserOut.model_validate(issued.user),
    )


def _user_id_of(user: CurrentUser) -> uuid.UUID:
    try:
        return uuid.UUID(user.id)
    except ValueError as exc:  # token 里的 sub 不是 UUID，等同登录失效
        raise Unauthorized("登录已失效，请重新登录") from exc


@auth_router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=TokenPairOut,
    summary="注册",
)
def register(payload: RegisterIn, db: DbDep) -> TokenPairOut:
    issued = IdentityService(db).register(
        username=payload.username, password=payload.password, email=payload.email
    )
    return _tokens_out(issued)


@auth_router.post("/login", response_model=TokenPairOut, summary="登录")
def login(payload: LoginIn, db: DbDep) -> TokenPairOut:
    return _tokens_out(
        IdentityService(db).login(username=payload.username, password=payload.password)
    )


@auth_router.post("/refresh", response_model=TokenPairOut, summary="刷新令牌")
def refresh(payload: RefreshIn, db: DbDep) -> TokenPairOut:
    return _tokens_out(IdentityService(db).refresh(payload.refresh_token))


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="退出登录")
def logout(user: CurrentUserDep, db: DbDep, payload: LogoutIn | None = None) -> Response:
    IdentityService(db).logout(
        user_id=_user_id_of(user),
        refresh_token=payload.refresh_token if payload else None,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@users_router.get("/me", response_model=UserOut, summary="当前用户")
def me(user: CurrentUserDep, db: DbDep) -> UserOut:
    # 库里没有这行、或账号已停用，都抛 Unauthorized：令牌有效不代表这个身份还在。
    return UserOut.model_validate(IdentityService(db).require_active_user(_user_id_of(user)))


@users_router.get(
    "/{user_id}/profile",
    response_model=UserProfileOut,
    # 契约里这些可选字段都不是 nullable：拿不到值就整个不出现，别回 null
    response_model_exclude_none=True,
    summary="用户公开主页",
)
def profile(user_id: uuid.UUID, db: DbDep) -> UserProfileOut:
    # 契约写的是 security: []，所以这里一个令牌依赖都不挂：匿名也要能看。
    return IdentityService(db).public_profile(user_id)
