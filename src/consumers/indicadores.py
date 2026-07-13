"""
Cálculo de indicadores e acionamento de reabastecimento.
Consome eventos CDC de lotes, movimentacoes e medicamentos.
Atualiza os níveis de estoque na memória (ou Redis) e publica solicitações de reabastecimento
quando o estoque <= limite (threshold) e não estiver bloqueado.
"""
import json
import logging
from typing import Dict, Optional
from kafka import KafkaConsumer, KafkaProducer
import threading
import time

from ..config import settings
from . import cdc_parser

logger = logging.getLogger(__name__)

class IndicatorEngine:
    def __init__(self):
        self.kafka_bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self.consumer = KafkaConsumer(
            bootstrap_servers=self.kafka_bootstrap_servers,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='indicator-group',
            value_deserializer=lambda m: m  # lidaremos com a desserialização manualmente
        )
        # Inscreve-se nos tópicos relevantes
        topics = [
            'dbserver1.public.lotes',
            'dbserver1.public.movimentacoes',
            'dbserver1.public.medicamentos'
        ]
        self.consumer.subscribe(topics)
        
        self.producer = KafkaProducer(
            bootstrap_servers=self.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        self.replenishment_topic = 'reabastecimento'
        
        # Estado em memória (poderia ser substituído por Redis para escalabilidade)
        # Mapeamento: medicine_id -> {'stock': int, 'blocked': bool}
        self.medicines: Dict[int, dict] = {}
        # Mapeamento: lote_id -> medicine_id
        self.lote_to_medicine: Dict[int, int] = {}
        
        # Configuração
        self.threshold = settings.REPLENISHMENT_THRESHOLD  # fração (ex: 0.1 para 10%)
        self.target_stock = getattr(settings, 'REPLENISHMENT_TARGET_STOCK', 100)
        
        # Inicia o loop de processamento em uma thread em segundo plano
        self.running = True
        self.thread = threading.Thread(self._run, daemon=True)
        self.thread.start()
    
    def _replenish_if_needed(self, medicine_id: int):
        """Verifica se o reabastecimento é necessário para um medicamento e o aciona."""
        med = self.medicines.get(medicine_id)
        if not med:
            return
        
        stock = med['stock']
        blocked = med['blocked']
        
        # Condição: estoque <= limite * estoque_alvo? 
        # Usaremos: estoque <= limite * estoque_alvo (se o limite for uma fração)
        # Mas o requisito pode ser estoque <= limite (absoluto). 
        # Assumiremos que o limite é uma fração do estoque_alvo.
        if stock <= self.threshold * self.target_stock and not blocked:
            quantity_to_order = max(0, self.target_stock - stock)
            if quantity_to_order > 0:
                message = {
                    'medicamento_id': medicine_id,
                    'quantidade': quantity_to_order,
                    'timestamp': int(time.time() * 1000)
                }
                self.producer.send(self.replenishment_topic, value=message)
                self.producer.flush()
                logger.info(f"Reabastecimento acionado para o medicamento {medicine_id}: {quantity_to_order} unidades")
    
    def _handle_lotes_event(self, parsed: dict):
        """Processa uma mudança na tabela lotes."""
        after = parsed.get('after')
        before = parsed.get('before')
        op = parsed['op']
        
        if op == 'c':  # insert
            if after:
                lote_id = after['id']
                medicine_id = after['medicamento_id']
                quantidade = after['quantidade']
                self.lote_to_medicine[lote_id] = medicine_id
                # Inicializa o estoque do medicamento se não estiver presente
                if medicine_id not in self.medicines:
                    self.medicines[medicine_id] = {'stock': 0, 'blocked': False}
                # Adiciona a quantidade inicial
                self.medicines