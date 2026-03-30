from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from backend.app.dependencies import get_db, require_roles
from backend.app.models.user import User
from backend.app.schemas.webhook import (
    WebhookDeliveryLogRead,
    WebhookEndpointCreate,
    WebhookEndpointRead,
)
from backend.app.services.webhook_service import WebhookService

router = APIRouter(prefix='/webhooks', tags=['webhook-management'])

_COMMON_RESPONSES = {
    401: {'description': 'Not authenticated', 'content': {'application/json': {'example': {'detail': 'Could not validate credentials.'}}}},
    403: {'description': 'Insufficient permissions', 'content': {'application/json': {'example': {'detail': 'Insufficient permissions.'}}}},
    404: {'description': 'Webhook not found', 'content': {'application/json': {'example': {'detail': 'Webhook not found.'}}}},
}


@router.post(
    '/',
    response_model=WebhookEndpointRead,
    status_code=201,
    responses={
        401: _COMMON_RESPONSES[401],
        403: _COMMON_RESPONSES[403],
    },
    summary='Register Webhook',
    description='Register a webhook callback URL. HMAC signing secret is auto-generated.',
)
def register_webhook(
    body: WebhookEndpointCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin')),
) -> WebhookEndpointRead:
    service = WebhookService(db)
    endpoint = service.register(
        url=body.url,
        description=body.description,
        events=body.events,
        created_by=current_user.id,
    )
    return WebhookEndpointRead.model_validate(endpoint)


@router.get(
    '/',
    response_model=list[WebhookEndpointRead],
    responses={
        401: _COMMON_RESPONSES[401],
        403: _COMMON_RESPONSES[403],
    },
    summary='List Webhooks',
)
def list_webhooks(
    active_only: bool = Query(True, description='Only show active webhooks'),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin')),
) -> list[WebhookEndpointRead]:
    service = WebhookService(db)
    endpoints = service.list_endpoints(active_only=active_only)
    return [WebhookEndpointRead.model_validate(ep) for ep in endpoints]


@router.get(
    '/{webhook_id}',
    response_model=WebhookEndpointRead,
    responses={**_COMMON_RESPONSES},
    summary='Get Webhook',
)
def get_webhook(
    webhook_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin')),
) -> WebhookEndpointRead:
    service = WebhookService(db)
    endpoint = service.get_endpoint(webhook_id)
    if endpoint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Webhook not found.')
    return WebhookEndpointRead.model_validate(endpoint)


@router.delete(
    '/{webhook_id}',
    status_code=204,
    response_class=Response,
    responses={
        401: _COMMON_RESPONSES[401],
        403: _COMMON_RESPONSES[403],
        404: _COMMON_RESPONSES[404],
    },
    summary='Unregister Webhook',
    description='Deactivate a webhook endpoint.',
)
def unregister_webhook(
    webhook_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin')),
):
    service = WebhookService(db)
    endpoint = service.get_endpoint(webhook_id)
    if endpoint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Webhook not found.')
    service.unregister(webhook_id)


@router.get(
    '/{webhook_id}/logs',
    response_model=list[WebhookDeliveryLogRead],
    responses={**_COMMON_RESPONSES},
    summary='Get Webhook Delivery Logs',
)
def get_webhook_logs(
    webhook_id: str,
    limit: int = Query(50, ge=1, le=200, description='Number of logs to return'),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin')),
) -> list[WebhookDeliveryLogRead]:
    service = WebhookService(db)
    endpoint = service.get_endpoint(webhook_id)
    if endpoint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Webhook not found.')
    logs = service.get_delivery_logs(webhook_id, limit=limit)
    return [WebhookDeliveryLogRead.model_validate(log) for log in logs]
