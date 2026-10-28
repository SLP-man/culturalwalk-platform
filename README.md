# 文化行走 CulturalWalk

按**时间 / 预算 / 文化主题**规划一条能照着走的城市文化路线，并且让用户把自己的走法**投稿、审核、发布**成社区路线。

> 这是一个**骨架仓库**：文档、契约、目录、CI、示例模块都已就位，业务逻辑（端点实现、算法、审核流）留给组员按任务卡认领。
> 当前状态见 [`CHANGELOG.md`](CHANGELOG.md)；要做什么见 [`docs/01-模块与任务看板.md`](docs/01-模块与任务看板.md)。

---

## 1. 它解决什么

打开任何旅游 App，你拿到的都是「本地热门景点 Top 10」。照着走完，大概率是：排了两小时队、预算超了一半、回来只记得哪里人多——**文化成了背景板，你只是路过**。

CulturalWalk 给的不是一张更好的榜单，而是**一条当地独有、有传承脉络、带着乡土气的文化线路**——走完你不是"打过卡"，而是**真的经历了一段中国文化**：知道它的来历、看见它还活在当地人的日子里、说得清它为什么长这样。

> 只有半天、带着老人、预算 200 块、想看「老长沙的市井气」——
> 它给的是**这几处为什么该放在一起、先后怎么走、每一处文化上有什么讲究**的一条路，
> 而不是十个名字。

**时间、预算、体力是硬框，文化是框里的内容**：框先卡死（走不通的方案直接不出），剩下的空间里，装的是有来历的文化，不是凑数的热门景点。

| 普通推荐 | 这里 |
|---|---|
| 一串热门地点，谁看都一样 | 一条**有主题的文化线路**：2–3 个相邻主题分段讲，每段都说得清"这一段在讲什么"、段与段之间为什么接得上 |
| 只按热度排 | 先用**你的时间 / 预算 / 体力 / 同行人**卡死可行性（框是硬的），再按**文化主题**选点排顺 |
| 文化说明是模型编的，看着还挺像 | 每个说法**挂着来源**：文献、**官方网站/地方志**、口述记录；查不到就标「待核实」，不假装确定 |
| 网红打卡、人人皆知 | 选**本地人真在过日子**的地方，有纵深（谁 → 什么年代 → 变成什么），不必是那几个人人都知道的地方 |
| 推荐完就结束 | 可保存、可分享；本地人能把**自己的走法投稿**，审核后进入社区，被更多人照着走、评论补充 |

一句话：**别人卖「哪里值得去」，我们给「你这一次该怎么走，以及这一路的文化到底讲了什么」——让你从路过的人，变成经历过的人。**

**为谁做**：**外地第一次来长沙的年轻游客**——他们最缺的不是「去哪」，而是「哪几处真值得看、为什么值得」这层信息差。

**打开后先看到什么**：先读**这条线路的故事**——这几处为什么被放在一起、串起来讲的是哪一段文化、每一处有什么讲究；觉得有意思了，再**展开成能照着走的行程表**（几点到哪、怎么走、花多少）。不是一上来甩给你一张时间表。

**社区怎么排**：人人可发，**审核把关**；列表默认按**收藏数**排，好的路线自己浮上来，不看谁发得早。

第二条主线是社区：用户写自己的路线 → 管理员审核 → 发布。审核看的是**某个具体版本的内容 hash**，通过后发布的也是这个版本 —— 中途被改过就发不出去。

### 文化合格线（一条线路要过的四道关）

一条路线/行程只要有一条明显不成立，就不算合格产出，只能算"景点串烧"：

| # | 关卡 | 具体要求 |
|---|---|---|
| 1 | **有据可查** | 每处的来历、年代、人物、说法都要挂来源；优先官方网站、地方志、学术资料，其次可靠口述。**没有来源的说法不许写成事实** |
| 2 | **有生活气** | 能看见当地人怎么过日子（菜市场、老街铺子、社区戏台）；不是"某某曾在此居住"的牌子墙 |
| 3 | **有纵深** | 说得出传承链路：谁 → 什么年代 → 变成什么、留下了什么；不许用"历史悠久""文化底蕴深厚"糊过去 |
| 4 | **有独特性** | 当地独有、或至少是本地才有的形态；人人都知道、每个城市都有的东西，不能当主线 |

外加一条编排要求：**一条线路 2–3 个相邻主题，分段讲，每段要有过渡说明**，不许无理由拼盘。

## 2. 一分钟跑起来

```bash
# 0) 依赖：Docker Desktop、Python 3.12、Node 20 + pnpm
git clone <this-repo> && cd culturalwalk-platform

# 1) 起数据库和对象存储
cd infra && cp .env.example .env && docker compose up -d db minio && cd ..

# 2) 后端
cd services/api
python -m venv .venv
.venv/Scripts/activate        # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
# → http://localhost:8000/docs

# 3) 前端（另开一个终端）
cd apps/web
pnpm install
pnpm gen          # 由契约生成 TS 类型
pnpm dev
# → http://localhost:5173
```

国内网络慢的话换镜像：

```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -e ".[dev]"
pnpm install --registry https://registry.npmmirror.com
```

或用 Dev Container（VS Code 里 Reopen in Container），`setup.sh` 会自动装依赖、起服务、跑迁移。

## 3. 仓库结构

