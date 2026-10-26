# -*- coding: utf-8 -*-
"""生成 services/api/app/modules/<模块>/ 的骨架文件。

每个模块固定 6 个文件 + tests。内容刻意保持"能跑但没有业务"：
- router.py 里只有 TODO 注释写明本模块要实现的端点（与 openapi.yaml 对齐）
- service.py 里只有类型签名占位，实现留给认领的人
这样骨架可以 uvicorn 起来，/docs 里能看到 9 个 tag，但没人会误以为功能已完成。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "services" / "api" / "app" / "modules"

MODULES = {
    "identity": {
        "title": "身份与会话",
        "prefix": "/auth",
        "tags": ["auth", "users"],
        "endpoints": [
            ("POST", "/auth/register", "注册（公开）"),
            ("POST", "/auth/login", "登录（公开）"),
            ("POST", "/auth/refresh", "刷新令牌（公开）"),
            ("POST", "/auth/logout", "退出登录"),
            ("GET", "/users/me", "当前用户"),
            ("GET", "/users/{user_id}/profile", "用户公开主页（公开）"),
        ],
        "owns": "User, Session",
        "not": "路线内容、审核判断",
        "examples": [
            "def register(payload: RegisterIn, db: DbDep, idem: IdemDep) -> TokenPairOut: ...",
            "def login(payload: LoginIn, db: DbDep) -> TokenPairOut: ...",
        ],
    },
    "catalog": {
        "title": "地点与文化资料",
        "prefix": "/places",
        "tags": ["places"],
        "endpoints": [
            ("GET", "/places", "地点列表（公开，支持 q/district/tag）"),
            ("GET", "/places/{place_id}", "地点详情（含 facts 与 sources）"),
            ("POST", "/places", "新增地点（编辑）"),
            ("POST", "/places/{place_id}/facts", "新增事实与来源（编辑）"),
        ],
        "owns": "Place, PlaceFact, PlaceSource",
        "not": "路线编排、发布",
        "examples": [
            "def list_places(q: str | None, district: str | None, db: DbDep) -> Page[PlaceOut]: ...",
        ],
    },
    "routes": {
        "title": "路线与版本",
        "prefix": "/route-drafts",
        "tags": ["drafts"],
        "endpoints": [
            ("GET", "/route-drafts", "我的草稿列表"),
            ("POST", "/route-drafts", "新建草稿"),
            ("GET", "/route-drafts/{draft_id}", "草稿详情"),
            ("PATCH", "/route-drafts/{draft_id}", "更新草稿（If-Match）"),
            ("DELETE", "/route-drafts/{draft_id}", "删除草稿（仅 EDITING）"),
            ("PUT", "/route-drafts/{draft_id}/nodes", "整表替换节点顺序"),
            ("POST", "/route-drafts/{draft_id}/submit", "提交审核（冻结版本，单事务）"),
            ("POST", "/route-drafts/{draft_id}/withdraw", "撤回投稿"),
        ],
        "owns": "Route, RouteDraft, RouteNode, RouteVersion",
        "not": "审核、发布、AI 生成",
        "examples": [
            "def freeze_version(db: Session, draft: RouteDraft) -> RouteVersion: ...",
            "def submit_for_review(db: Session, draft_id: UUID, user: CurrentUser) -> Submission: ...",
        ],
    },
    "moderation": {
        "title": "审核与发布",
        "prefix": "/review",
        "tags": ["review"],
        "endpoints": [
            ("GET", "/review/tasks", "审核队列（管理员）"),
            ("POST", "/review/tasks/{task_id}/claim", "领取任务（租约）"),
            ("POST", "/review/tasks/{task_id}/release", "释放任务"),
            ("POST", "/review/tasks/{task_id}/decision", "审核决定 approve/request_changes/reject"),
            ("GET", "/submissions/{submission_id}", "投稿详情（含 diff 快照）"),
            ("POST", "/submissions/{submission_id}/publish", "发布（校验 version_id + hash）"),
            ("POST", "/publications/{publication_id}/unpublish", "下线（必须写原因）"),
        ],
        "owns": "Submission, ReviewTask, ReviewAction, Publication",
        "not": "编辑内容本身",
        "examples": [
            "def claim_task(db: Session, task_id: UUID, reviewer: CurrentUser) -> ReviewTask: ...",
            "def publish(db: Session, submission_id: UUID, version_id: UUID, content_hash: str) -> Publication: ...",
        ],
    },
    "community": {
        "title": "社区互动",
        "prefix": "/routes",
        "tags": ["community"],
        "endpoints": [
            ("GET", "/routes/{route_id}/comments", "评论列表（公开，置顶优先）"),
            ("POST", "/routes/{route_id}/comments", "发表评论"),
            ("POST", "/comments/{comment_id}/pin", "作者置顶一条"),
            ("POST", "/routes/{route_id}/favorite", "收藏"),
            ("DELETE", "/routes/{route_id}/favorite", "取消收藏"),
        ],
        "owns": "Comment, Favorite",
        "not": "路线内容修改、举报申诉（二期）",
        "examples": [
            "def create_comment(db: Session, route_id: UUID, body: str, user: CurrentUser) -> Comment: ...",
        ],
    },
    "planner": {
        "title": "行程规划（多 Agent）",
        "prefix": "/plans",
        "tags": ["plans"],
        "endpoints": [
            ("GET", "/plans", "我的行程列表"),
            ("POST", "/plans", "提交规划（异步 202）"),
            ("GET", "/plans/{plan_id}", "行程详情（含步骤进度）"),
            ("DELETE", "/plans/{plan_id}", "删除行程"),
            ("POST", "/plans/{plan_id}/to-draft", "行程转路线草稿"),
        ],
        "owns": "Itinerary, ItineraryDay, ItineraryItem, PlanRun, AgentStep",
        "not": "路线投稿、发布",
        "examples": [
            "def enqueue_plan(db: Session, payload: PlanInput, user: CurrentUser) -> PlanRun: ...",
            "def run_agents(run_id: UUID) -> None:  # researcher -> planner -> critic -> verifier",
        ],
        "extra": '''
# --- 多 Agent 编排契约（实现见 agents/） -------------------------------------
# 每个 Agent 只做一件事，输入输出都是 PlanContext，禁止互相 import 具体实现：
#
#   class Agent(Protocol):
#       name: Literal["researcher", "planner", "critic", "verifier"]
#       def run(self, ctx: PlanContext) -> PlanContext: ...
#
# researcher: 从 catalog 检索候选地点与事实（只读）
# planner   : 按时间/地理邻近/预算组排，产出日程骨架
# critic    : 检查超预算、赶路、闭馆、重复点位，回写 issues[]
# verifier  : 逐条核对来源，无来源的项标 confidence=unverified
#
# 失败策略：任一步抛异常 -> run.state=FAILED，已完成步骤与输出保留，不整体丢弃。
''',
    },
    "media": {
        "title": "媒体资源",
        "prefix": "/media",
        "tags": ["media"],
        "endpoints": [
            ("POST", "/media/intent", "申请上传（返回预签名，zone=quarantine）"),
            ("POST", "/media/{media_id}/complete", "通知上传完成（入队扫描）"),
            ("GET", "/media/{media_id}", "媒体状态（CLEAN 才有公开 URL）"),
        ],
        "owns": "MediaAsset",
        "not": "内容审核",
        "examples": [
            "def create_intent(db: Session, filename: str, mime: str, size: int, user: CurrentUser) -> MediaIntentOut: ...",
        ],
    },
    "notifications": {
        "title": "站内通知",
        "prefix": "/notifications",
        "tags": ["notifications"],
        "endpoints": [
            ("GET", "/notifications", "我的通知"),
            ("POST", "/notifications/{notification_id}/read", "标记已读"),
        ],
        "owns": "Notification",
        "not": "短信、邮件、推送",
        "examples": [
            "def notify(db: Session, user_id: UUID, type: str, payload: dict) -> Notification: ...",
        ],
    },
    "audit": {
        "title": "审计",
        "prefix": "/audit-logs",
        "tags": ["audit"],
        "endpoints": [
            ("GET", "/audit-logs", "审计查询（管理员）"),
        ],
        "owns": "AuditLog",
        "not": "业务状态变更",
        "examples": [
            "def write(db: Session, *, actor_id, action, object_type, object_id, before_hash, after_hash, reason) -> AuditLog: ...",
        ],
        "extra": '''
# 调用方约定：审计由业务模块在同一个事务里显式调用 audit.service.write()，
# 不做隐式事件钩子——出了问题必须能在代码里一眼看到"谁记了这条审计"。
''',
    },
}

ROUTER = '''# {title} · HTTP 入口
"""只做编解码与依赖注入。业务规则一律写进 service.py。

