"""Interfaz TraceStore + implementación SQLAlchemy async (Fase 1).

El procesamiento es asíncrono: TraceStore métodos son corrutinas
(asyncio + asyncio.Queue, Fase 2).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select, update as sa_update
from tracelens.schemas.label import Label
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from tracelens.schemas.trace import Span, Trace, TraceStatus
from tracelens.storage.models import Base, LabelORM, TraceORM, utcnow


class TraceStore(ABC):
    """Interfaz abstracta de almacenamiento de trazas."""

    @abstractmethod
    async def initialize(self) -> None:
        """Crea las tablas (idempotente)."""

    @abstractmethod
    async def save(self, trace: Trace) -> str:
        """Inserta una traza; devuelve su id."""

    @abstractmethod
    async def get(self, trace_id: str) -> Optional[Trace]:
        """Devuelve una traza por id o None."""

    @abstractmethod
    async def list(
        self,
        *,
        service: Optional[str] = None,
        severity: Optional[list[str]] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Trace]:
        """Lista trazas (nuevas primero) con filtros opcionales."""

    @abstractmethod
    async def count(
        self,
        *,
        service: Optional[str] = None,
        severity: Optional[list[str]] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> int:
        """Cuenta trazas con filtros opcionales."""

    @abstractmethod
    async def update(self, trace_id: str, **fields) -> Optional[Trace]:
        """Actualiza campos de una traza; devuelve la traza o None."""

    @abstractmethod
    async def delete(self, trace_id: str) -> bool:
        """Elimina una traza; True si existía."""

    @abstractmethod
    async def batch_save(self, traces: list) -> list[str]:
        """Inserta varias trazas; devuelve sus ids (Fase 2+)."""

    # -- etiquetas (Fase 3.2) ----------------------------------------------
    @abstractmethod
    async def add_label(self, label) -> None:
        """Guarda una etiqueta."""

    @abstractmethod
    async def get_labels_by_trace(self, trace_id: str) -> list:
        """Etiquetas de una traza."""

    @abstractmethod
    async def get_labels_by_name(self, name: str) -> list:
        """Etiquetas con un nombre (todas)."""

    @abstractmethod
    async def update_label(self, label) -> None:
        """Actualiza una etiqueta."""

    @abstractmethod
    async def delete_label(self, label_id: int) -> bool:
        """Elimina una etiqueta; True si existía."""

    @abstractmethod
    async def list_labels(self) -> list:
        """Todas las etiquetas."""

    @abstractmethod
    async def aclose(self) -> None:
        """Libera recursos (conexión del pool)."""


def _to_trace(row: TraceORM) -> Trace:
    """Convierte una fila TraceORM en el esquema Trace (Fase 1)."""
    return Trace(
        id=row.id,
        timestamp=row.timestamp,
        service=row.service,
        message=row.message,
        severity=TraceStatus(row.severity),
        source=row.source,
        trace_id=row.trace_id,
        labels=list(row.labels or []),
        metadata=dict(row.metadata_ or {}),
        raw=dict(row.raw) if row.raw is not None else None,
        spans=[Span(**s) for s in row.spans or []],
    )


class SQLAlchemyTraceStore(TraceStore):
    """Implementación de TraceStore sobre SQLite (async) / PostgreSQL."""

    def __init__(self, db_url: str, echo: bool = False) -> None:
        self.engine: AsyncEngine = create_async_engine(db_url, echo=echo)
        self._session_factory: async_sessionmaker = async_sessionmaker(
            self.engine, expire_on_commit=False
        )

    async def initialize(self) -> None:
        """Crea las tablas (idempotente)."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def save(self, trace: Trace) -> str:
        """Inserta una traza; devuelve su id."""
        trace_id = trace.id or uuid4().hex
        async with self._session_factory() as session:
            row = TraceORM(
                id=trace_id,
                timestamp=trace.timestamp,
                service=trace.service,
                message=trace.message,
                severity=trace.severity.value,
                source=trace.source,
                trace_id=trace.trace_id,
                labels=list(trace.labels),
                metadata_=dict(trace.metadata),
                raw=trace.raw,
                spans=[s.model_dump(mode="json") for s in trace.spans],
                created_at=utcnow(),
            )
            session.add(row)
            await session.commit()
        return trace_id

    async def get(self, trace_id: str) -> Optional[Trace]:
        """Devuelve una traza por id o None."""
        async with self._session_factory() as session:
            row = await session.get(TraceORM, trace_id)
            return _to_trace(row) if row is not None else None

    def _apply_filters(
        self,
        stmt,
        service: Optional[str],
        severity: Optional[list[str]],
        start: Optional[datetime],
        end: Optional[datetime],
    ):
        if service:
            stmt = stmt.where(TraceORM.service == service)
        if severity:
            stmt = stmt.where(
                TraceORM.severity.in_(
                    [s.value if isinstance(s, TraceStatus) else s for s in severity]
                )
            )
        if start is not None:
            stmt = stmt.where(TraceORM.timestamp >= start)
        if end is not None:
            stmt = stmt.where(TraceORM.timestamp <= end)
        return stmt

    async def list(
        self,
        *,
        service: Optional[str] = None,
        severity: Optional[list[str]] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Trace]:
        """Lista trazas (nuevas primero) con filtros opcionales."""
        stmt = select(TraceORM).order_by(TraceORM.timestamp.desc(), TraceORM.id.desc())
        stmt = self._apply_filters(stmt, service, severity, start, end)
        stmt = stmt.limit(limit).offset(offset)
        async with self._session_factory() as session:
            rows = (await session.execute(stmt)).scalars().all()
            return [_to_trace(r) for r in rows]

    async def count(
        self,
        *,
        service: Optional[str] = None,
        severity: Optional[list[str]] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> int:
        """Cuenta trazas con filtros opcionales."""
        stmt = select(func.count()).select_from(TraceORM)
        stmt = self._apply_filters(stmt, service, severity, start, end)
        async with self._session_factory() as session:
            result = await session.execute(stmt)
            return int(result.scalar_one())

    async def update(self, trace_id: str, **fields) -> Optional[Trace]:
        """Actualiza campos de una traza; devuelve la traza o None."""
        attr_map = {
            "severity": TraceORM.severity,
            "labels": TraceORM.labels,
            "metadata": TraceORM.metadata_,
            "source": TraceORM.source,
            "trace_id": TraceORM.trace_id,
            "message": TraceORM.message,
            "service": TraceORM.service,
            "timestamp": TraceORM.timestamp,
            "spans": TraceORM.spans,
        }
        async with self._session_factory() as session:
            row = await session.get(TraceORM, trace_id)
            if row is not None:
                for key, value in fields.items():
                    attr = attr_map.get(key)
                    if attr is None:
                        continue
                    if key == "spans" and value is not None:
                        value = [s.model_dump(mode="json") for s in value]
                    setattr(row, attr.key, value)
                await session.commit()
        return await self.get(trace_id)

    async def delete(self, trace_id: str) -> bool:
        """Elimina una traza; True si existía."""
        async with self._session_factory() as session:
            result = await session.execute(sa_delete(TraceORM).where(TraceORM.id == trace_id))
            await session.commit()
            return bool(result.rowcount)

    async def batch_save(self, traces: list) -> list[str]:
        """Inserta varias trazas; devuelve sus ids."""
        ids = [t.id or uuid4().hex for t in traces]
        async with self._session_factory() as session:
            for trace, tid in zip(traces, ids):
                session.add(
                    TraceORM(
                        id=tid,
                        timestamp=trace.timestamp,
                        service=trace.service,
                        message=trace.message,
                        severity=trace.severity.value,
                        source=trace.source,
                        trace_id=trace.trace_id,
                        labels=list(trace.labels),
                        metadata_=dict(trace.metadata),
                        raw=trace.raw,
                        spans=[s.model_dump(mode="json") for s in trace.spans],
                        created_at=utcnow(),
                    )
                )
            await session.commit()
        return ids

    # -- etiquetas (Fase 3.2) ----------------------------------------------
    async def add_label(self, label) -> int:
        """Guarda una etiqueta; devuelve su id."""
        async with self._session_factory() as session:
            row = LabelORM(
                trace_id=label.trace_id,
                name=label.name,
                category=label.category,
                source=label.source,
                confidence=label.confidence,
                created_at=utcnow(),
            )
            session.add(row)
            await session.commit()
        return row.id
        # Invalidar la memoria del trazo (Fase 3.2: labels en Trace)
        t = await self.get(label.trace_id)
        if t is not None and label.name not in t.labels:
            await self.update(label.trace_id, labels=t.labels + [label.name])

    async def _labels_query(self, where):
        from tracelens.storage.models import LabelORM
        async with self._session_factory() as session:
            stmt = select(LabelORM).where(where)
            rows = (await session.execute(stmt)).scalars().all()
            return [self._label_to_orm(r) for r in rows]

    def _label_to_orm(self, row):
        from tracelens.storage.models import LabelORM  # noqa: F401
        from tracelens.schemas.label import Label
        return Label(
            id=row.id, trace_id=row.trace_id, name=row.name, category=row.category,
            source=row.source, confidence=row.confidence, created_at=row.created_at,
        )

    async def get_labels_by_trace(self, trace_id: str) -> list:
        return await self._labels_query(LabelORM.trace_id == trace_id)  # type: ignore[name-defined]

    async def get_labels_by_name(self, name: str) -> list:
        return await self._labels_query(LabelORM.name == name)  # type: ignore[name-defined]

    async def update_label(self, label) -> None:
        async with self._session_factory() as session:
            await session.execute(
                sa_update(LabelORM).where(LabelORM.id == label.id).values(
                    name=label.name, category=label.category, source=label.source
                )
            )
            await session.commit()
        # Sincronizar la memoria de la traza (labels) si cambia
        trace = await self.get(label.trace_id)
        if trace is not None and label.name not in trace.labels:
            await self.update(label.trace_id, labels=trace.labels + [label.name])

    async def delete_label(self, label_id: int) -> bool:
        from tracelens.storage.models import LabelORM
        async with self._session_factory() as session:
            result = await session.execute(sa_delete(LabelORM).where(LabelORM.id == label_id))
            await session.commit()
            return bool(result.rowcount)

    async def list_labels(self) -> list:
        from tracelens.storage.models import LabelORM
        async with self._session_factory() as session:
            rows = (await session.execute(select(LabelORM))).scalars().all()
            return [self._label_to_orm(r) for r in rows]

    async def aclose(self) -> None:
        """Libera recursos (conexión del pool)."""
        await self.engine.dispose()
