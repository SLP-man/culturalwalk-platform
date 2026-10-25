# 协作规范（初稿）

## 分支与 PR

- `main` 受保护：禁止直接 push，必须 PR + 至少 1 人 approve + CI 通过
- 分支命名：`feat/web-h5-route-list`、`fix/api-409-conflict`、`docs/adr-0002`
- 一个 PR 只做一件事；结构大改先开 Issue 说明理由
- 8 人分两组，按业务领域切分写边界，不要按「前端组 / 后端组」互相改文件

## 提交信息

采用 Conventional Commits 简版：

```text
feat: 新增路线列表页
fix: 修复重复提交返回 500
docs: 补充 ADR-0002
refactor: 抽取坐标校验
test: 补充审核状态机负例
chore: 升级依赖
```

## 结构调整

结构未定稿期间：

1. 新增或重命名顶层目录，先在 PR 里写清楚原因
2. 使用 `git mv` 保留历史，不要「删了再建」
3. 跨模块改动拆成「契约 PR → 实现 PR」，由两个 owner 共同 review

## 评审清单

- [ ] 只改了职责范围内的文件
- [ ] 文档 / ADR 已同步
- [ ] 本地测试通过
- [ ] 没有提交 `.env`、密钥、token
- [ ] 没有把数据库 ORM 模型直接暴露成 API schema

## 数据库迁移

- 迁移集中由一个负责人审查
- 禁止多个分支同时修改同一个迁移编号
- 破坏性迁移采用 expand / contract，并写明回滚方式

## AI 协作

- AI 生成的代码必须人工 review 后才能合并
- 「AI 说可以」不是完成标准；以测试和验收标准为准
- 发现上下文冲突时先暂停并更新文档 / ADR，不要让 AI 自行拍板
