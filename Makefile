.PHONY: setup start-services register-connector init-analytics-schema start-consumers start-alert-job start-dashboard test clean

# Configuração: inicia os serviços, registra o conector, inicializa o esquema analítico
setup: start-services register-connector init-analytics-schema

# Inicia os serviços (Kafka, Connect, Redis, Postgres Analytics)
start-services:
	docker-compose up -d

# Registra o conector do Debezium
register-connector:
	./connect/register-connector.sh

# Inicializa o esquema analítico do banco de dados
init-analytics-schema:
	python -m src.models.analytics_schema

# Inicia os consumidores CDC (indicadores)
start-consumers:
	python -m src.consumers.indicadores

# Inicia o job periódico de alertas (opcional)
start-alert-job:
	python -m src.jobs.varredura_alertas

# Inicia o dashboard do Streamlit
start-dashboard:
	streamlit run dashboard/app.py

# Executa os testes (placeholder)
test:
	@echo "Nenhum teste definido ainda."

# Limpar: para e remove os contêineres, volumes e imagens
clean:
	docker-compose down -v
	@echo "Contêineres e volumes limpos."