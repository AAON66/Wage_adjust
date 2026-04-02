from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class RuleResultSchema(BaseModel):
    """Single eligibility rule evaluation result."""

    model_config = ConfigDict(from_attributes=True)

    rule_code: str
    rule_label: str
    status: Literal['eligible', 'ineligible', 'data_missing']
    detail: str


class EligibilityResultSchema(BaseModel):
    """Overall eligibility evaluation result.

    Terminology mapping (ELIG-08/D-10):
    - all eligible -> 'eligible'
    - any ineligible -> 'ineligible'
    - no ineligible but some data_missing -> 'pending'
    """

    overall_status: Literal['eligible', 'ineligible', 'pending']
    rules: list[RuleResultSchema]


class PerformanceRecordCreate(BaseModel):
    employee_no: str
    year: int
    grade: str


class PerformanceRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    employee_id: str
    employee_no: str
    year: int
    grade: str
    source: str
    created_at: datetime
    updated_at: datetime


class SalaryAdjustmentRecordCreate(BaseModel):
    employee_no: str
    adjustment_date: date
    adjustment_type: str
    amount: Decimal | None = None


class SalaryAdjustmentRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    employee_id: str
    employee_no: str
    adjustment_date: date
    adjustment_type: str
    amount: Decimal | None
    source: str
    created_at: datetime
    updated_at: datetime


class EligibilityCheckRequest(BaseModel):
    reference_date: date | None = None
    year: int | None = None
