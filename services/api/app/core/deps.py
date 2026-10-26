# CulturalWalk API · 认证与依赖
"""鉴权只在这里做。router 里只允许 `user = Depends(require_user)` 这一种写法。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header
from jose import JWTError, jwt

from app.core.config import settings
from app.core.errors import Forbidden, Unauthorized


@dataclass(frozen=True)
class CurrentUser:
    id: str
    username: str
    role: str  # user | editor | admin

    def is_admin(self) -> bool:
        return self.role in {"admin", "editor"}


def create_access_token(*, user_id: str, username: str, role: str) -> str:
    import time

    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": int(time.time()) + settings.access_token_ttl_seconds,
        "typ": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
    except JWTError as exc:  # 过期、签名错、格式错统一 401
        raise Unauthorized("登录已失效，请重新登录") from exc


def _user_from_auth_header(authorization: str | None) -> CurrentUser | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise Unauthorized("认证头格式错误")
    payload = decode_token(token)
    if payload.get("typ") != "access":
        raise Unauthorized("令牌类型错误")
    return CurrentUser(id=payload["sub"], username=payload["username"], role=payload["role"])


def optional_user(
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser | None:
    """公开接口用它：有 token 就带上用户（用于 is_favorited 之类）。"""
    return _user_from_auth_header(authorization)


def require_user(
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    user = _user_from_auth_header(authorization)
    if user is None:
        raise Unauthorized("请先登录")
    return user


def require_admin(
    user: Annotated[CurrentUser, Depends(require_user)],
) -> CurrentUser:
    if not user.is_admin():
        raise Forbidden("需要管理员权限")
    return user


CurrentUserDep = Annotated[CurrentUser, Depends(require_user)]
OptionalUserDep = Annotated[CurrentUser | None, Depends(optional_user)]
AdminDep = Annotated[CurrentUser, Depends(require_admin)]
