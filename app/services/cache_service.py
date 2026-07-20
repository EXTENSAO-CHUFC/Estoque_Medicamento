from __future__ import annotations
import json
import redis
from app.config.settings import settings

class CacheService:
    def __init__(self):
        self.client = redis.Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True)

    def set_entity(self, table: str, record_id: int, payload: dict | None) -> None:
        key = f"cdc:{table}:{record_id}"
        if payload is None:
            self.client.delete(key)
        else:
            self.client.set(key, json.dumps(payload, default=str))

    def set_stock(self, medicamento_id: int, stock: int) -> None:
        self.client.set(f"estoque:medicamento:{medicamento_id}", stock)
