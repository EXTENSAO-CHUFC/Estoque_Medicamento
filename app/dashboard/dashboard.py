from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from app.config.settings import settings
from app.services.cache_service import CacheService

st.set_page_config(
    page_title="Estoque CDC em tempo real",
    layout="wide",
)
st.title("Dashboard de Estoque em Tempo Real")
st.caption("Fonte: eventos CDC do PostgreSQL processados via Kafka e armazenados no Redis.")


def medication_name_map(medications: list[dict[str, Any]]) -> dict[int, str]:
    result: dict[int, str] = {}
    for item in medications:
        try:
            identifier = int(item["id"])
        except (KeyError, TypeError, ValueError):
            continue
        result[identifier] = str(item.get("nome") or f"Medicamento {identifier}")
    return result


def build_stock_frame(
    lots: list[dict[str, Any]],
    names: dict[int, str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for lote in lots:
        try:
            med_id = int(lote["medicamento_id"])
            quantity = int(lote.get("quantidade") or 0)
        except (KeyError, TypeError, ValueError):
            continue
        rows.append(
            {
                "medicamento_id": med_id,
                "medicamento": names.get(med_id, f"Medicamento {med_id}"),
                "quantidade": quantity,
            }
        )
    if not rows:
        return pd.DataFrame(columns=["medicamento_id", "medicamento", "estoque_total"])
    return (
        pd.DataFrame(rows)
        .groupby(["medicamento_id", "medicamento"], as_index=False)["quantidade"]
        .sum()
        .rename(columns={"quantidade": "estoque_total"})
        .sort_values("medicamento")
    )


def build_movements_frame(
    movements: list[dict[str, Any]],
    names: dict[int, str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for movement in movements:
        try:
            med_id = int(movement.get("medicamento_id"))
            quantity = int(movement.get("quantidade") or 0)
        except (TypeError, ValueError):
            continue
        raw_date = movement.get("data_movimentacao")
        rows.append(
            {
                "medicamento": names.get(med_id, f"Medicamento {med_id}"),
                "tipo": str(movement.get("tipo") or "DESCONHECIDO"),
                "quantidade": quantity,
                "data_movimentacao": raw_date,
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=["medicamento", "tipo", "quantidade", "data_movimentacao"]
        )
    frame = pd.DataFrame(rows)
    frame["data_movimentacao"] = pd.to_datetime(
        frame["data_movimentacao"],
        errors="coerce",
        utc=True,
    )
    frame["data"] = frame["data_movimentacao"].dt.date
    return frame


def build_alerts_frame(
    alerts: list[dict[str, Any]],
    names: dict[int, str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for alert in alerts:
        med_id = int(alert.get("medicamento_id") or 0)
        created = alert.get("criado_em_epoch")
        rows.append(
            {
                "criado_em": datetime.fromtimestamp(float(created)) if created else None,
                "medicamento": names.get(med_id, f"Medicamento {med_id}"),
                "estoque_observado": alert.get("estoque_observado"),
                "quantidade_solicitada": alert.get("quantidade_solicitada"),
            }
        )
    return pd.DataFrame(rows)


@st.fragment(run_every=f"{settings.dashboard_refresh_seconds}s")
def render_dashboard() -> None:
    try:
        cache = CacheService()
        health = cache.health()
        medications = cache.list_medications()
        lots = cache.list_lots()
        movements = cache.list_movements(limit=200)
        alerts = cache.list_alerts(limit=50)
    except Exception as exc:
        st.error(f"Não foi possível ler o Redis: {exc}")
        return

    names = medication_name_map(medications)
    stock = build_stock_frame(lots, names)
    movement_frame = build_movements_frame(movements, names)
    alerts_frame = build_alerts_frame(alerts, names)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Medicamentos", len(medications))
    c2.metric(
        "Estoque total",
        int(stock["estoque_total"].sum()) if not stock.empty else 0,
    )
    c3.metric("Movimentações", len(movements))
    c4.metric("Eventos processados", health["eventos_processados"])

    st.subheader("Estoque atual")
    if stock.empty:
        st.info("Aguardando eventos de medicamentos e lotes do Debezium.")
    else:
        st.plotly_chart(
            px.bar(
                stock,
                x="medicamento",
                y="estoque_total",
                text="estoque_total",
            ),
            use_container_width=True,
        )
        st.dataframe(stock, use_container_width=True, hide_index=True)

    st.subheader("Movimentações")
    if movement_frame.empty:
        st.info("Ainda não há movimentações processadas.")
    else:
        chart_data = (
            movement_frame.dropna(subset=["data"])
            .groupby(["data", "tipo"], as_index=False)["quantidade"]
            .sum()
        )
        if not chart_data.empty:
            st.plotly_chart(
                px.bar(
                    chart_data,
                    x="data",
                    y="quantidade",
                    color="tipo",
                    barmode="group",
                ),
                use_container_width=True,
            )
        st.dataframe(
            movement_frame[
                ["data_movimentacao", "medicamento", "tipo", "quantidade"]
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Alertas de reabastecimento")
    if alerts_frame.empty:
        st.info("Nenhum alerta emitido.")
    else:
        st.dataframe(alerts_frame, use_container_width=True, hide_index=True)

    st.caption(
        f"Redis: conectado · atualização automática a cada "
        f"{settings.dashboard_refresh_seconds} segundo(s)."
    )


render_dashboard()
