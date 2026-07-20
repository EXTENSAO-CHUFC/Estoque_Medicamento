from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")
from dataclasses import dataclass


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


@dataclass(frozen=True)
class Settings:
    kafka_bootstrap_servers: str = _env("KAFKA_BOOTSTRAP_SERVERS", "localhost:19090")
    topic_prefix: str = _env("CDC_TOPIC_PREFIX", "estoque")
    replenishment_topic: str = _env("REPLENISHMENT_TOPIC", "reabastecimento")

    analytics_host: str = _env("ANALYTICS_HOST", "localhost")
    analytics_port: int = int(_env("ANALYTICS_PORT", "5435"))
    analytics_database: str = _env("ANALYTICS_DATABASE", "estoque_analytics")
    analytics_user: str = _env("ANALYTICS_USER", "analytics_user")
    analytics_password: str = _env("ANALYTICS_PASSWORD", "analytics_password")

    redis_host: str = _env("REDIS_HOST", "localhost")
    redis_port: int = int(_env("REDIS_PORT", "6379"))

    replenishment_threshold: float = float(_env("REPLENISHMENT_THRESHOLD", "0.10"))
    replenishment_target_stock: int = int(_env("REPLENISHMENT_TARGET_STOCK", "100"))

    @property
    def analytics_database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.analytics_user}:{self.analytics_password}"
            f"@{self.analytics_host}:{self.analytics_port}/{self.analytics_database}"
        )

    @property
    def cdc_topics(self) -> list[str]:
        return [
            f"{self.topic_prefix}.public.medicamentos",
            f"{self.topic_prefix}.public.lotes",
            f"{self.topic_prefix}.public.movimentacoes",
        ]

settings = Settings()
