from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str
    webhook_secret: str
    public_url: str
    database_url: str
    owner_id: int
    cron_secret: str
    supabase_url: str
    supabase_service_role_key: str
    supabase_anon_key: str = ""
    storage_bucket: str = "materials"
    session_secret: str = ""
    bot_username: str = ""
    site_url: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""
    upload_limit_bytes: int = 20 * 1024 * 1024
    send_limit_bytes: int = 50 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
