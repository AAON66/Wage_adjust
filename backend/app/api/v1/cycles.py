from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.app.dependencies import get_db, get_current_user, require_roles
from backend.app.schemas.cycle import CycleCreate, CycleListResponse, CycleRead, CycleUpdate
from backend.app.services.cycle_service import CycleService

router = APIRouter(prefix="/cycles", tags=["cycles"])


@router.post("", response_model=CycleRead, status_code=status.HTTP_201_CREATED)
def create_cycle(
    payload: CycleCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles("admin", "hrbp")),
) -> CycleRead:
    try:
        cycle = CycleService(db).create_cycle(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return CycleRead.model_validate(cycle)


@router.get("", response_model=CycleListResponse)
def list_cycles(
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> CycleListResponse:
    items, total = CycleService(db).get_cycles()
    return CycleListResponse(items=[CycleRead.model_validate(item) for item in items], total=total)


@router.patch("/{cycle_id}", response_model=CycleRead)
def update_cycle(
    cycle_id: str,
    payload: CycleUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles("admin", "hrbp")),
) -> CycleRead:
    service = CycleService(db)
    try:
        cycle = service.update_cycle(cycle_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if cycle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found.")
    return CycleRead.model_validate(cycle)


@router.post("/{cycle_id}/publish", response_model=CycleRead)
def publish_cycle(
    cycle_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles("admin", "hrbp")),
) -> CycleRead:
    service = CycleService(db)
    try:
        cycle = service.update_cycle_status(cycle_id, "published")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if cycle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found.")
    return CycleRead.model_validate(cycle)


@router.post("/{cycle_id}/archive", response_model=CycleRead)
def archive_cycle(
    cycle_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles("admin", "hrbp")),
) -> CycleRead:
    service = CycleService(db)
    try:
        cycle = service.update_cycle_status(cycle_id, "archived")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if cycle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found.")
    return CycleRead.model_validate(cycle)


@router.delete("/{cycle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cycle(
    cycle_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles("admin", "hrbp")),
) -> Response:
    service = CycleService(db)
    try:
        deleted = service.delete_cycle(cycle_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
