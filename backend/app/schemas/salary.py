from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SalaryRecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    evaluation_id: str
    current_salary: Decimal
    recommended_ratio: float
    recommended_salary: Decimal
    ai_multiplier: float
    certification_bonus: float
    final_adjustment_ratio: float
    status: str
    created_at: datetime
    explanation: Optional[str] = None


class SalaryRecommendationAdminRead(BaseModel):
    """Full salary figures — visible to admin and hrbp roles only."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    evaluation_id: str
    current_salary: Decimal
    recommended_ratio: float
    recommended_salary: Decimal
    ai_multiplier: float
    certification_bonus: float
    final_adjustment_ratio: float
    status: str
    created_at: datetime
    explanation: Optional[str] = None


class SalaryRecommendationEmployeeRead(BaseModel):
    """Redacted salary view — visible to manager and employee roles.

    Contains adjustment percentage only; absolute salary figures are omitted.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    evaluation_id: str
    final_adjustment_ratio: float
    status: str
    created_at: datetime
    explanation: Optional[str] = None


class SalaryHistoryItemRead(BaseModel):
    recommendation_id: str
    evaluation_id: str
    submission_id: str
    cycle_id: str
    cycle_name: str
    review_period: str
    current_salary: Decimal
    recommended_salary: Decimal
    recommended_ratio: float
    final_adjustment_ratio: float
    adjustment_amount: Decimal
    ai_level: str
    overall_score: float
    status: str
    created_at: datetime


class SalaryHistoryResponse(BaseModel):
    items: list[SalaryHistoryItemRead]
    total: int


class SalaryRecommendRequest(BaseModel):
    evaluation_id: str


class SalaryRecommendationUpdateRequest(BaseModel):
    final_adjustment_ratio: float = Field(ge=0, le=1)
    status: Optional[str] = None


class SalarySimulationRequest(BaseModel):
    cycle_id: str
    department: Optional[str] = None
    job_family: Optional[str] = None
    budget_amount: Optional[Decimal] = None


class SalarySimulationItem(BaseModel):
    employee_id: str
    employee_name: str
    department: str
    job_family: str
    evaluation_id: str
    ai_level: str
    current_salary: Decimal
    recommended_salary: Decimal
    final_adjustment_ratio: float


class SalarySimulationResponse(BaseModel):
    cycle_id: str
    budget_amount: Decimal
    total_recommended_amount: Decimal
    over_budget: bool
    items: list[SalarySimulationItem]


class SalaryLockResponse(BaseModel):
    id: str
    status: str

