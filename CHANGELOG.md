## 2026-10-30

- 工程：新增 `scripts/preflight.sh`（一条命令跑后端 lint/测试、前端 typecheck/单测/构建、契约自检）；必读1 §2 修正为**真实可复制**的命令（仓库根没有 package.json，原 `pnpm typecheck` 等命令不存在）；新增 `docs/问题与回滚台账.md`（问题记录 + 回滚三板斧 + 基线 tag）。
# 变更记录

按时间倒序。每次合并到 main 前在 PR 里追加一行。

| 日期 | 范围 | 变更 | 负责人 |
| --- | --- | --- | --- |
| 2026-10-30 | FE/QA | 前端单测进 CI（`pnpm -C apps/web test`）；补共享层/路由/审核状态/三个页面冒烟测试，共 22 文件 128 例；修复无 `localStorage` 环境 import 即崩、非 JSON 响应解析崩溃；必读1/CONTRIBUTING/00 同步测试底线 | P1 |
| 2026-10-30 | M0 | 仓库迁到组织 `sit-rhg`（显示名 CulturalWalk）；必读1/必读2/00/CONTRIBUTING 同步新地址、组员找仓库与旧克隆改远端说明 | P1 |
| 2026-10-27 | M0 | 任务卡改由看板生成（cards.json / cards.yml / 认领清单.md），人天配平 107.5 | P1 |
| 2026-10-27 | M0 | 新增 `discovery` 只读模块；角色分工三处文档对齐 | P1 |
| 2026-10-26 | M0 | 仓库骨架、契约、九个模块、CI | P1–P4 |
