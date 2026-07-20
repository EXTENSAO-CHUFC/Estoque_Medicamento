from __future__ import annotations
from datetime import date, datetime, timezone
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from app.models.entities import AlertaReabastecimento, EstoqueSnapshot, LoteAtual, MedicamentoDim, MovimentacaoFato

class AnalyticsService:
    def __init__(self, session: Session):
        self.session = session

    def apply(self, table: str, event: dict) -> int | None:
        op, before, after = event.get("op"), event.get("before"), event.get("after")
        row = after or before
        if not row or op not in {"c", "u", "d", "r"}:
            return None
        if table == "medicamentos":
            self._medicamento(op, row)
            return int(row["id"])
        if table == "lotes":
            medicamento_id = int(row["medicamento_id"])
            self._lote(op, row)
            self._snapshot(medicamento_id)
            return medicamento_id
        if table == "movimentacoes":
            self._movimentacao(op, row)
            lote_id = int(row["lote_id"])
            medicamento_id = self.session.scalar(select(LoteAtual.medicamento_id).where(LoteAtual.id == lote_id))
            return medicamento_id
        return None

    def _medicamento(self, op: str, row: dict) -> None:
        if op == "d":
            self.session.execute(delete(MedicamentoDim).where(MedicamentoDim.id == int(row["id"])))
            return
        stmt = insert(MedicamentoDim).values(
            id=int(row["id"]), nome=row.get("nome") or "Sem nome",
            principio_ativo=row.get("principio_ativo"),
            bloqueio_reabastecimento=bool(row.get("bloqueio_reabastecimento", False)),
        ).on_conflict_do_update(index_elements=[MedicamentoDim.id], set_={
            "nome": row.get("nome") or "Sem nome",
            "principio_ativo": row.get("principio_ativo"),
            "bloqueio_reabastecimento": bool(row.get("bloqueio_reabastecimento", False)),
            "atualizado_em": func.now(),
        })
        self.session.execute(stmt)

    def _lote(self, op: str, row: dict) -> None:
        if op == "d":
            self.session.execute(delete(LoteAtual).where(LoteAtual.id == int(row["id"])))
            return
        stmt = insert(LoteAtual).values(
            id=int(row["id"]), medicamento_id=int(row["medicamento_id"]),
            almoxarifado_id=row.get("almoxarifado_id"), numero_lote=row.get("numero_lote"),
            quantidade=int(row.get("quantidade", 0)), data_validade=row.get("data_validade"),
        ).on_conflict_do_update(index_elements=[LoteAtual.id], set_={
            "medicamento_id": int(row["medicamento_id"]), "almoxarifado_id": row.get("almoxarifado_id"),
            "numero_lote": row.get("numero_lote"), "quantidade": int(row.get("quantidade", 0)),
            "data_validade": row.get("data_validade"), "atualizado_em": func.now(),
        })
        self.session.execute(stmt)

    def _movimentacao(self, op: str, row: dict) -> None:
        if op == "d":
            self.session.execute(delete(MovimentacaoFato).where(MovimentacaoFato.id == int(row["id"])))
            return
        lote_id = int(row["lote_id"])
        medicamento_id = self.session.scalar(select(LoteAtual.medicamento_id).where(LoteAtual.id == lote_id))
        stmt = insert(MovimentacaoFato).values(
            id=int(row["id"]), lote_id=lote_id, medicamento_id=medicamento_id,
            tipo=row.get("tipo") or "", quantidade=int(row.get("quantidade", 0)),
            usuario_id=row.get("usuario_id"), data_movimentacao=row.get("data_movimentacao"),
        ).on_conflict_do_update(index_elements=[MovimentacaoFato.id], set_={
            "lote_id": lote_id, "medicamento_id": medicamento_id, "tipo": row.get("tipo") or "",
            "quantidade": int(row.get("quantidade", 0)), "usuario_id": row.get("usuario_id"),
            "data_movimentacao": row.get("data_movimentacao"),
        })
        self.session.execute(stmt)

    def _snapshot(self, medicamento_id: int) -> None:
        total = int(self.session.scalar(select(func.coalesce(func.sum(LoteAtual.quantidade), 0)).where(LoteAtual.medicamento_id == medicamento_id)) or 0)
        stmt = insert(EstoqueSnapshot).values(medicamento_id=medicamento_id, data=date.today(), estoque_total=total).on_conflict_do_update(
            constraint="uq_snapshot_medicamento_data", set_={"estoque_total": total, "atualizado_em": func.now()}
        )
        self.session.execute(stmt)

    def current_stock(self, medicamento_id: int) -> int:
        return int(self.session.scalar(select(func.coalesce(func.sum(LoteAtual.quantidade), 0)).where(LoteAtual.medicamento_id == medicamento_id)) or 0)

    def replenishment_blocked(self, medicamento_id: int) -> bool:
        return bool(self.session.scalar(select(MedicamentoDim.bloqueio_reabastecimento).where(MedicamentoDim.id == medicamento_id)) or False)

    def save_alert(self, medicamento_id: int, quantity: int, stock: int) -> None:
        self.session.add(AlertaReabastecimento(medicamento_id=medicamento_id, quantidade_solicitada=quantity, estoque_observado=stock))