契约以 docs/api/openapi.yaml 为准，本文件只负责把端点挂上去。
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="{prefix}", tags={tags})


# ===== 待实现端点（认领任务卡后逐条填） =====
{endpoint_lines}
{extra}'''

SERVICE = '''# {title} · 业务规则
"""本模块唯一允许写业务判断的地方。router 不许写 if/else 业务逻辑。

拥有数据：{owns}
明确不做：{excluded}
"""
from __future__ import annotations

from sqlalchemy.orm import Session

# ===== 待实现：下面是签名示意（已注释，抄下来改成真实现） =====
{examples}


class {cls}Service:
    """依赖注入的官方入口；外部模块只能通过它访问本模块能力。"""

    def __init__(self, db: Session) -> None:
        self.db = db
'''

REPO = '''# {title} · 数据访问
"""只写查询和落库，不写权限判断、不写业务流程。"""
from __future__ import annotations

from sqlalchemy.orm import Session


class {cls}Repository:
    def __init__(self, db: Session) -> None:
        self.db = db
'''

MODELS = '''# {title} · ORM 模型
"""表结构以 docs/02-数据模型与状态机.md 为准。

迁移只由 P3 一人生成：alembic revision --autogenerate -m "<动词>_<对象>"
"""
from __future__ import annotations

