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
    status: Literal['eligible', 'ineligible', 'data_missing', 'overridden']
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


class EligibilityBatchItemSchema(BaseModel):
    """Single employee in a batch eligibility response."""

    model_config = ConfigDict(from_attributes=True)

    employee_id: str
    employee_no: str
    name: str
    department: str
    job_family: str
    job_level: str
    overall_status: str
    rules: list[RuleResultSchema]


class EligibilityBatchResponse(BaseModel):
    """Paginated batch eligibility response."""

    items: list[EligibilityBatchItemSchema]
    total: int
    page: int
    page_size: int


class OverrideRequestCreate(BaseModel):
    """Request body for creating an eligibility override."""

    employee_id: str
    override_rules: list[str]
    reason: str
    year: int | None = None
    reference_date: date | None = None


class OverrideRequestRead(BaseModel):
    """Response schema for an eligibility override record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    employee_id: str
    requester_id: str
    override_rules: list[str]
    reason: str
    status: str
    year: int
    reference_date: date | None
    hrbp_approver_id: str | None
    hrbp_decision: str | None
    hrbp_comment: str | None
    hrbp_decided_at: datetime | None
    admin_approver_id: str | None
    admin_decision: str | None
    admin_comment: str | None
    admin_decided_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OverrideDecisionPayload(BaseModel):
    """Request body for deciding on an override."""

    decision: Literal['approve', 'reject']
    comment: str | None = None


class OverrideListResponse(BaseModel):
    """Paginated list of overrides."""

    items: list[OverrideRequestRead]
    total: int
    page: int
    page_size: int


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
