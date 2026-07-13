"""
Job periódico para verificar necessidades de reabastecimento e inserir alertas.
Executado de forma independente do processamento CDC para garantir que capturemos quaisquer condições perdidas.
"""
import time
import psycopg2
from datetime import datetime
from ..config import settings

def get_postgres_connection():
    return psycopg2.connect(
        host=settings.PG_ANALYTICS_HOST,
        port=settings.PG_ANALYTICS_PORT,
        user=settings.PG_ANALYTICS_USER,
        password=settings.PG_ANALYTICS_PASSWORD,
        database=settings.PG_ANALYTICS_DATABASE
    )

def check_and_alert():
    """Verifica o estoque atual e insere alertas, se necessário."""
    conn = get_postgres_connection()
    try:
        with conn.cursor() as cur:
            # Obtém o estoque atual por medicamento do snapshot mais recente
            # Usaremos uma consulta simples: assumindo que temos uma tabela com o estoque mais recente
            # Por simplicidade, calcularemos a partir da tabela estoque_por_medicamento_diario (data mais recente)
            cur.execute("""
                WITH latest_estoque AS (
                    SELECT DISTINCT ON (medicamento_id) medicamento_id, estoque_total
                    FROM estoque_por_medicamento_diario
                    ORDER BY medicamento_id, data DESC
                )
                SELECT le.medicamento_id, le.estoque_total
                FROM latest_estoque le
                JOIN medicamentos m ON le.medicamento_id = m.id
                WHERE m.bloqueio_reabastecimento = FALSE
                  AND le.estoque_total <= (SELECT COALESCE(AVG(estoque_total) * 0.1, 10) 
                                           FROM estoque_por_medicamento_diario 
                                           WHERE medicamento_id = le.medicamento_id);
            """)
            rows = cur.fetchall()
            for medicamento_id, estoque_atual in rows:
                # Calcula quanto pedir para atingir, digamos, 50% da média? 
                # Pediremos apenas uma quantidade fixa por simplicidade.
                quantidade_a_pedir = 100  # valor de exemplo
                # Insere o alerta
                cur.execute(
                    """INSERT INTO alertas_reabastecimento (medicamento_id, quantidade_solicitada)
                       VALUES (%s, %s);""",
                    (medicamento_id, quantidade_a_pedir)
                )
                print(f"[{datetime.now()}] Alerta de reposição para medicamento {medicamento_id}: {quantidade_a_pedir} unidades")
            conn.commit()
    except Exception as e:
        print(f"Erro em check_and_alert: {e}")
        conn.rollback()
    finally:
        conn.close()

def run_continuously(interval_seconds=60):
    """Executa a verificação periodicamente."""
    while True:
        try:
            check_and_alert()
        except Exception as e:
            print(f"Erro no loop do job: {e}")
        time.sleep(interval_seconds)

if __name__ == "__main__":
    print("Iniciando job de verificação de alertas...")
    run_continuously()