"""
Dashboard Streamlit para monitoramento de estoque e alertas.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
from config import settings

# Configuração da página
st.set_page_config(page_title="Estoque Analytics Dashboard", layout="wide")

# Conexão com o banco de dados
def get_engine():
    connection_string = f"postgresql://{settings.PG_ANALYTICS_USER}:{settings.PG_ANALYTICS_PASSWORD}@{settings.PG_ANALYTICS_HOST}:{settings.PG_ANALYTICS_PORT}/{settings.PG_ANALYTICS_DATABASE}"
    return create_engine(connection_string)

@st.cache_data(ttl=60)  # cache de 1 minuto
def load_estoque_data():
    """Carrega os níveis diários de estoque."""
    engine = get_engine()
    query = """
        SELECT m.nome AS medicamento, e.data, e.estoque_total
        FROM estoque_por_medicamento_diario e
        JOIN medicamentos m ON e.medicamento_id = m.id
        ORDER BY m.nome, e.data;
    """
    return pd.read_sql(query, engine)

@st.cache_data(ttl=60)
def load_movimentacoes_data():
    """Carrega as movimentações diárias."""
    engine = get_engine()
    query = """
        SELECT m.nome AS medicamento, t.tipo, SUM(t.quantidade) AS quantidade, t.data
        FROM movimentacoes_diario t
        JOIN medicamentos m ON t.medicamento_id = m.id
        GROUP BY m.nome, t.tipo, t.data
        ORDER BY m.nome, t.data;
    """
    return pd.read_sql(query, engine)

@st.cache_data(ttl=60)
def load_alerts_data():
    """Carrega os alertas recentes."""
    engine = get_engine()
    query = """
        SELECT a.id, m.nome AS medicamento, a.quantidade_solicitada, a.timestamp, a.processado
        FROM alertas_reabastecimento a
        JOIN medicamentos m ON a.medicamento_id = m.id
        ORDER BY a.timestamp DESC
        LIMIT 50;
    """
    return pd.read_sql(query, engine)

def main():
    st.title("📊 Dashboard do Estoque de Medicamentos")
    
    # Abas
    tab1, tab2, tab3 = st.tabs(["Estoque", "Movimentações", "Alertas"])
    
    with tab1:
        st.header("Níveis de Estoque")
        df_estoque = load_estoque_data()
        if not df_estoque.empty:
            fig = px.line(
                df_estoque, 
                x='data', 
                y='estoque_total', 
                color='medicamento',
                title='Estoque por Medicamento ao Longo do Tempo'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado de estoque disponível.")
    
    with tab2:
        st.header("Movimentações Diárias")
        df_mov = load_movimentacoes_data()
        if not df_mov.empty:
            fig = px.bar(
                df_mov, 
                x='data', 
                y='quantidade', 
                color='tipo',
                facet_col='medicamento',
                title='Movimentações por Tipo e Medicamento'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado de movimentação disponível.")
    
    with tab3:
        st.header("Alertas de Reabastecimento")
        df_alerts = load_alerts_data()
        if not df_alerts.empty:
            st.dataframe(df_alerts)
            
            # Botão para marcar como processado (para demonstração)
            if st.button("Marcar todos como processados"):
                # Em um aplicativo real, atualizaríamos o banco de dados
                st.success("Todos os alertas marcados como processados.")
        else:
            st.info("Nenhum alerta no momento.")
    
    # Atualização automática
    st.markdown("---")
    st.caption("Dados atualizados automaticamente a cada minuto.")

if __name__ == "__main__":
    main()