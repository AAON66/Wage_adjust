from __future__ import annotations

from decimal import Decimal
from typing import Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.schemas.cycle import CycleCreate, CycleUpdate

VALID_CYCLE_STATUSES: Final[set[str]] = {'draft', 'collecting', 'published', 'archived'}
EDITABLE_CYCLE_STATUSES: Final[set[str]] = {'draft', 'collecting', 'published'}


class CycleService:
    def __init__(self, db: Session):
        self.db = db

    def _normalize_status(self, status: str) -> str:
        normalized = status.strip().lower()
        if normalized not in VALID_CYCLE_STATUSES:
            raise ValueError('Invalid cycle status.')
        return normalized

    def _validate_budget(self, budget_amount: Decimal | None) -> None:
        if budget_amount is not None and budget_amount < 0:
            raise ValueError('Budget amount must be greater than or equal to 0.')

    def create_cycle(self, payload: CycleCreate) -> EvaluationCycle:
        status = self._normalize_status(payload.status)
        self._validate_budget(payload.budget_amount)
        cycle = EvaluationCycle(
            name=payload.name,
            review_period=payload.review_period,
            budget_amount=payload.budget_amount,
            status=status,
        )
        self.db.add(cycle)
        self.db.commit()
        self.db.refresh(cycle)
        return cycle

    def get_cycles(self) -> tuple[list[EvaluationCycle], int]:
        query = select(EvaluationCycle).order_by(EvaluationCycle.created_at.desc())
        items = list(self.db.scalars(query))
        total = int(self.db.scalar(select(func.count()).select_from(EvaluationCycle)) or 0)
        return items, total

    def get_cycle(self, cycle_id: str) -> EvaluationCycle | None:
        return self.db.get(EvaluationCycle, cycle_id)

    def update_cycle(self, cycle_id: str, payload: CycleUpdate) -> EvaluationCycle | None:
        cycle = self.get_cycle(cycle_id)
        if cycle is None:
            return None
        if cycle.status == 'archived':
            raise ValueError('Archived cycles cannot be edited.')

        update_data = payload.model_dump(exclude_unset=True)
        if 'status' in update_data and update_data['status'] is not None:
            update_data['status'] = self._normalize_status(update_data['status'])
        if 'budget_amount' in update_data:
            self._validate_budget(update_data['budget_amount'])

        for field, value in update_data.items():
            setattr(cycle, field, value)

        self.db.add(cycle)
        self.db.commit()
        self.db.refresh(cycle)
        return cycle

    def update_cycle_status(self, cycle_id: str, status: str) -> EvaluationCycle | None:
        cycle = self.get_cycle(cycle_id)
        if cycle is None:
            return None

        next_status = self._normalize_status(status)
        if cycle.status == 'archived' and next_status != 'archived':
            raise ValueError('Archived cycles cannot be reactivated.')
        if cycle.status not in EDITABLE_CYCLE_STATUSES and next_status != 'archived':
            raise ValueError('This cycle status cannot be changed.')
        if cycle.status == next_status:
            return cycle

        cycle.status = next_status
        self.db.add(cycle)
        self.db.commit()
        self.db.refresh(cycle)
        return cycle
