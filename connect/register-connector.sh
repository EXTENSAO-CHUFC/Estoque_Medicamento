#!/bin/bash
echo "Registrando o conector do Debezium..."

# Aguarda o Kafka Connect ficar pronto
while [ "$(curl -s -o /dev/null -w \"%{http_code}\" http://localhost:8083/connectors)" -ne 200 ]; do
  echo "Aguardando o Kafka Connect..."
  sleep 5
done

# Registra o conector
curl -X POST -H "Content-Type: application/json" \
  --data @/connectors/debezium-postgres-connector.json \
  http://localhost:8083/connectors

echo "Registro do conector concluído."