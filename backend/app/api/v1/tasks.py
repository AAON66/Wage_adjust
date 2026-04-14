from __future__ import annotations

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.celery_app import celery_app
from backend.app.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.schemas.task import TaskStatusResponse

router = APIRouter(prefix='/tasks', tags=['tasks'])


@router.get('/{task_id}', response_model=TaskStatusResponse)
def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> TaskStatusResponse:
    result = AsyncResult(task_id, app=celery_app)
    state = result.state

    # T-22-01: Verify task ownership (user_id in meta must match current_user)
    if state not in {'PENDING', 'FAILURE'} and current_user.role != 'admin':
        info = result.info
        if isinstance(info, dict):
            task_user_id = info.get('user_id')
            if task_user_id and task_user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='You do not have permission to view this task.',
                )

    if state == 'PENDING':
        return TaskStatusResponse(task_id=task_id, status='pending')

    if state == 'STARTED':
        return TaskStatusResponse(task_id=task_id, status='running')

    if state == 'PROGRESS':
        info = result.info if isinstance(result.info, dict) else {}
        progress = {
            k: v for k, v in info.items()
            if k in ('processed', 'total', 'errors')
        }
        return TaskStatusResponse(
            task_id=task_id,
            status='running',
            progress=progress or None,
        )

    if state == 'SUCCESS':
        payload = result.result if isinstance(result.result, dict) else {}
        return TaskStatusResponse(
            task_id=task_id,
            status=payload.get('status', 'completed'),
            result=payload.get('result'),
            error=payload.get('error'),
        )

    if state == 'FAILURE':
        return TaskStatusResponse(
            task_id=task_id,
            status='failed',
            error=str(result.result) if result.result else 'Unknown error',
        )

    # Other states (RETRY, REVOKED, etc.)
    return TaskStatusResponse(task_id=task_id, status=state.lower())
