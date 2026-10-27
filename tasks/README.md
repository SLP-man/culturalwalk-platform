# 任务卡（认领用）

> **不想读文件？** 任务已经全部建成了 GitHub Issues，直接去
> <https://github.com/SLP-man/culturalwalk-platform/issues?q=is%3Aissue> 挑一张，点 **Assign yourself** 就行。
> 第一次上手先看 [`docs/必读2-零基础全流程.md`](../docs/必读2-零基础全流程.md)。

这里的文件都由脚本生成，**不要手改**：

| 文件 | 用途 |
|---|---|
| `cards.yml` | 机读+人读，建 issue 用 |
| `cards.json` | 同上，给不装 yaml 的工具用 |
| `认领清单.md` | 不联网时也能看的纯 Markdown 版 |
| `issues.csv` / `issue-map.json` | 卡 ↔ issue 号 对照表（建完 issue 后自动写回） |

真源是 [`docs/01-模块与任务看板.md`](../docs/01-模块与任务看板.md)：改任务只改那张表，然后

```bash
python scripts/gen_cards.py     # 从看板重新生成 cards.yml / cards.json / 认领清单.md
```

看板第 1 节写的「总工作量 X 人天 / Y 张卡」和实际不一致时，这个脚本会报错退出，避免两处数字对不上。

## 开 issue

57 张卡**已经建好了**（2026-10-27，其中 6 张 M0 已完成并关闭）。只有改了看板、需要补建时才跑：

```bash
python scripts/create_issues.py --dry-run   # 只看会建哪些
GITHUB_TOKEN=xxx python scripts/create_issues.py   # 真建
```

- 标题相同的 issue 已存在就跳过，**可以反复跑，不会重复建**；
- 会自动补齐标签：模块名 / `M1`–`M5` / `P1`–`P4` / `任务卡`；
- 跑完把 `tasks/issue-map.json` 和 `tasks/issues.csv` 一起提交。

## 认领规则

1. 一张卡只给一个人，**不要两个人同时改同一个目录**（见 `AGENTS.md` 第 1 条）。
2. 认领后 24 h 内没开 PR，卡释放，由 P1 在周会上重新分配。
3. 合并时同时更新 `CHANGELOG.md` 一行。
4. 卡之间有依赖（`depends_on`），依赖没合并就别开始下游卡。
5. 完成标准：**PR 合并 + CI 四项全绿**，然后在 issue 里贴自测结果并关闭（写 `Closes #编号` 会自动关）。
