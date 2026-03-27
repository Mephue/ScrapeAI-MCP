from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    scraper_service_url: str = "http://localhost:8001"
    mcp_store_path: str = "/tmp/mcp_store.json"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

