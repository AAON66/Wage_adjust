from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description='Key 名称')
    rate_limit: int = Field(1000, ge=1, le=100000, description='每小时请求上限')
    expires_at: datetime | None = Field(None, description='可选过期时间')


class ApiKeyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    key_prefix: str
    is_active: bool
    rate_limit: int
    expires_at: datetime | None
    last_used_at: datetime | None
    last_used_ip: str | None
    created_at: datetime
    updated_at: datetime
    created_by: str


class ApiKeyCreateResponse(BaseModel):
    """创建后一次性返回明文 Key，后续不可再查看（per D-02, D-12）"""
    key: ApiKeyRead
    plain_key: str = Field(..., description='完整 API Key 明文（仅此一次展示）')


class ApiKeyRotateResponse(BaseModel):
    """轮换后返回新 Key 明文"""
    key: ApiKeyRead
    plain_key: str
    old_key_id: str
