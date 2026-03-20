from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CycleBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    review_period: str = Field(min_length=1, max_length=128)
    budget_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    status: str = Field(default="draft", min_length=1, max_length=32)


class CycleCreate(CycleBase):
    pass


class CycleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    review_period: str | None = Field(default=None, min_length=1, max_length=128)
    budget_amount: Decimal | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, min_length=1, max_length=32)


class CycleRead(CycleBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class CycleListResponse(BaseModel):
    items: list[CycleRead]
    total: int
