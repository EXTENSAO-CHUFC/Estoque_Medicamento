"""
Modelos do SQLAlchemy para o banco de dados analítico.
Estas tabelas armazenam dados agregados para relatórios e dashboards.
"""
# Em um projeto real, usaríamos modelos do SQLAlchemy.
# Por simplicidade, definiremos o esquema apenas como strings SQL.

# Tabela: estoque_por_medicamento_diario
# Snapshot diário do estoque por medicamento
ESTOQUE_POR_MEDICAMENTO_DIARIO_SQL = """
CREATE TABLE IF NOT EXISTS estoque_por_medicamento_diario (
    id SERIAL PRIMARY KEY,
    medicamento_id INTEGER NOT NULL,
    data DATE NOT NULL,
    estoque_total INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Tabela: movimentacoes_diario
# Movimentações agregadas diariamente
MOVIMENTACOES_DIARIO_SQL = """
CREATE TABLE IF NOT EXISTS movimentacoes_diario (
    id SERIAL PRIMARY KEY,
    medicamento_id INTEGER NOT NULL,
    tipo VARCHAR(10) NOT NULL, -- ENTRADA, SAIDA
    quantidade INTEGER NOT NULL,
    data DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Tabela: alertas_reabastecimento
# Gatilhos históricos de reabastecimento
ALERTAS_REABASTECIMENTO_SQL = """
CREATE TABLE IF NOT EXISTS alertas_reabastecimento (
    id SERIAL PRIMARY KEY,
    medicamento_id INTEGER NOT NULL,
    quantidade_solicitada INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processado BOOLEAN DEFAULT FALSE
);
"""

# Função para criar todas as tabelas
def create_all_tables():
    return [ESTOQUE_POR_MEDICAMENTO_DIARIO_SQL, MOVIMENTACOES_DIARIO_SQL, ALERTAS_REABASTECIMENTO_SQL]