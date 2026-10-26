# AGENTS.md

给在这个仓库里写代码的 AI 助手（Claude Code / Codex / Cursor / Copilot 等）看的约定。
人也要遵守，只是人可以讲道理，模型最好别自由发挥。

## 先读什么

按顺序读，别跳：

1. `docs/00-总体开发文档.md` —— 产品边界、模块职责、里程碑
2. `docs/02-数据模型与状态机.md` —— 表和状态，改数据前必读
3. `docs/03-接口契约规范.md` —— 命名、错误码、分页、幂等
4. `docs/api/openapi.yaml` —— 契约本身
5. 当前任务卡（`tasks/cards.json` 或对应 issue）；任务卡由 `python scripts/gen_cards.py` 从看板生成，**不要手改** `tasks/` 下的产物

## 硬性规则

- **不许自己发明端点**。要加接口，先改 `docs/api/openapi.yaml`，再跑 `python scripts/check_contract.py`。
- **不许手写 DTO 类型**。前端类型来自 `pnpm gen`（`packages/contracts/src/types.ts`）。
- **不许跨模块 import `models`**。只能 import 其他模块的 `service`，见 `app/modules/__init__.py` 里的依赖方向。
- **不许在 `router.py` 写业务逻辑**。router 只做参数解码、调 service、返回响应。
- **不许改 `migrations/env.py` 和已有 migration**（除非你就是 P3 且任务卡写了）。
- **不许 `git commit --no-verify`**，不许关掉 CI 检查来"先合进去"。
- **不许把密钥写进代码**。本地用 `infra/.env`，CI 用 secrets。
- **不许为了通过测试改断言**。测试挂了先看是实现错还是断言错，说不清就别改。

## 写代码时的偏好

- Python：类型标注 + `from __future__ import annotations`；SQL 用 SQLAlchemy 2.0 写法；错误抛 `AppError` 子类而不是 `HTTPException`（统一信封）。
- 前端：`<script setup lang="ts">`；状态尽量留在页面，别提前上 Pinia；请求一律走 `@/shared/api`。
- 注释写"为什么"，不写"是什么"。`# 这里加 1` 这种删掉。
- 新增依赖前先问：标准库/现有依赖能不能做？不能就在 PR 描述里写一句理由。

## 提交前自查

```bash
cd services/api && ruff check . && ruff format --check . && pytest -q
cd apps/web && pnpm typecheck && pnpm build
python scripts/check_contract.py
```

四条全绿再开 PR。CI 会跑同样的东西。

## 遇到不确定的需求

不要猜。在 issue 里 @ 提需求的人，或者写进 PR 描述里的「待确认」小节。
猜错的代价是别人基于你的错误假设继续开发，比停下来问一句贵得多。
