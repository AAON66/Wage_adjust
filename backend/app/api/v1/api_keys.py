from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.dependencies import get_db, require_roles
from backend.app.models.user import User
from backend.app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyCreateResponse,
    ApiKeyRead,
    ApiKeyRotateResponse,
)
from backend.app.services.api_key_service import ApiKeyService

router = APIRouter(prefix='/api-keys', tags=['api-key-management'])

_COMMON_RESPONSES = {
    401: {'description': 'Not authenticated', 'content': {'application/json': {'example': {'detail': 'Could not validate credentials.'}}}},
    403: {'description': 'Insufficient permissions', 'content': {'application/json': {'example': {'detail': 'Insufficient permissions.'}}}},
    404: {'description': 'API Key not found', 'content': {'application/json': {'example': {'detail': 'API Key not found.'}}}},
}


@router.post(
    '/',
    response_model=ApiKeyCreateResponse,
    status_code=201,
    responses={
        401: _COMMON_RESPONSES[401],
        403: _COMMON_RESPONSES[403],
    },
    summary='Create API Key',
    description='Create a new API Key. The plain key is returned only once (per D-02, D-12).',
)
def create_api_key(
    body: ApiKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin')),
) -> ApiKeyCreateResponse:
    service = ApiKeyService(db)
    api_key, plain_key = service.create_key(
        name=body.name,
        rate_limit=body.rate_limit,
        expires_at=body.expires_at,
        created_by=current_user.id,
    )
    return ApiKeyCreateResponse(
        key=ApiKeyRead.model_validate(api_key),
        plain_key=plain_key,
    )


@router.get(
    '/',
    response_model=list[ApiKeyRead],
    responses={
        401: _COMMON_RESPONSES[401],
        403: _COMMON_RESPONSES[403],
    },
    summary='List API Keys',
    description='List all API Keys including revoked ones.',
)
def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin')),
) -> list[ApiKeyRead]:
    service = ApiKeyService(db)
    keys = service.list_keys()
    return [ApiKeyRead.model_validate(k) for k in keys]


@router.get(
    '/{key_id}',
    response_model=ApiKeyRead,
    responses={**_COMMON_RESPONSES},
    summary='Get API Key',
)
def get_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin')),
) -> ApiKeyRead:
    service = ApiKeyService(db)
    api_key = service.get_key(key_id)
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='API Key not found.')
    return ApiKeyRead.model_validate(api_key)


@router.post(
    '/{key_id}/rotate',
    response_model=ApiKeyRotateResponse,
    responses={**_COMMON_RESPONSES},
    summary='Rotate API Key',
    description='Revoke old key and generate a new one with the same configuration.',
)
def rotate_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin')),
) -> ApiKeyRotateResponse:
    service = ApiKeyService(db)
    old_key = service.get_key(key_id)
    if old_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='API Key not found.')
    new_key, plain_key = service.rotate_key(key_id, created_by=current_user.id)
    return ApiKeyRotateResponse(
        key=ApiKeyRead.model_validate(new_key),
        plain_key=plain_key,
        old_key_id=key_id,
    )


@router.post(
    '/{key_id}/revoke',
    response_model=ApiKeyRead,
    responses={**_COMMON_RESPONSES},
    summary='Revoke API Key',
    description='Immediately revoke an API Key (per API-04).',
)
def revoke_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin')),
) -> ApiKeyRead:
    service = ApiKeyService(db)
    old_key = service.get_key(key_id)
    if old_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='API Key not found.')
    revoked = service.revoke_key(key_id)
    return ApiKeyRead.model_validate(revoked)
