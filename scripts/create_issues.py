#!/usr/bin/env python3
"""把 `tasks/cards.yml` 里的任务卡批量建成 GitHub Issues（幂等，可反复执行）。

用法：
    export GITHUB_TOKEN=<有 repo 权限的 token>     # Windows: $env:GITHUB_TOKEN="..."
    python scripts/create_issues.py                 # 默认读 origin 的仓库
    python scripts/create_issues.py --repo owner/name --dry-run

行为：
1. 先补齐标签（模块名 / 里程碑 M0–M5 / 角色 P1–P4 / `任务卡`）；
2. 每条卡建一个 issue，标题 `[M0-01] 仓库骨架与目录`；**已存在同标题的 open/closed issue 就跳过**
   （所以重复执行不会产生重复 issue，只会在卡片内容变化时打印提示）；
3. 把结果写回 `tasks/issues.csv` 和 `tasks/issue-map.json`（id → issue 号 / 链接），供文档引用。

只依赖标准库，不需要 requests。
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.github.com"

LABEL_COLORS = {
    "任务卡": "5319e7",
    "M0": "bfd4f2", "M1": "bfd4f2", "M2": "c5def5", "M3": "d4c5f9",
    "M4": "e4d5f9", "M5": "f4d5f9",
    "P1": "f9d0c4", "P2": "fef2c0", "P3": "d3f9d8", "P4": "d0ebff",
}


def module_color(module: str) -> str:
    """给模块标签一个稳定的颜色（同一模块永远同色）。"""
    palette = ["1d76db", "0e8a16", "b60205", "e99695", "c2e0c6", "f9d0c4", "5319e7", "006b75", "d93f0b", "0052cc"]
    return palette[sum(map(ord, module)) % len(palette)]


class GitHub:
    def __init__(self, token: str, repo: str) -> None:
        self.token = token
        self.repo = repo

    def request(self, method: str, path: str, payload: dict | None = None, *, retries: int = 4):
        url = path if path.startswith("http") else API + path
        data = json.dumps(payload).encode() if payload is not None else None
        last: Exception | None = None
        for attempt in range(1, retries + 1):
            req = urllib.request.Request(url, data=data, method=method)
            req.add_header("Authorization", f"Bearer {self.token}")
            req.add_header("Accept", "application/vnd.github+json")
            req.add_header("X-GitHub-Api-Version", "2022-11-28")
            req.add_header("User-Agent", "culturalwalk-create-issues")
            if data:
                req.add_header("Content-Type", "application/json")
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    body = resp.read().decode()
                    return json.loads(body) if body.strip() else {}
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode(errors="replace")[:300]
                if exc.code in (401, 403) or exc.code == 404:
                    raise SystemExit(f"{method} {path} → {exc.code}：{detail}") from exc
                last = RuntimeError(f"{exc.code} {detail}")
            except Exception as exc:  # noqa: BLE001 - 网络抖动统一重试
                last = exc
            time.sleep(1.5 * attempt)
        raise SystemExit(f"{method} {path} 连续失败：{last}")

    def paged(self, path: str) -> list[dict]:
        items: list[dict] = []
        page = 1
        while True:
            sep = "&" if "?" in path else "?"
            chunk = self.request("GET", f"{path}{sep}per_page=100&page={page}")
            if not isinstance(chunk, list) or not chunk:
                return items
            items.extend(chunk)
            if len(chunk) < 100:
                return items
            page += 1


def detect_repo() -> str:
    try:
        url = subprocess.run(
            ["git", "remote", "get-url", "origin"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise SystemExit("拿不到 origin，请用 --repo owner/name 指定仓库") from exc
    match = re.search(r"github\.com[:/]+([^/]+)/(.+?)(?:\.git)?$", url)
    if not match:
        raise SystemExit(f"无法从 origin 解析 owner/repo：{url}")
    return f"{match.group(1)}/{match.group(2)}"


def ensure_labels(gh: GitHub, modules: list[str], milestones: list[str], roles: list[str]) -> None:
    existing = {label["name"] for label in gh.paged(f"/repos/{gh.repo}/labels")}
    wanted: list[tuple[str, str, str]] = [("任务卡", LABEL_COLORS["任务卡"], "任务看板卡片")]
    wanted += [(m, module_color(m), f"{m} 模块") for m in modules]
    wanted += [(m, LABEL_COLORS.get(m, "ededed"), f"里程碑 {m}") for m in milestones]
    wanted += [(r, LABEL_COLORS.get(r, "ededed"), f"负责角色 {r}") for r in roles]
    for name, color, desc in wanted:
        if name in existing:
            continue
        gh.request("POST", f"/repos/{gh.repo}/labels", {"name": name, "color": color, "description": desc})
        print(f"  + 标签 {name}")


def card_paths(card: dict) -> str:
    module = card["module"]
    if module == "apps/web":
        return "`apps/web/src/**`（页面、组件、api client）"
    if module == "qa":
        return "`tests/`、`scripts/`、`.github/workflows/`（测试与流水线）"
    if module == "infra":
        return "`infra/`、`services/api/app/infra/`、`.devcontainer/`"
    return f"`services/api/app/modules/{module}/**`"


def card_body(card: dict) -> str:
    depends = card.get("depends_on") or "无"
    return f"""## 这张卡要交付什么

