#!/usr/bin/env python3
"""从 docs/01-模块与任务看板.md 生成任务卡清单。

产物三个，都别手改：
- tasks/cards.json  —— 机读版，给 scripts/create_issues.sh 用
- tasks/cards.yml   —— 人读版，review 时看 diff 方便
- tasks/认领清单.md —— 没装 gh/python 的组员照这个认领任务、建目录

看板是唯一真源：改任务只改 Markdown 表格，然后
    python scripts/gen_cards.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KANBAN = ROOT / "docs" / "01-模块与任务看板.md"
OUT_YML = ROOT / "tasks" / "cards.yml"
OUT_JSON = ROOT / "tasks" / "cards.json"
OUT_MD = ROOT / "tasks" / "认领清单.md"

# 章节标题前缀 → (模块目录名, 负责人, 里程碑)
SECTIONS = {
    "M0": ("infra", "P1", "M0"),
    "identity": ("identity", "P2", "M1"),
    "catalog": ("catalog", "P3", "M1"),
    "routes": ("routes", "P3", "M1"),
    "moderation": ("moderation", "P1", "M2"),
    "discovery": ("discovery", "P4", "M2"),
    "community": ("community", "P3", "M3"),
    "planner": ("planner", "P4", "M2"),
    "media": ("media", "P3", "M4"),
    "notifications": ("notifications", "P2", "M3"),
    "前端": ("apps/web", "P2", "M4"),
    "测试与材料": ("qa", "P1", "M5"),
}

ROW = re.compile(r"^\|\s*([A-Z][A-Z0-9]{0,3}-[A-Z]{0,3}\d{2})(\s*\|.*)$")
HEADING = re.compile(r"^### (.+)$")


def section_key(heading: str) -> str | None:
    for key in SECTIONS:
        if heading.startswith(key):
            return key
    return None


def split_cells(row: str) -> list[str]:
    """按 | 切分表格行，但忽略反引号内的 |（接口路径里常见）。"""
    cells: list[str] = []
    buf: list[str] = []
    in_code = False
    for ch in row.strip().strip("|"):
        if ch == "`":
            in_code = not in_code
            buf.append(ch)
        elif ch == "|" and not in_code:
            cells.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    cells.append("".join(buf))
    return [c.strip() for c in cells]


def clean(cell: str) -> str:
    return cell.replace("|", "/").replace("`", "").strip()


def parse() -> list[dict[str, str]]:
    heading = ""
    cards: list[dict[str, str]] = []
    seen: set[str] = set()
    for line in KANBAN.read_text(encoding="utf-8").splitlines():
        m = HEADING.match(line)
        if m:
            heading = m.group(1).strip()
            continue
        m = ROW.match(line.strip())
        key = section_key(heading) if heading else None
        if not m or not key:
            continue
        card_id = m.group(1)
        cells = [clean(c) for c in split_cells(m.group(2))]
        if len(cells) < 5:
            continue
        if card_id in seen:
            raise SystemExit(f"重复的任务 ID：{card_id}")
        seen.add(card_id)
        module, owner, milestone = SECTIONS[key]
        cards.append(
            {
                "id": card_id,
                "module": module,
                "owner": owner,
                "milestone": milestone,
                "title": cells[0],
                "deliverable": cells[1],
                "accept": cells[2],
                "depends_on": cells[3],
                "estimate_days": cells[4].replace("✅", "").strip(),
            }
        )
    return cards


def write_yml(cards: list[dict[str, str]]) -> None:
    lines = [
        "# 由 scripts/gen_cards.py 从 docs/01-模块与任务看板.md 生成，请勿手改。",
        f"# 共 {len(cards)} 张卡。改任务请改看板后重新生成。",
        "cards:",
    ]
    for c in cards:
        lines += [
            f'  - id: "{c["id"]}"',
            f'    module: "{c["module"]}"',
            f'    owner: "{c["owner"]}"',
            f'    milestone: "{c["milestone"]}"',
            f"    title: {q(c['title'])}",
            f"    deliverable: {q(c['deliverable'])}",
            f"    accept: {q(c['accept'])}",
            f"    depends_on: {q(c['depends_on'])}",
            f"    estimate_days: {c['estimate_days']}",
        ]
    OUT_YML.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(cards: list[dict[str, str]]) -> None:
    payload = [dict(c) for c in cards]
    for c in payload:
        c["estimate_days"] = float(c["estimate_days"])
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_md(cards: list[dict[str, str]]) -> None:
    total = sum(float(c["estimate_days"]) for c in cards)
    lines = [
        "# 任务卡认领清单",
        "",
        "> 由 `scripts/gen_cards.py` 生成，请勿手改；改任务请改 `docs/01-模块与任务看板.md`。",
        f"> 共 {len(cards)} 张卡，合计 {total:g} 人天。",
        "",
        "认领方式：找到自己模块的卡，在 GitHub issue 下回「我来」，然后把「输出」里列的文件建出来。",
        "",
    ]
    current = None
    for c in cards:
        if c["module"] != current:
            current = c["module"]
            lines += ["", f"## {current}（{c['owner']}）", ""]
        lines += [
            f"### {c['id']} {c['title']}",
            "",
            f"- 负责人：{c['owner']}　里程碑：{c['milestone']}　估时：{c['estimate_days']} 人天",
            f"- 依赖：{c['depends_on']}",
            f"- 输出：{c['deliverable']}",
            f"- 验收：{c['accept']}",
            "",
        ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def q(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main() -> int:
    cards = parse()
    if not cards:
        raise SystemExit("没有从看板解析到任务卡")
    write_yml(cards)
    write_json(cards)
    write_md(cards)

    total = sum(float(c["estimate_days"]) for c in cards)
    by_owner: dict[str, float] = {}
    for c in cards:
        by_owner[c["owner"]] = by_owner.get(c["owner"], 0) + float(c["estimate_days"])
    print(f"已生成 {len(cards)} 张卡，合计 {total:g} 人天")
    for owner, days in sorted(by_owner.items()):
        print(f"  {owner}: {days:g} 人天")

    declared = re.search(
        r"总工作量 ([\d.]+) 人天（(\d+) 张卡）", KANBAN.read_text(encoding="utf-8")
    )
    if declared and (
        declared.group(1) != f"{total:g}" or declared.group(2) != str(len(cards))
    ):
        print(
            f"⚠ 看板第 1 节写的 {declared.group(1)} 人天 / {declared.group(2)} 张，"
            f"与实际 {total:g} 人天 / {len(cards)} 张不一致，请更新看板文字",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
