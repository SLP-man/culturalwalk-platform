# CulturalWalk API · 核心配置
"""所有环境变量集中在这里读取，其他模块不许直接摸 os.environ。"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 应用
    app_name: str = "CulturalWalk API"
    env: str = "local"  # local | demo | prod
    api_prefix: str = "/api/v1"
    debug: bool = True

    # 数据库
    database_url: str = "postgresql+psycopg://cw:cw@localhost:5432/culturalwalk"
    db_echo: bool = False

    # 认证
    jwt_secret: str = "dev-only-change-me"
    jwt_alg: str = "HS256"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 14 * 24 * 3600

    # 对象存储
    s3_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "culturalwalk"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    media_max_bytes: int = 10 * 1024 * 1024

    # 外部 Provider（留空则走 fake 实现，便于无网演示）
    map_provider: str = "fake"  # fake | amap | tencent
    map_api_key: str = ""
    llm_provider: str = "fake"  # fake | openai-compatible
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    # 业务开关
    plan_max_days: int = 7
    review_lease_minutes: int = 30
    public_cache_seconds: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
