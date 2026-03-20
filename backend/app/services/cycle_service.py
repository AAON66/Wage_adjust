from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.schemas.cycle import CycleCreate, CycleUpdate


class CycleService:
    def __init__(self, db: Session):
        self.db = db

    def create_cycle(self, payload: CycleCreate) -> EvaluationCycle:
        cycle = EvaluationCycle(**payload.model_dump())
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

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(cycle, field, value)

        self.db.add(cycle)
        self.db.commit()
        self.db.refresh(cycle)
        return cycle

    def update_cycle_status(self, cycle_id: str, status: str) -> EvaluationCycle | None:
        cycle = self.get_cycle(cycle_id)
        if cycle is None:
            return None
        cycle.status = status
        self.db.add(cycle)
        self.db.commit()
        self.db.refresh(cycle)
        return cycle
