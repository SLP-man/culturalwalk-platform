-- 本地开发库初始化：只装扩展，不建业务表（业务表由 alembic 管理）
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- 关键词模糊搜索（避免一上来就上向量库）
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