```
culturalwalk-platform/
├── docs/                     ← 先读这里，代码是文档的落地
│   ├── 00-总体开发文档.md      产品定位、架构、范式、里程碑
│   ├── 01-模块与任务看板.md    每个模块谁负责、拆成哪些可认领的卡
│   ├── 02-数据模型与状态机.md  表、字段、四套状态机、并发规则
│   ├── 03-接口契约规范.md      路径命名、错误码、分页、幂等、鉴权
│   ├── 04-开发环境与协作.md    git 流程、分支、提交规范、评审清单
│   ├── 05-演示脚本与验收.md    答辩 6 分钟怎么演、验收逐条打勾
│   └── api/openapi.yaml      ← 契约唯一真源，前后端都从它生成/校验
├── services/api/             ← FastAPI 模块化单体
│   ├── app/core/             配置、DB、依赖、错误信封
│   ├── app/modules/<模块>/   models / repository / service / router / schemas / tests
│   └── migrations/           alembic（只有 P3 写）
├── apps/web/                 ← Vue 3 + Vite
│   └── src/modules/<模块>/   一个目录 = 一张（或几张）任务卡
├── packages/contracts/       契约 → TS 类型生成器
├── infra/                    docker-compose、数据库初始化、环境变量样例
├── tasks/                    任务卡清单（cards.json / cards.yml / 认领清单.md，脚本生成）
└── scripts/                 契约自检、骨架生成、任务卡生成、批量开 issue
```

**一条规矩**：`docs/api/openapi.yaml` 改了才能改端点签名；类型由它生成，不许手写 `interface RouteDTO`。

## 4. 模块一览

| 模块 | 负责 | 不负责 |
|---|---|---|
| `identity` | 注册登录、用户档案、角色 | 权限判断（在 `core/deps`） |
| `catalog` | 地点、文化主题、来源链接 | 组排（在 `planner`） |
| `routes` | 草稿、节点顺序、版本快照 | 谁批准（在 `moderation`） |
| `discovery` | 公开列表/详情/首页聚合（只读，无表） | 任何写操作 |
| `moderation` | 审核队列、通过/退回、发布/下线 | 内容编辑 |
| `community` | 评论、收藏 | 台账类计数（走聚合） |
| `planner` | 规划输入→四步流水线→行程 | 发布（只能转草稿） |
| `media` | 图片上传、隔离区、清理 | 业务对象引用 |
| `notifications` | 站内通知 | 邮件/短信（LATER） |
| `audit` | 操作留痕、只读查询 | 业务状态变更 |

细节（含依赖方向、禁止调用）见 [`docs/00-总体开发文档.md`](docs/00-总体开发文档.md) 第 4 节。

## 5. 怎么认领工作

任务卡**已经全部建成 GitHub Issues（57 条）**：<https://github.com/SLP-man/culturalwalk-platform/issues?q=is%3Aissue>

1. 打开 Issues，用标签筛自己的模块，比如 `label:identity`、`label:M1`；
2. 在右侧 **Assignees** 里点 *assign yourself*，这张卡就是你的了；
3. 开 PR 时正文写 `Closes #12`，合并后 issue 自动关闭，看板自动推进。

M0 的 6 张卡（骨架 / 后端骨架 / 前端骨架 / CI / 契约链路 / 一键启动）已在初始提交完成，已关闭并附证据评论；
`M0-07 种子数据脚本` 还空着，适合当第一张练手卡。

刚接触这个项目？只读两份：

- 人 → [**`docs/必读2-零基础全流程.md`**](docs/必读2-零基础全流程.md)：零基础全流程（准备 → 领卡 → 和 AI 说话 → 验收 → 合并）
- AI 助手 → [**`docs/必读1-开发约定.md`**](docs/必读1-开发约定.md)：一页纸讲完全部规矩，丢给 agent 就能开工

改了看板要补建 issue 时：`python scripts/create_issues.py --dry-run` 先看，去掉 `--dry-run` 真建（同标题跳过，可反复跑）。

## 6. 开发范式（几条硬规矩）

1. **契约先行**：先改 `openapi.yaml` → 跑 `python scripts/check_contract.py` → 再写实现。
2. **分层不许穿透**：`router` 只做编解码，`service` 写规则，`repository` 碰 SQL。router 里出现 `select(` 就是错的。
3. **状态机只管一处**：状态流转写在 `service.py`，用显式函数，不许散落在各处的 if。
4. **负例优先**：每个端点先写「越权/非法状态/重复提交」的测试，再写正常路径。
5. **AI 产出必须可追溯**：任何模型生成的内容入库时带 `source_url` 或标 `unverified`。
6. **不引入新依赖要理由**：加库前在 PR 描述里写「为什么标准库/现有依赖不行」。

## 7. 常用命令

```bash
# 后端
pytest -q                       # 测试
ruff check . && ruff format .    # 风格
alembic revision --autogenerate -m "add xxx"   # 只有 P3 跑
alembic upgrade head

# 前端
pnpm dev / pnpm build / pnpm typecheck
pnpm gen                        # 重新生成契约类型

# 契约
python scripts/check_contract.py
```

## 8. 现在还没有的东西（别当成 bug）

- 真实的地图/大模型接入：默认 `MAP_PROVIDER=fake` `LLM_PROVIDER=fake`，离线可跑通演示链路。
- 备案、公网部署、真实支付：不在本期范围（见 `docs/00` 第 9 节）。
- 推荐算法、向量检索、离线包：LATER，先验证「有来源的地点库 + 规则组排」够不够用。
