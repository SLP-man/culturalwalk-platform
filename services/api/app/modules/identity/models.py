# 身份与会话 · ORM 模型
"""表结构以 docs/02-数据模型与状态机.md 为准。

迁移只由 P3 一人生成：alembic revision --autogenerate -m "<动词>_<对象>"
"""

from __future__ import annotations

# from app.core.db import Base
# from sqlalchemy.orm import Mapped, mapped_column
#
# class Identity(Base):
#     __tablename__ = "identitys"
#     ...
