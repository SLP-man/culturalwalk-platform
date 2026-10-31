"""骨架自检：模块可导入、router 已挂载。真正业务测试写在 test_auth_api.py。"""

from __future__ import annotations

from app.modules.identity.router import auth_router, router, users_router


def test_router_importable() -> None:
    assert router is not None


def test_prefix_configured() -> None:
    # 顶层 router 是空前缀的挂载点，端点必须分别落在 /auth 与 /users 下，
    # 否则模块路由会跑到 api 根路径上。
    assert {auth_router.prefix, users_router.prefix} == {"/auth", "/users"}
