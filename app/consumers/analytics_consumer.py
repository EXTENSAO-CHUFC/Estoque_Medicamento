from __future__ import annotations
import json, logging
from kafka import KafkaConsumer, KafkaProducer
from app.config.database import SessionLocal
from app.config.settings import settings
from app.consumers.cdc_parser import parse_debezium_message
from app.services.analytics_service import AnalyticsService
from app.services.cache_service import CacheService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

def table_from_topic(topic: str) -> str:
    return topic.rsplit(".", 1)[-1]

def main() -> None:
    consumer = KafkaConsumer(
        *settings.cdc_topics,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="estoque-analytics-v1",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda value: value,
    )
    producer = KafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers, value_serializer=lambda value: json.dumps(value).encode())
    cache = CacheService()
    log.info("Consumindo: %s", ", ".join(settings.cdc_topics))
    for message in consumer:
        table = table_from_topic(message.topic)
        event = parse_debezium_message(message.value)
        row = event.get("after") or event.get("before")
        try:
            with SessionLocal() as session:
                service = AnalyticsService(session)
                medicamento_id = service.apply(table, event)
                if row and "id" in row:
                    cache.set_entity(table, int(row["id"]), event.get("after"))
                if medicamento_id is not None:
                    stock = service.current_stock(medicamento_id)
                    cache.set_stock(medicamento_id, stock)
                    threshold = int(settings.replenishment_target_stock * settings.replenishment_threshold)
                    if stock <= threshold and not service.replenishment_blocked(medicamento_id):
                        quantity = max(settings.replenishment_target_stock - stock, 0)
                        if quantity:
                            producer.send(settings.replenishment_topic, {"medicamento_id": medicamento_id, "quantidade": quantity})
                            service.save_alert(medicamento_id, quantity, stock)
                session.commit()
            consumer.commit()
        except Exception:
            log.exception("Falha ao processar evento de %s", message.topic)

if __name__ == "__main__":
    main()
