from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class MedicamentoDim(Base):
    __tablename__ = "medicamentos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    principio_ativo: Mapped[str | None] = mapped_column(String(200))
    bloqueio_reabastecimento: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

class LoteAtual(Base):
    __tablename__ = "lotes_atuais"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    medicamento_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    almoxarifado_id: Mapped[int | None] = mapped_column(Integer, index=True)
    numero_lote: Mapped[str | None] = mapped_column(String(100))
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_validade: Mapped[date | None] = mapped_column(Date)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

class MovimentacaoFato(Base):
    __tablename__ = "movimentacoes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lote_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    medicamento_id: Mapped[int | None] = mapped_column(Integer, index=True)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    usuario_id: Mapped[int | None] = mapped_column(Integer)
    data_movimentacao: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    recebido_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class EstoqueSnapshot(Base):
    __tablename__ = "estoque_snapshots"
    __table_args__ = (UniqueConstraint("medicamento_id", "data", name="uq_snapshot_medicamento_data"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    medicamento_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    data: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    estoque_total: Mapped[int] = mapped_column(Integer, nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

class AlertaReabastecimento(Base):
    __tablename__ = "alertas_reabastecimento"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    medicamento_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    quantidade_solicitada: Mapped[int] = mapped_column(Integer, nullable=False)
    estoque_observado: Mapped[int] = mapped_column(Integer, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    processado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
