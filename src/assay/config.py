"""Assay configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./assay.db"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Evaluation
    anthropic_api_key: str = ""
    eval_model: str = "claude-haiku-4-5-20251001"
    eval_batch_size: int = 10

    # Paths
    base_dir: Path = Path(__file__).parent.parent.parent

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
