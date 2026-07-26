# estoque-medicamento-cdc

Segundo repositório do projeto de estoque. Ele não possui banco analítico próprio.

## Responsabilidades

- executar um cluster Kafka de três nós em modo KRaft;
- executar Kafka Connect com o conector PostgreSQL do Debezium;
- capturar alterações do PostgreSQL OLTP do repositório `estoque-banco`;
- processar eventos de medicamentos, lotes e movimentações;
- manter no Redis o estado necessário ao dashboard;
- publicar comandos no tópico `reabastecimento`;
- exibir dados no Streamlit com atualização automática.

## Fluxo

```text
estoque-banco → PostgreSQL/WAL → Debezium → Kafka → consumer Python → Redis → Streamlit
                                                               └→ reabastecimento → estoque-banco
```

## Serviços

| Serviço | Endereço no host |
|---|---|
| Kafka 1 | `localhost:19090` |
| Kafka 2 | `localhost:19091` |
| Kafka 3 | `localhost:19092` |
| Kafka Connect | `http://localhost:8083` |
| Redis | `localhost:6379` |
| Dashboard | `http://localhost:8501` |

## Primeira execução

```bash
poetry install
```

Confira `infra/debezium/connector.env` e então execute:

```bash
make run
```

No Windows com MinGW:

```powershell
mingw32-make run
```

## Recriar o pipeline e solicitar novo snapshot

Quando a arquitetura ou o grupo consumidor mudar, use:

```bash
make reset
```

Esse comando apaga os volumes Kafka e Redis, registra novamente o conector e permite que o snapshot inicial seja processado do zero.
