from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class WebhookEndpointCreate(BaseModel):
    url: str = Field(..., description='Webhook 回调 URL')
    description: Optional[str] = Field(None, max_length=256)
    events: list[str] = Field(default_factory=lambda: ['recommendation.approved'], description='订阅事件类型')


class WebhookEndpointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    url: str
    is_active: bool
    description: Optional[str]
    events: list[str]
    created_by: str
    created_at: datetime
    updated_at: datetime


class WebhookDeliveryLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    webhook_id: str
    event_type: str
    payload: dict
    response_status: Optional[int]
    response_body: Optional[str]
    attempt: int
    success: bool
    error_message: Optional[str]
    created_at: datetime
