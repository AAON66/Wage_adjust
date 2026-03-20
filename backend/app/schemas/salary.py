from __future__ import annotations

from datetime import datetime
from decimal import Decimal

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
    explanation: str | None = None


class SalaryRecommendRequest(BaseModel):
    evaluation_id: str


class SalaryRecommendationUpdateRequest(BaseModel):
    final_adjustment_ratio: float = Field(ge=0, le=1)
    status: str | None = None


class SalarySimulationRequest(BaseModel):
    cycle_id: str
    department: str | None = None
    job_family: str | None = None
    budget_amount: Decimal | None = None


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

