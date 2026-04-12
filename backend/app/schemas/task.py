from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # 'pending' | 'running' | 'completed' | 'failed'
    progress: dict | None = None  # {processed: int, total: int, errors: int}
    result: Any = None  # evaluation dict or import summary dict
    error: str | None = None


class TaskTriggerResponse(BaseModel):
    task_id: str
    status: str  # always 'pending' on trigger