| 项 | 内容 |
| --- | --- |
| 输出 | {card.get('deliverable', '—')} |
| 验收 | {card.get('accept', '—')} |
| 依赖 | {depends} |
| 估计 | {card.get('estimate_days', '?')} 人天 |
| 负责角色 | {card.get('owner', '—')} |

## 只看自己这摊代码

改动范围：{card_paths(card)}

不要动别人的模块、不要手改生成文件（`packages/contracts/src/types.ts`、`tasks/*`、`docs/01-*`）。

## 怎么算完成

- [ ] 代码通过 PR 合进 `main`（不要直推）
- [ ] CI 四项检查全绿：`backend` / `frontend` / `contract` / `compose`
- [ ] 验收条件自己跑过一遍，并把结果贴在本 issue 的评论里

## 遇到卡壳

先看 [`docs/04-新手入门指南.md`](../blob/main/docs/04-新手入门指南.md) 的「常见报错」一节；还不行就在本 issue 下写清楚「我做了什么 / 期望什么 / 实际什么」。

<sub>由 `tasks/cards.yml` 自动生成——改任务请改 `docs/01-模块与任务看板.md` 后重跑 `python scripts/gen_cards.py`。</sub>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="把任务卡建成 GitHub Issues")
    parser.add_argument("--repo", default=None, help="owner/name，默认取 origin")
    parser.add_argument("--dry-run", action="store_true", help="只打印，不真的建")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token and not args.dry_run:
        raise SystemExit("缺少 GITHUB_TOKEN 环境变量（需要 repo 权限）")

    data = yaml.safe_load((ROOT / "tasks" / "cards.yml").read_text(encoding="utf-8"))
    cards: list[dict] = data["cards"]
    repo = args.repo or detect_repo()
    print(f"仓库 {repo}，共 {len(cards)} 张卡{'（dry-run）' if args.dry_run else ''}")

    if args.dry_run:
        for card in cards:
            print(f"  [{card['id']}] {card['title']}  ← {card['module']} / {card['milestone']} / {card['owner']}")
        return

    gh = GitHub(token, repo)
    ensure_labels(
        gh,
        sorted({c["module"] for c in cards}),
        sorted({c["milestone"] for c in cards}),
        sorted({c["owner"] for c in cards}),
    )

    existing: dict[str, dict] = {}
    for issue in gh.paged(f"/repos/{repo}/issues?state=all"):
        if "pull_request" not in issue:
            existing.setdefault(issue["title"], issue)

    mapping: dict[str, dict] = {}
    created = skipped = 0
    for card in cards:
        title = f"[{card['id']}] {card['title']}"
        if title in existing:
            issue = existing[title]
            skipped += 1
            mapping[card["id"]] = {"number": issue["number"], "url": issue["html_url"], "title": title}
            continue
        issue = gh.request(
            "POST",
            f"/repos/{repo}/issues",
            {
                "title": title,
                "body": card_body(card),
                "labels": ["任务卡", card["module"], card["milestone"], card["owner"]],
            },
        )
        created += 1
        mapping[card["id"]] = {"number": issue["number"], "url": issue["html_url"], "title": title}
        print(f"  #{issue['number']:>3} {title}")
        time.sleep(0.4)

    (ROOT / "tasks" / "issue-map.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    with (ROOT / "tasks" / "issues.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["id", "module", "milestone", "owner", "title", "estimate_days", "issue", "url"])
        for card in cards:
            entry = mapping[card["id"]]
            writer.writerow(
                [card["id"], card["module"], card["milestone"], card["owner"], card["title"],
                 card.get("estimate_days", ""), entry["number"], entry["url"]]
            )
    print(f"完成：新建 {created} 条，已存在跳过 {skipped} 条；映射写入 tasks/issue-map.json 与 tasks/issues.csv")


if __name__ == "__main__":
    sys.exit(main())
