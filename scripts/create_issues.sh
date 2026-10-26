#!/usr/bin/env bash
# 把 tasks/cards.json 里的任务卡批量建成本仓库的 GitHub issue。
#
# 前置：装好 gh（https://cli.github.com/）并 gh auth login，在仓库根目录执行。
# 用法：
#   bash scripts/create_issues.sh --dry-run     # 只打印，不建，不需要 gh
#   bash scripts/create_issues.sh               # 真建，标题已存在的跳过
#   bash scripts/create_issues.sh --label 任务   # 建时加标签
set -euo pipefail

DRY_RUN=0
LABEL=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --label) LABEL="${2:-}"; shift 2 ;;
    *) echo "未知参数：$1"; exit 1 ;;
  esac
done

cd "$(dirname "$0")/.."

if [[ "$DRY_RUN" -eq 0 ]] && ! command -v gh >/dev/null 2>&1; then
  echo "没找到 gh。先装：https://cli.github.com/ ，再 gh auth login"
  echo "（只想预览：bash scripts/create_issues.sh --dry-run 不需要 gh）"
  exit 1
fi

PY=""
if [[ -n "${PYTHON:-}" ]] && "$PYTHON" -c 'import json' >/dev/null 2>&1; then
  PY="$PYTHON"
fi
if [[ -z "$PY" ]]; then
  for c in python3 python py; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import json' >/dev/null 2>&1; then
      PY="$c"
      break
    fi
  done
fi
if [[ -z "$PY" ]]; then
  echo "没找到可用的 python。装 Python 3.10+，或按 tasks/认领清单.md 手工建 issue。"
  exit 1
fi

"$PY" - "$DRY_RUN" "$LABEL" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

dry_run = sys.argv[1] == "1"
label = sys.argv[2]
cards = json.loads(Path("tasks/cards.json").read_text(encoding="utf-8"))

existing = set()
if not dry_run:
    try:
        out = subprocess.run(
            ["gh", "issue", "list", "--limit", "500", "--json", "title"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        existing = {item["title"] for item in json.loads(out)}
    except Exception:
        existing = set()

created = 0
skipped = 0
for card in cards:
    title = f"[{card['id']}] {card['title']}"
    if title in existing:
        skipped += 1
        continue
    body = "\n".join(
        [
            f"**模块**：{card['module']}　**里程碑**：{card['milestone']}",
            f"**建议负责人**：{card['owner']}　**估时**：{card['estimate_days']:g} 人天",
            f"**依赖**：{card['depends_on']}",
            "",
            "**输出（要建出来的东西）**",
            card["deliverable"],
            "",
            "**验收标准**",
            card["accept"],
            "",
            "---",
            "认领方式：在本 issue 下回一句「我来」。规则见 `CONTRIBUTING.md` 第 2 节。",
            "全部任务见 `docs/01-模块与任务看板.md`。",
        ]
    )
    if dry_run:
        print("—" * 60)
        print(title)
        print(body)
        continue
    cmd = ["gh", "issue", "create", "--title", title, "--body", body]
    if label:
        cmd += ["--label", label]
    subprocess.run(cmd, check=True)
    created += 1
    print(f"已创建：{title}")

if dry_run:
    print("—" * 60)
    print(f"（dry-run）共 {len(cards)} 张卡，全部可建")
else:
    print(f"完成：新建 {created} 张，跳过已存在 {skipped} 张")
PY
