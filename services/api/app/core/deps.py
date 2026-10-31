# CulturalWalk API · 认证与依赖
"""鉴权只在这里做。router 里只允许 `user = Depends(require_user)` 或
`Depends(require_role("admin", ...))` 这几种写法。"""

from __future__ import annotations

from collections.abc import Callable
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


_ROLE_LABELS = {"admin": "管理员", "editor": "编辑"}


def _forbidden_message(allowed: frozenset[str]) -> str:
    if not allowed:
        return "接口未配置可访问角色，已默认拒绝"
    labels = "、".join(_ROLE_LABELS.get(role, role) for role in sorted(allowed))
    return f"需要{labels}权限"


def require_role(*allowed_roles: str) -> Callable[..., CurrentUser]:
    """角色依赖工厂：`require_role("admin", "editor")` 生成一个能直接 Depends 的依赖。

    用法（角色判断只写在这里，router 里不许再写 if）::

        AdminDep = Annotated[CurrentUser, Depends(require_role("admin", "editor"))]

    不传角色按 fail-closed 处理：谁都进不去（403）。漏写一个角色参数应该是"门关死了"
    而不是"门全开了"，而且失败方向是看得见的 403，比 import 期抛异常更难被忽略。
    """
    allowed = frozenset(allowed_roles)

    def dependency(user: Annotated[CurrentUser, Depends(require_user)]) -> CurrentUser:
        if user.role not in allowed:
            raise Forbidden(_forbidden_message(allowed))
        return user

    return dependency


# 历史别名：admin 与 editor 都能进管理端（沿用 is_admin 的既有口径，行为不变）
require_admin = require_role("admin", "editor")


CurrentUserDep = Annotated[CurrentUser, Depends(require_user)]
OptionalUserDep = Annotated[CurrentUser | None, Depends(optional_user)]
AdminDep = Annotated[CurrentUser, Depends(require_admin)]
