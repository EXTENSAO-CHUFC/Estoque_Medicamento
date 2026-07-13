"""
Armazena os níveis de estoque atualizados no Redis para acesso em tempo real.
"""
import json
import redis
from . import cdc_parser
from ..config import settings

def get_redis_client():
    return redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)

def update_stock_from_cdc_event(topic: str, event: dict):
    """
    Atualiza o Redis com as informações mais recentes de estoque com base em um evento CDC.
    Assumimos que o tópico está no formato 'dbserver1.public.nome_da_tabela'.
    """
    r = get_redis_client()
    parsed = cdc_parser.parse_debezium_message(event.get('value', b'') if isinstance(event.get('value'), bytes) else event.get('value'))
    details = cdc_parser.extract_change_details(parsed)
    
    # Por simplicidade, armazenaremos apenas o estado mais recente da entidade como JSON
    # Formato da chave: <nome_da_tabela>:<id>
    # Precisamos saber o nome da tabela a partir do tópico.
    # Em um cenário real, analisaríamos o tópico para obter a tabela.
    # Por enquanto, pularemos os detalhes de implementação e mostraremos apenas o conceito.
    pass

def get_stock_from_cache(table_name: str, record_id: int) -> dict:
    """
    Recupera o estado armazenado em cache de um registro.
    """
    r = get_redis_client()
    key = f"{table_name}:{record_id}"
    data = r.get(key)
    if data:
        return json.loads(data)
    return None