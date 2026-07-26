.PHONY: run start stop restart status logs logs-app clean reset infra connector consumer dashboard redis-cli topics help

PYTHON := poetry run python

run start:
	$(PYTHON) -m scripts.iniciar

stop:
	$(PYTHON) -m scripts.encerrar

restart: stop run

status:
	$(PYTHON) -m scripts.status

logs:
	docker compose logs -f --tail=200

logs-app:
	$(PYTHON) -c "from pathlib import Path; p=Path('.runtime/logs'); print('\\n'.join(str(x) for x in sorted(p.glob('*.log'))) if p.exists() else 'Nenhum log disponível em .runtime/logs')"

infra:
	docker compose up -d --wait

connector:
	$(PYTHON) -m scripts.register_connector

consumer:
	$(PYTHON) -m app.consumers.analytics_consumer

dashboard:
	poetry run streamlit run app/dashboard/dashboard.py

redis-cli:
	docker exec -it estoque-cdc-redis redis-cli

topics:
	docker exec -it estoque-cdc-kafka1 /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka1:9092 --list

clean: stop
	docker compose down -v --remove-orphans

reset: clean run

help:
	@echo "Comandos principais:"
	@echo "  make run       Sobe Kafka KRaft, Connect, Redis, consumer e dashboard"
	@echo "  make stop      Encerra processos e containers preservando volumes"
	@echo "  make restart   Reinicia o sistema"
	@echo "  make status    Mostra containers, conector e processos Python"
	@echo "  make logs      Acompanha logs dos containers"
	@echo "  make logs-app  Lista os logs do consumer e dashboard"
	@echo "  make topics    Lista os tópicos Kafka"
	@echo "  make redis-cli Abre o redis-cli"
	@echo "  make clean     Encerra tudo e apaga Kafka/Redis"
	@echo "  make reset     Recria o pipeline e força novo snapshot"
