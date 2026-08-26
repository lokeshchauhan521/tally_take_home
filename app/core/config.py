from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Tally XML Ingestion API"
    app_env: str = "development"
    database_url: str = "sqlite:///./tally.db"
    upload_max_size_mb: int = 10
    secret_key: str = "development-secret-key"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
