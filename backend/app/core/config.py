from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = "development"
    secret_key: str = "change-me"

    supabase_url: str = ""
    supabase_service_key: str = ""

    gemini_api_key: str = ""

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    class Config:
        env_file = ".env"


settings = Settings()
