from __future__ import annotations

from decimal import Decimal
from typing import Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.cycle_department_budget import CycleDepartmentBudget
from backend.app.models.department import Department
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.submission import EmployeeSubmission
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

    def _normalize_department_budgets(
        self,
        department_budgets: list[dict[str, object]] | None,
        *,
        total_budget: Decimal,
    ) -> list[tuple[Department, Decimal]]:
        if not department_budgets:
            return []

        normalized_ids: list[str] = []
        budget_by_department_id: dict[str, Decimal] = {}
        for item in department_budgets:
            department_id = str(item.get('department_id') or '').strip()
            if not department_id:
                raise ValueError('Department id is required for department budget allocation.')
            if department_id in budget_by_department_id:
                raise ValueError('Department budget allocations cannot contain duplicate departments.')
            amount = Decimal(str(item.get('budget_amount', '0')))
            if amount < 0:
                raise ValueError('Department budget allocation must be greater than or equal to 0.')
            normalized_ids.append(department_id)
            budget_by_department_id[department_id] = amount.quantize(Decimal('0.01'))

        departments = list(
            self.db.scalars(
                select(Department)
                .where(Department.id.in_(normalized_ids))
                .order_by(Department.name.asc())
            )
        )
        if len(departments) != len(normalized_ids):
            raise ValueError('One or more departments were not found.')

        department_by_id = {department.id: department for department in departments}
        allocations = [(department_by_id[department_id], budget_by_department_id[department_id]) for department_id in normalized_ids]
        allocated_total = sum((amount for _, amount in allocations), Decimal('0.00')).quantize(Decimal('0.01'))
        if allocated_total > total_budget:
            raise ValueError('Department budget allocations cannot exceed the total cycle budget.')
        return allocations

    def _replace_department_budgets(
        self,
        cycle: EvaluationCycle,
        allocations: list[tuple[Department, Decimal]],
    ) -> None:
        cycle.department_budgets.clear()
        self.db.flush()

        for department, amount in allocations:
            if amount <= 0:
                continue
            cycle.department_budgets.append(
                CycleDepartmentBudget(
                    department_id=department.id,
                    budget_amount=amount,
                )
            )

    def create_cycle(self, payload: CycleCreate) -> EvaluationCycle:
        status = self._normalize_status(payload.status)
        self._validate_budget(payload.budget_amount)
        allocations = self._normalize_department_budgets(
            [item.model_dump() for item in payload.department_budgets],
            total_budget=payload.budget_amount,
        )
        cycle = EvaluationCycle(
            name=payload.name,
            review_period=payload.review_period,
            budget_amount=payload.budget_amount,
            status=status,
        )
        self.db.add(cycle)
        self.db.flush()
        self._replace_department_budgets(cycle, allocations)
        self.db.commit()
        self.db.refresh(cycle)
        return cycle

    def get_cycles(self) -> tuple[list[EvaluationCycle], int]:
        query = (
            select(EvaluationCycle)
            .options(selectinload(EvaluationCycle.department_budgets).selectinload(CycleDepartmentBudget.department))
            .order_by(EvaluationCycle.created_at.desc())
        )
        items = list(self.db.scalars(query))
        total = int(self.db.scalar(select(func.count()).select_from(EvaluationCycle)) or 0)
        return items, total

    def get_cycle(self, cycle_id: str) -> EvaluationCycle | None:
        query = (
            select(EvaluationCycle)
            .options(selectinload(EvaluationCycle.department_budgets).selectinload(CycleDepartmentBudget.department))
            .where(EvaluationCycle.id == cycle_id)
        )
        return self.db.scalar(query)

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
        next_budget_amount = update_data.get('budget_amount', cycle.budget_amount)
        allocations = None
        if 'department_budgets' in update_data:
            raw_department_budgets = update_data.pop('department_budgets')
            allocations = self._normalize_department_budgets(raw_department_budgets, total_budget=next_budget_amount)
        elif 'budget_amount' in update_data:
            current_allocated_total = sum((item.budget_amount for item in cycle.department_budgets), Decimal('0.00')).quantize(Decimal('0.01'))
            if current_allocated_total > next_budget_amount:
                raise ValueError('Department budget allocations cannot exceed the total cycle budget.')

        for field, value in update_data.items():
            setattr(cycle, field, value)
        if allocations is not None:
            self._replace_department_budgets(cycle, allocations)

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

    def delete_cycle(self, cycle_id: str) -> bool:
        cycle = self.get_cycle(cycle_id)
        if cycle is None:
            return False

        submission_count = int(
            self.db.scalar(
                select(func.count()).select_from(EmployeeSubmission).where(EmployeeSubmission.cycle_id == cycle_id)
            )
            or 0
        )
        if submission_count > 0:
            raise ValueError('This cycle already has employee submissions and cannot be deleted.')

        self.db.delete(cycle)
        self.db.commit()
        return True
