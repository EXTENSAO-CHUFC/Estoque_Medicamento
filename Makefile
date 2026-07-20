.PHONY: run start stop restart status logs logs-app clean reset infra schema connector consumer dashboard help

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

schema:
	$(PYTHON) -m app.models.init_db

connector:
	$(PYTHON) -m scripts.register_connector

consumer:
	$(PYTHON) -m app.consumers.analytics_consumer

dashboard:
	poetry run streamlit run app/dashboard/dashboard.py

clean: stop
	docker compose down -v --remove-orphans

reset: clean run

help:
	@echo "Comandos principais:"
	@echo "  make run       Sobe infraestrutura, schema, Debezium, consumer e dashboard"
	@echo "  make stop      Encerra processos e containers preservando os dados"
	@echo "  make restart   Reinicia todo o sistema"
	@echo "  make status    Mostra containers e processos Python"
	@echo "  make logs      Acompanha logs dos containers"
	@echo "  make clean     Encerra tudo e apaga o volume do banco analítico"
	@echo "  make reset     Recria tudo do zero"