# from app.core.db import Base
# from sqlalchemy.orm import Mapped, mapped_column
#
# class {cls}(Base):
#     __tablename__ = "{table}"
#     ...
'''

SCHEMAS = '''# {title} · DTO
"""请求/响应模型。字段与 docs/api/openapi.yaml 保持一致，改 yaml 再改这里。"""
from __future__ import annotations

from pydantic import BaseModel


class {cls}Out(BaseModel):
    """TODO: 按 openapi.yaml 的 schema 补齐字段。"""
'''

INIT = '''"""本模块的公开出口。外部模块只能 import 这里的 service，不要 import models。"""
'''

SMOKE = '''"""骨架自检：模块可导入、router 已挂载。真正业务测试写在本文件下方。"""
from __future__ import annotations

from app.modules.{module}.router import router


def test_router_importable() -> None:
    assert router is not None


def test_prefix_configured() -> None:
    assert router.prefix.startswith("/"), "router 必须带前缀，否则端点会跑到根路径"


# TODO: 认领任务卡后在此补 2xx / 4xx / 权限负例
'''

MODULES_INIT = '''"""业务模块集合。

依赖方向（禁止反向）：
    routes -> catalog
    planner -> catalog, routes(只读)
    moderation -> routes, audit
    community -> routes(只读), identity
    discovery -> routes, catalog, community(只读)
    media -> identity
    notifications -> identity
    audit <- 所有模块（只写）

出现循环依赖先写 docs/adr 的 ADR，不许"先 import 了再说"。
"""
'''

TESTS_INIT = ''


def wrap_example(text: str, width: int = 92) -> str:
    """把签名示意折成多行注释，避免 E501（生成物必须一次通过 ruff）。"""
    prefix = "#   "
    if len(prefix + text) <= width:
        return prefix + text
    head, sep, tail = text.partition(" -> ")
    if sep and len(prefix + head + sep) <= width:
        return f"{prefix}{head}{sep}\n{prefix}    {tail}"
    words = text.split(" ")
    lines: list[str] = []
    current = prefix
    for word in words:
        if len(current) + len(word) + 1 > width and current != prefix:
            lines.append(current.rstrip())
            current = prefix + "    "
        current += word + " "
    lines.append(current.rstrip())
    return "\n".join(lines)


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "__init__.py").write_text(MODULES_INIT, encoding="utf-8")

    for module, spec in MODULES.items():
        base = ROOT / module
        (base / "tests").mkdir(parents=True, exist_ok=True)
        cls = "".join(part.capitalize() for part in module.split("_"))

        endpoint_lines = "\n".join(
            f'#   {m:6s} {p:48s} {desc}' for m, p, desc in spec["endpoints"]
        )
        files = {
            "__init__.py": INIT,
            "router.py": ROUTER.format(
                title=spec["title"],
                prefix=spec["prefix"],
                tags=spec["tags"],
                endpoint_lines=endpoint_lines,
                extra=spec.get("extra", ""),
            ),
            "service.py": SERVICE.format(
                title=spec["title"],
                owns=spec["owns"],
                excluded=spec["not"],
                examples="\n".join(wrap_example(ex) for ex in spec["examples"]),
                cls=cls,
            ),
            "repository.py": REPO.format(title=spec["title"], cls=cls),
            "models.py": MODELS.format(title=spec["title"], cls=cls, table=module + "s"),
            "schemas.py": SCHEMAS.format(title=spec["title"], cls=cls),
            "tests/__init__.py": TESTS_INIT,
            "tests/test_smoke.py": SMOKE.format(module=module),
        }
        for name, content in files.items():
            path = base / name
            path.write_text(content, encoding="utf-8")
        print(f"  {module:<14} {len(spec['endpoints'])} 个待实现端点")

    print("完成")


if __name__ == "__main__":
    main()
