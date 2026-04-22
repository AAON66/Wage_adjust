from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional

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

    Phase 32.1 D-15: data_updated_at = max(updated_at) across 4 data sources
    (employee/performance/salary_adjustment/non_statutory_leave). None if all
    sources missing. Rendered as ISO 8601 by Pydantic.
    """

    overall_status: Literal['eligible', 'ineligible', 'pending']
    rules: List[RuleResultSchema]
    data_updated_at: Optional[datetime] = None  # Phase 32.1 D-15


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
    rules: List[RuleResultSchema]


class EligibilityBatchResponse(BaseModel):
    """Paginated batch eligibility response."""

    items: List[EligibilityBatchItemSchema]
    total: int
    page: int
    page_size: int


class OverrideRequestCreate(BaseModel):
    """Request body for creating an eligibility override."""

    employee_id: str
    override_rules: List[str]
    reason: str
    year: Optional[int] = None
    reference_date: Optional[date] = None


class OverrideRequestRead(BaseModel):
    """Response schema for an eligibility override record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    employee_id: str
    employee_no: Optional[str] = None
    employee_name: Optional[str] = None
    requester_id: str
    requester_name: Optional[str] = None
    override_rules: List[str]
    reason: str
    status: str
    year: int
    reference_date: Optional[date]
    hrbp_approver_id: Optional[str]
    hrbp_decision: Optional[str]
    hrbp_comment: Optional[str]
    hrbp_decided_at: Optional[datetime]
    admin_approver_id: Optional[str]
    admin_decision: Optional[str]
    admin_comment: Optional[str]
    admin_decided_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class OverrideDecisionPayload(BaseModel):
    """Request body for deciding on an override."""

    decision: Literal['approve', 'reject']
    comment: Optional[str] = None


class OverrideListResponse(BaseModel):
    """Paginated list of overrides."""

    items: List[OverrideRequestRead]
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
    amount: Optional[Decimal] = None


class SalaryAdjustmentRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    employee_id: str
    employee_no: str
    adjustment_date: date
    adjustment_type: str
    amount: Optional[Decimal]
    source: str
    created_at: datetime
    updated_at: datetime


class EligibilityCheckRequest(BaseModel):
    reference_date: Optional[date] = None
    year: Optional[int] = None
