#!/usr/bin/env bash
# 提交 PR 之前跑这一条，替代“我记得好像跑过测试”。
#
#   bash scripts/preflight.sh          # 全跑（后端 + 前端 + 契约）
#   bash scripts/preflight.sh web      # 只跑前端（改页面时用，快）
#   bash scripts/preflight.sh api      # 只跑后端
#
# 任何一项失败，脚本以非 0 退出，并告诉你是哪一项。
# 后端测试要能连数据库；没起就先：
#   docker compose -f infra/docker-compose.yml up -d
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
SCOPE="${1:-all}"
FAILED=()

# ---- 找 pnpm ---------------------------------------------------------------
# PATH 里有就直接用；没有就试几个常见位置（Windows 的 Git Bash 经常不带）。
# 找到的是 pnpm.cjs 这种脚本时，用同一个 node 去跑它。
NODE_BIN="$(command -v node 2>/dev/null || true)"
PNPM_CMD=()

if command -v pnpm >/dev/null 2>&1; then
  PNPM_CMD=(pnpm)
else
  for cjs in \
    "$HOME/AppData/Local/pnpm/pnpm.cjs" \
    "$HOME/AppData/Local/pnpm/bin/pnpm.cjs" \
    "$HOME/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/pnpm/bin/pnpm.cjs"
  do
    if [ -f "$cjs" ]; then
      if [ -z "$NODE_BIN" ]; then
        for n in "$HOME/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/node/bin/node.exe" \
                 "/c/Program Files/nodejs/node.exe"; do
          [ -x "$n" ] && NODE_BIN="$n" && break
        done
      fi
      if [ -n "$NODE_BIN" ]; then
        PNPM_CMD=("$NODE_BIN" "$cjs")
        break
      fi
    fi
  done
fi

if (( ${#PNPM_CMD[@]} == 0 )); then
  echo "找不到 pnpm。先装：npm i -g pnpm"
  echo "或者手动指定：PNPM_CMD='/path/to/pnpm' bash scripts/preflight.sh"
  exit 2
fi
echo "pnpm: ${PNPM_CMD[*]}"

# pnpm 跑包脚本时还会再调用 node；PATH 里没有 node 时补上（Git Bash 常见）
if ! command -v node >/dev/null 2>&1 && [ -n "$NODE_BIN" ]; then
  export PATH="$(dirname "$NODE_BIN"):$PATH"
fi

pnpm_run() { "${PNPM_CMD[@]}" "$@"; }

# ---- 跑检查 ---------------------------------------------------------------
step() { printf '\n== %s\n' "$1"; }

run() { # run <名字> <命令...>
  local name="$1"; shift
  step "$name"
  if "$@"; then
    echo "  OK  $name"
  else
    echo "  FAIL $name"
    FAILED+=("$name")
  fi
}

if [[ "$SCOPE" == "all" || "$SCOPE" == "api" ]]; then
  run "后端 lint"      bash -c 'cd services/api && ruff check . && ruff format --check .'
  run "后端测试"       bash -c 'cd services/api && python -m pytest -q'
fi

if [[ "$SCOPE" == "all" || "$SCOPE" == "web" ]]; then
  run "前端类型检查"   pnpm_run -C apps/web typecheck
  run "前端单测"       pnpm_run -C apps/web test
  run "前端构建"       pnpm_run -C apps/web build
fi

if [[ "$SCOPE" == "all" ]]; then
  run "契约自检"       python scripts/check_contract.py
  run "任务卡与看板一致" bash -c 'python scripts/gen_cards.py >/dev/null && git diff --quiet -- tasks/ || { echo "tasks/ 与看板不一致：重新生成并提交"; false; }'
fi

printf '\n'
if (( ${#FAILED[@]} == 0 )); then
  echo "全部通过，可以开 PR"
  exit 0
fi
echo "失败项：${FAILED[*]}"
echo "修完再提交；如果是新发现的问题，顺手补一条 docs/问题与回滚台账.md"
exit 1
