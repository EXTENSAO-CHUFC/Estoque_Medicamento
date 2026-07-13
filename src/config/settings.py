"""
Configurações do projeto
"""
import os

class Settings:
    # PostgreSQL para o Debezium
    PG_HOST = os.getenv("PG_HOST", "host.docker.internal")
    PG_PORT = int(os.getenv("PG_PORT", "5433"))
    PG_USER = os.getenv("PG_USER", "debezium_replicator")
    PG_PASSWORD = os.getenv("PG_PASSWORD", "debezium_password")
    PG_DATABASE = os.getenv("PG_DATABASE", "postgres")

    # PostgreSQL (analitico)
    PG_ANALYTICS_HOST = os.getenv("PG_ANALYTICS_HOST", "host.docker.internal")
    PG_ANALYTICS_PORT = int(os.getenv("PG_ANALYTICS_PORT", "5434"))
    PG_ANALYTICS_USER = os.getenv("PG_ANALYTICS_USER", "postgres")
    PG_ANALYTICS_PASSWORD = os.getenv("PG_ANALYTICS_PASSWORD", "postgres")
    PG_ANALYTICS_DATABASE = os.getenv("PG_ANALYTICS_DATABASE", "analytics")

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19090")

    # Redis
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

    #limite de reposição
    REPLENISHMENT_THRESHOLD = float(os.getenv("REPLENISHMENT_THRESHOLD", "0.1"))  # 10%
