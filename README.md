# Estoque Medicamento — CDC e Analytics

Segundo repositório do projeto de estoque. Ele recebe alterações do PostgreSQL OLTP por Debezium/Kafka Connect, processa os eventos, atualiza PostgreSQL analítico e Redis e disponibiliza um dashboard Streamlit.

## Arquitetura

```text
PostgreSQL OLTP (:5434)
        ↓ WAL lógico
Debezium / Kafka Connect (:8083)
        ↓
Kafka (:19090)
        ↓
Consumer analítico
   ├── PostgreSQL Analytics (:5435)
   ├── Redis (:6379)
   └── tópico reabastecimento
        ↓
Streamlit (:8501)
```

## Pré-requisitos

- Python 3.12
- Poetry
- Docker com Docker Compose v2
- GNU Make (`make` no Linux ou `mingw32-make` no Windows)
- O repositório `estoque-banco` em execução, com PostgreSQL OLTP em `localhost:5434`

Instale as dependências uma vez:

```bash
poetry install
```

## Inicialização completa

Linux:

```bash
make run
```

Windows com MinGW:

```powershell
mingw32-make run
```

O orquestrador detecta o sistema operacional e executa automaticamente:

1. verifica Docker e Docker Compose;
2. cria `.env` e `infra/debezium/connector.env` a partir dos exemplos, caso não existam;
3. verifica se o PostgreSQL OLTP responde em `localhost:5434`;
4. sobe Kafka, Kafka Connect, Redis e PostgreSQL analítico;
5. cria/valida o schema analítico;
6. registra ou atualiza o conector Debezium;
7. inicia consumidor e dashboard em segundo plano;
8. salva PIDs e logs em `.runtime/`.

Dashboard: `http://localhost:8501`

## Encerramento

Preserva o volume e os dados analíticos:

```bash
make stop
```

No Windows:

```powershell
mingw32-make stop
```

## Comandos

```text
make run       inicia todo o sistema
make stop      encerra processos e containers, preservando os dados
make restart   reinicia o sistema
make status    exibe containers, consumer e dashboard
make logs      acompanha logs dos containers
make clean     encerra tudo e remove o volume analítico
make reset     recria todo o ambiente do zero
```

Os comandos individuais (`infra`, `schema`, `connector`, `consumer` e `dashboard`) permanecem disponíveis para diagnóstico.

## Configuração

O `.env` configura Kafka, Redis, PostgreSQL analítico e regras de reabastecimento.

O arquivo `infra/debezium/connector.env` configura o acesso do Debezium ao banco OLTP. A senha deve coincidir com a senha do usuário `debezium_replicator` criada pelo primeiro repositório.

```env
OLTP_HOST=host.docker.internal
OLTP_PORT=5434
OLTP_DATABASE=estoque_banco
OLTP_USER=debezium_replicator
OLTP_PASSWORD=debezium_password
```

## Logs

```text
.runtime/logs/consumer.log
.runtime/logs/dashboard.log
```

Logs da infraestrutura Docker:

```bash
make logs
```

## Estrutura

```text
app/
├── config/
├── consumers/
├── dashboard/
├── models/
└── services/

infra/
├── debezium/
└── postgres/

scripts/
├── iniciar.py
├── encerrar.py
├── status.py
└── register_connector.py
```
