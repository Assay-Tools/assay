"""Assay configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./assay.db"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Submission auth — comma-separated API keys for evaluation submissions
    submission_api_keys: str = ""
    # Admin auth — comma-separated API keys for approve/reject and admin endpoints
    admin_api_keys: str = ""

    # GitHub OAuth (for contributor auth)
    github_client_id: str = ""
    github_client_secret: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_report: str = ""  # Price ID for $99 one-time report
    stripe_price_monitoring: str = ""  # Price ID for $3/mo recurring
    app_url: str = "https://assay.tools"  # For Stripe redirect URLs

    # Discovery
    github_token: str = ""  # GitHub PAT for 5,000 req/hr (vs 60 unauthenticated)
    smithery_token: str = ""  # Smithery.ai API token for registry access
    glama_token: str = ""  # Glama.ai API token (if required)
    docker_hub_token: str = ""  # Docker Hub token for higher rate limits

    # Evaluation
    anthropic_api_key: str = ""
    eval_model: str = "claude-haiku-4-5-20251001"
    eval_batch_size: int = 10

    # Paths
    base_dir: Path = Path(__file__).parent.parent.parent

    model_config = {
        "env_file": (".env", ".secrets"), "env_file_encoding": "utf-8", "extra": "ignore",
    }


settings = Settings()
