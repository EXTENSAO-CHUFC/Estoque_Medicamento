import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import text
from app.config.database import engine

st.set_page_config(page_title="Estoque Analytics", layout="wide")
st.title("Dashboard de Estoque em Tempo Real")

@st.cache_data(ttl=10)
def query(sql: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)

estoque = query("""
SELECT m.nome AS medicamento, COALESCE(SUM(l.quantidade),0) AS estoque_total
FROM medicamentos m LEFT JOIN lotes_atuais l ON l.medicamento_id=m.id
GROUP BY m.id,m.nome ORDER BY m.nome
""")
mov = query("""
SELECT COALESCE(m.nome, 'Medicamento ' || f.medicamento_id::text) AS medicamento,
       f.tipo, DATE(f.data_movimentacao) AS data, SUM(f.quantidade) AS quantidade
FROM movimentacoes f LEFT JOIN medicamentos m ON m.id=f.medicamento_id
GROUP BY 1,2,3 ORDER BY 3 DESC
""")
alertas = query("""
SELECT a.criado_em, COALESCE(m.nome, a.medicamento_id::text) AS medicamento,
       a.estoque_observado, a.quantidade_solicitada, a.processado
FROM alertas_reabastecimento a LEFT JOIN medicamentos m ON m.id=a.medicamento_id
ORDER BY a.criado_em DESC LIMIT 50
""")

c1,c2,c3=st.columns(3)
c1.metric("Medicamentos", len(estoque))
c2.metric("Estoque total", int(estoque.estoque_total.sum()) if not estoque.empty else 0)
c3.metric("Alertas", len(alertas))

st.subheader("Estoque atual")
if estoque.empty: st.info("Aguardando eventos CDC.")
else: st.plotly_chart(px.bar(estoque,x="medicamento",y="estoque_total"),use_container_width=True)

st.subheader("Movimentações")
if mov.empty: st.info("Ainda não há movimentações processadas.")
else: st.plotly_chart(px.bar(mov,x="data",y="quantidade",color="tipo",facet_col="medicamento"),use_container_width=True)

st.subheader("Alertas de reabastecimento")
st.dataframe(alertas,use_container_width=True)
