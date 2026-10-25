# CulturalWalk · 文创路线平台

移动 Web/H5 优先的城市文化路线共创平台：浏览文化节点与路线、查看地图定位、投稿路线，由管理员审核、退回、发布与下线。

> **当前阶段：结构草稿期（v0.1）**
> 本仓库先落地「设计文档 + 协作规范」，代码目录只是占位。**顶层目录随时可以改**，见下方「目录可改」。
> 设计文档入口：[docs/](./docs/README.md)。

## 技术栈（方向已定，细节待 ADR 冻结）

| 层 | 选型 |
|---|---|
| 前端 | Vue 3 + TypeScript + Vite（移动 H5 + 管理端路由） |
| 后端 | FastAPI + Pydantic + SQLAlchemy/Alembic，模块化单体 |
| 数据 | PostgreSQL 为事实源；图片/附件走对象存储 |
| 部署 | 单机 Docker Compose + Nginx/Caddy，单地域、单实例起步 |

> 后端框架仍以 ADR-0012 的结论为准；ADR 未冻结前只做框架中立的纵向切片。

## 仓库结构（初稿）

```text
.
├── apps/
│   └── web-h5/          # 用户 H5 + 管理端页面（占位，代码未生成）
├── services/
│   └── api/             # 模块化单体 API（占位，代码未生成）
├── infra/               # docker / proxy / deploy（占位）
├── docs/                # 设计文档、ADR
└── .github/             # CI、PR / Issue 模版
```

业务模块（identity、nodes、routes、submissions、navigation、ai_drafting、media、audit）和 `packages/` **暂不创建**，等结构定稿后再生成，避免反复改目录。

## 目录可改

这套结构是起点，不是承诺：

- 改名 / 移动：`git mv 旧路径 新路径`，Git 历史保留
- 删除：`git rm -r 路径`
- 结构调整：开一个 PR 说明原因，团队 review 后合并
- 已推送的历史不会因为目录调整而丢失

## 协作方式

1. `main` 受保护：只能通过 PR 合并，至少 1 人 approve + CI 通过
2. 分支：`feat/<模块>-<简述>`、`fix/<简述>`、`docs/<简述>`
3. 提交信息：`feat: ...` / `fix: ...` / `docs: ...`
4. 详细规范见 [CONTRIBUTING.md](./CONTRIBUTING.md)

## 里程碑

- [ ] 结构定稿 → 生成前后端最小可运行骨架
- [ ] S1 纵向切片：匿名浏览 → 登录 → 创建草稿 → 提交 → 审核 → 发布 → 下线
- [ ] 公网试点：备份、监控、回滚 runbook 演练

## 文档

- [VibeCoding 底层架构与开发范式](./docs/CulturalWalk_VibeCoding底层架构与开发范式.md)：架构基线 v0.1（2026-10-14）
- [新手开发手册](./docs/CulturalWalk_新手开发手册.md)：零基础入门与第一个纵向切片

> 另有两份材料（《技术栈与开发方式方案》《对话导出_可恢复记录》）尚未入库：源文件在微信缓存目录，受 macOS 权限保护当前读取不到。需要时把文件放进 `docs/` 再提交即可。
