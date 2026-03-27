from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from backend.app.models.audit_log import AuditLog


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def query(
        self,
        *,
        target_type: str | None = None,
        target_id: str | None = None,
        operator_id: str | None = None,
        action: str | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        filters = []
        if target_type is not None:
            filters.append(AuditLog.target_type == target_type)
        if target_id is not None:
            filters.append(AuditLog.target_id == target_id)
        if operator_id is not None:
            filters.append(AuditLog.operator_id == operator_id)
        if action is not None:
            filters.append(AuditLog.action == action)
        if from_dt is not None:
            filters.append(AuditLog.created_at >= from_dt)
        if to_dt is not None:
            filters.append(AuditLog.created_at <= to_dt)

        where_clause = and_(*filters) if filters else True

        total = self.db.scalar(
            select(func.count()).select_from(AuditLog).where(where_clause)
        ) or 0

        items = list(
            self.db.scalars(
                select(AuditLog)
                .where(where_clause)
                .order_by(AuditLog.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        )

        return items, total
