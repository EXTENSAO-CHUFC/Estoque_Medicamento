"""
Analisador (parser) de eventos de mudança do Debezium.
"""
import json
from typing import Dict, Any, Optional

def parse_debezium_message(message_value: bytes) -> dict:
    """
    Analisa uma mensagem JSON do Debezium.
    Retorna um dicionário com as chaves: 'before', 'after', 'op', 'ts_ms'.
    """
    try:
        payload = json.loads(message_value.decode('utf-8'))
        # Envelope do Debezium
        # {
        #   "schema": {...},
        #   "payload": {
        #       "before": {...},
        #       "after": {...},
        #       "op": "c|u|d|r",
        #       "ts_ms": ...
        #   }
        # }
        payload_data = payload.get('payload', {})
        return {
            'before': payload_data.get('before'),
            'after': payload_data.get('after'),
            'op': payload_data.get('op'),
            'ts_ms': payload_data.get('ts_ms')
        }
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"Mensagem inválida do Debezium: {e}")

def extract_change_details(parsed: dict) -> dict:
    """
    Extrai os campos relevantes para o nosso caso de uso.
    Por simplicidade, assumimos que a tabela é 'medicamentos' ou 'movimentacoes'.
    """
    op = parsed['op']
    # Determinar qual tabela mudou olhando os metadados da fonte? 
    # No Debezium, a tabela de origem fica no campo 'source'.
    # Mas, por simplicidade, assumiremos que quem chamou a função conhece o tópico.
    # Retornaremos a operação e os estados anterior (before) e posterior (after).
    return {
        'operation': op,
        'before': parsed['before'],
        'after': parsed['after'],
        'timestamp': parsed['ts_ms']
    }