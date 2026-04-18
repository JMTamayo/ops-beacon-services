import math
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pygination.errors import PaginationError
from pygination.pygination import Page
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.integrity import integrity_error_detail
from app.api.pagination_query import ListPage, ListSizeDeviceEntityAssignments
from app.db.session import get_db
from app.domain import devices as devices_service
from app.domain import device_entity_assignments as assignments_service
from app.domain import entities as entities_service
from app.schemas.list_sort import DeviceEntityAssignmentListSortDate, SortOrder
from app.schemas.device_entity_assignment import (
    DeviceEntityAssignmentCreate,
    DeviceEntityAssignmentRead,
    DeviceEntityAssignmentUpdate,
)
from app.schemas.pagination import DeviceEntityAssignmentPage

assignments_router = APIRouter(
    prefix="/v1/device-entity-assignments",
    tags=["device-entity-assignments"],
)


@assignments_router.post("", response_model=DeviceEntityAssignmentRead, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: DeviceEntityAssignmentCreate,
    db: Session = Depends(get_db),
) -> DeviceEntityAssignmentRead:
    if devices_service.get_device(db, payload.device_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found; register the device in /v1/devices first.",
        )
    if entities_service.get_entity(db, payload.entity_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found; create or list entities via /v1/entities.",
        )
    try:
        row = assignments_service.create_assignment(db, payload)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=integrity_error_detail(exc),
        ) from None
    return DeviceEntityAssignmentRead.model_validate(row)


@assignments_router.get("", response_model=DeviceEntityAssignmentPage)
def list_assignments(
    page: ListPage = 0,
    size: ListSizeDeviceEntityAssignments = 100,
    device_id: uuid.UUID | None = Query(default=None),
    entity_id: uuid.UUID | None = Query(default=None),
    interval_from: datetime | None = Query(
        default=None,
        description="When set with interval_to, filter assignments whose [started_at, ended_at) "
        "overlaps the closed window [interval_from, interval_to].",
    ),
    interval_to: datetime | None = Query(
        default=None,
        description="Upper bound (inclusive) of the overlap window when paired with interval_from.",
    ),
    description_like: str | None = Query(
        default=None,
        description="Case-insensitive substring filter on ``description`` (SQL ILIKE).",
    ),
    sort_date: DeviceEntityAssignmentListSortDate = Query(
        default=DeviceEntityAssignmentListSortDate.started_at,
        description="Date/time column to sort by.",
    ),
    sort_order: SortOrder = Query(
        default=SortOrder.DESC,
        description="Sort direction for ``sort_date`` (ascending or descending).",
    ),
    db: Session = Depends(get_db),
) -> DeviceEntityAssignmentPage:
    if (
        interval_from is not None
        and interval_to is not None
        and interval_from > interval_to
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="interval_from must be less than or equal to interval_to.",
        )
    offset = page * size
    rows, total = assignments_service.list_assignments(
        db,
        offset=offset,
        limit=size,
        device_id=device_id,
        entity_id=entity_id,
        interval_from=interval_from,
        interval_to=interval_to,
        description_like=description_like,
        sort_date=sort_date,
        sort_order=sort_order,
    )
    pages = math.ceil(total / size) if size else 0
    if page > 0 and (pages == 0 or page > pages - 1):
        return DeviceEntityAssignmentPage(
            items=[],
            page=page,
            size=size,
            total=total,
            pages=pages,
            next_page=None,
            previous_page=page - 1,
        )
    try:
        p = Page(rows, page, size, total)
    except PaginationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return DeviceEntityAssignmentPage(
        items=[DeviceEntityAssignmentRead.model_validate(i) for i in p.items],
        page=p.page,
        size=p.size,
        total=p.total,
        pages=p.pages,
        next_page=p.next_page,
        previous_page=p.previous_page,
    )


@assignments_router.get("/{assignment_id}", response_model=DeviceEntityAssignmentRead)
def get_assignment(assignment_id: uuid.UUID, db: Session = Depends(get_db)) -> DeviceEntityAssignmentRead:
    row = assignments_service.get_assignment(db, assignment_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    return DeviceEntityAssignmentRead.model_validate(row)


@assignments_router.patch("/{assignment_id}", response_model=DeviceEntityAssignmentRead)
def update_assignment(
    assignment_id: uuid.UUID,
    payload: DeviceEntityAssignmentUpdate,
    db: Session = Depends(get_db),
) -> DeviceEntityAssignmentRead:
    if payload.device_id is not None and devices_service.get_device(db, payload.device_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found; register the device in /v1/devices first.",
        )
    if payload.entity_id is not None and entities_service.get_entity(db, payload.entity_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found; create or list entities via /v1/entities.",
        )
    try:
        row = assignments_service.update_assignment(db, assignment_id, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from None
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=integrity_error_detail(exc),
        ) from None
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    return DeviceEntityAssignmentRead.model_validate(row)


@assignments_router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(assignment_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    ok = assignments_service.delete_assignment(db, assignment_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
