# estoque_medicamento-cdc

Este repositório contém os componentes de análise e CDC (Change Data Capture) para a solução de gerenciamento de estoque.

## Arquitetura

- **Conector Debezium** captura alterações do banco de dados PostgreSQL de origem (do repositório `estoque-banco`) e as publica em tópicos Kafka.
- **Kafka Connect** executa o conector Debezium.
- **Consumidores Python** processam os eventos CDC:
  - `cdc_parser.py`: analisa mensagens Debezium.
  - `stage_redis.py`: atualiza o cache Redis com níveis de estoque em tempo real.
  - `indicadores.py`: calcula indicadores (por exemplo, níveis de estoque) e dispara solicitações de reposição quando o estoque estiver ≤ 10% e não bloqueado.
- **PostgreSQL Analítico** armazena dados agregados para relatórios.
- **Jobs**: tarefas periódicas (por exemplo, `varredura_alertas.py`) que verificam condições e geram alertas.
- **Dashboard**: aplicação Streamlit (`dashboard/app.py`) para visualização de níveis de estoque, movimentações e alertas.

## Estrutura do Diretório

- `docker-compose.yml`: define os serviços (Kafka, Kafka Connect, Redis, PostgreSQL Analítico).
- `connect/`: configuração do conector Debezium e script de registro.
- `src/`: código-fonte Python.
  - `config/`: gerenciamento de configuração.
  - `consumers/`: consumidores Kafka para processamento CDC.
  - `models/`: definições de esquema do banco de dados analítico.
  - `jobs/`: trabalhos em segundo plano.
  - `dashboard/`: painel Streamlit.
- `tests/`: testes unitários (a serem implementados).
- `README.md`: este arquivo.

## Como Começar

### Pré-requisitos

- Docker e Docker Compose
- Python 3.12 (recomendado, gerenciado via pyenv)
- Poetry (para gerenciamento de dependências)
- Repositório `estoque-banco` já em execução (veja a seção "Observações")

### Configuração

1. **Clone o repositório** (se ainda não o fez).

2. **Configure o ambiente Python**:
   ```bash
   pyenv install 3.12.10
   pyenv local 3.12.10
   poetry install
   ```

3. **Inicie os serviços**:
   ```bash
   docker compose up -d
   ```

4. **Registre o conector Debezium**:
   ```bash
   ./connect/register-connector.sh
   ```
   (O script aguarda o Kafka Connect ficar pronto e então registra o conector.)

5. **Inicialize o esquema do banco de dados analítico**:
   ```bash
   python -m src.models.analytics_schema
   ```
   (Este script cria as tabelas necessárias no banco de dados PostgreSQL analítico.)

6. **Inicie os consumidores CDC**:
   ```bash
   python -m src.consumers.indicadores
   ```

7. **Inicie o job periódico de alertas** (opcional):
   ```bash
   python -m src.jobs.varredura_alertas
   ```

8. **Inicie o painel**:
   ```bash
   streamlit run src/dashboard/app.py
   ```

## Como Funciona

1. O repositório `estoque-banco` executa o banco de dados OLTP principal (PostgreSQL) com replicação lógica habilitada, de forma totalmente independente — ele não conhece este repositório nem o Kafka.
2. O Debezium captura operações `INSERT`, `UPDATE` e `DELETE` nas tabelas `medicamentos`, `lotes`, `movimentacoes`, `fornecedores`, `almoxarifados` e `usuarios`, e as publica em tópicos Kafka.
3. O consumidor `indicadores.py`:
   - Escuta os tópicos CDC relevantes.
   - Atualiza um cache Redis com os níveis mais recentes de estoque (derivados de `lotes` e `movimentacoes`).
   - Monitora a flag `bloqueio_reabastecimento` da tabela `medicamentos`.
   - Quando o saldo de um lote cai para ≤ 10% do `estoque_maximo` e o medicamento não está bloqueado, publica uma mensagem no tópico `reabastecimento`.
4. O `consumidor_reabastecimento.py`, que mora no repositório `estoque-banco`, consome o tópico `reabastecimento` e registra a movimentação de `ENTRADA` no banco de dados OLTP — fechando o ciclo. Este repositório nunca escreve diretamente no banco transacional.
5. O banco de dados analítico recebe os dados processados pelos consumidores CDC, alimentando os indicadores.
6. O painel fornece visibilidade em tempo real dos níveis de estoque, movimentações e alertas.

## Observações

- Certifique-se de que o repositório `estoque-banco` esteja em execução e seu banco de dados seja acessível via `host.docker.internal:5433` a partir dos contêineres desta stack.
- Ajuste as variáveis de ambiente em `docker-compose.yml` ou em arquivos `.env` conforme necessário para sua configuração.
- Os arquivos `consumers/indicadores.py` e `jobs/varredura_alertas.py` contêm lógica simplificada; adapte os critérios de reposição às suas regras de negócio.
- Este repositório **não hospeda o banco transacional nem escreve nele diretamente** — toda escrita no OLTP acontece do lado do `estoque-banco`, mesmo quando originada por um evento detectado aqui. O isolamento entre os dois repositórios é intencional.
- Evolução futura possível: substituir o PostgreSQL analítico por uma ferramenta OLAP dedicada, como o ClickHouse, caso o volume de dados justifique consultas colunares otimizadas para agregações.

## Licença

MIT