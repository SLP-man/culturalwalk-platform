"""骨架自检：模块可导入、router 已挂载。真正业务测试写在本文件下方。"""

from __future__ import annotations

from app.modules.routes.router import router


def test_router_importable() -> None:
    assert router is not None


def test_prefix_configured() -> None:
    assert router.prefix.startswith("/"), "router 必须带前缀，否则端点会跑到根路径"


# TODO: 认领任务卡后在此补 2xx / 4xx / 权限负例
