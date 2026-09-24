from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SG_", env_file=".env", extra="ignore")

    # SQLAlchemy URL (psycopg 3 driver); procrastinate dostane rovnakú DB bez "+psycopg"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/smartgrocery"

    storage_dir: Path = Path("./data/raw")
    raw_retention_days: int = 90

    # Extrakcia – Claude vision. ANTHROPIC_API_KEY sa číta priamo SDK.
    llm_model: str = "claude-opus-5"
    llm_effort: str = "high"
    llm_max_tokens: int = 16000
    llm_server_fallbacks: bool = True
    # cena za 1M tokenov (USD) – na výpočet nákladov behu, overiť podľa cenníka
    llm_price_input_per_mtok: Decimal = Decimal("5")
    llm_price_output_per_mtok: Decimal = Decimal("25")
    llm_daily_cost_limit_usd: Decimal = Decimal("5")

    extraction_version: str = "claude-vision-v1"
    parser_version: str = "pdf-render-v1"
    render_dpi: int = 170

    check_interval_minutes: int = 30
    http_user_agent: str = "SmartGroceryBot/0.1 (+mailto:change-me@example.com)"

    admin_token: str = "change-me"

    @property
    def procrastinate_conninfo(self) -> str:
        return self.database_url.replace("postgresql+psycopg://", "postgresql://")


@lru_cache
def get_settings() -> Settings:
    return Settings()
