from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    database_url: str = "postgresql+asyncpg://promptreview:promptreview@localhost:5432/promptreview"
    anthropic_api_key: str = ""

    review_model: str = "claude-sonnet-4-20250514"
    review_schedule_hour: int = 2
    review_max_doc_chars: int = 50_000

    host: str = "0.0.0.0"
    port: int = 8000


settings = Settings()
