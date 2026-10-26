# 任务卡（认领用）

这里的三个文件都由脚本生成，**不要手改**：

| 文件 | 用途 |
|---|---|
| `cards.json` | 机读版，`scripts/create_issues.sh` 用它建 issue |
| `cards.yml` | 人读版，review diff 方便 |
| `认领清单.md` | 没装 gh / python 的人直接看这个 |

真源是 [`docs/01-模块与任务看板.md`](../docs/01-模块与任务看板.md)：改任务只改那张表，然后

```bash
python scripts/gen_cards.py     # 从看板重新生成上面三个文件
```

看板第 1 节写的「总工作量 X 人天 / Y 张卡」和实际不一致时，这个脚本会报错退出，避免两处数字对不上。

## 开 issue

```bash
bash scripts/create_issues.sh --dry-run   # 先看会建哪些
bash scripts/create_issues.sh             # 真建，标题已存在的会跳过
```

需要先 `gh auth login`。不想装 gh 就用 `认领清单.md` 手工建，内容一样。

## 认领规则

1. 一张卡只给一个人，**不要两个人同时改同一个目录**（见 `AGENTS.md` 第 1 条）。
2. 认领后 24 h 内没开 PR，卡释放，由 P1 在周会上重新分配。
3. 合并时同时更新 `CHANGELOG.md` 一行。
4. 卡之间有依赖（`depends_on`），依赖没合并就别开始下游卡。
