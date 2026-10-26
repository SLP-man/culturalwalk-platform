# services/api（占位）

模块化单体 API，一个部署单元。计划使用 FastAPI + Pydantic + SQLAlchemy/Alembic，数据库 PostgreSQL。

**当前未生成代码**，等 ADR-0012（后端框架）与整体结构定稿后再初始化。

## 定稿后的模块边界（草案）

`identity`、`nodes`、`routes`、`submissions`、`navigation`、`ai_drafting`、`media`、`audit`

> 模块目录暂不创建，避免先入为主；模块只通过接口/端口互相依赖。

## 如果以后要改位置

```bash
git mv services/api backend    # 例：扁平化成 backend/
```
