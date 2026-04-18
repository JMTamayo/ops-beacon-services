import math
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pygination.errors import PaginationError
from pygination.pygination import Page
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.pagination_query import ListPage, ListSizeMeasurements
from app.db.session import get_db
from app.domain import devices as devices_service
from app.domain import measurements as measurements_service
from app.schemas.list_sort import MeasurementListSortDate, SortOrder
from app.schemas.measurement import MeasurementCreate, MeasurementRead, MeasurementUpdate
from app.schemas.pagination import MeasurementPage

measurements_router = APIRouter(prefix="/v1/measurements", tags=["measurements"])


@measurements_router.post("", response_model=MeasurementRead, status_code=status.HTTP_201_CREATED)
def create_measurement(payload: MeasurementCreate, db: Session = Depends(get_db)) -> MeasurementRead:
    device = devices_service.get_device(db, payload.device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found; register the device in /v1/devices first.",
        )
    if not device.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device is not active.",
        )
    try:
        row = measurements_service.create_measurement(db, payload)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A measurement already exists for this device_id and local_time.",
        ) from None
    return MeasurementRead.model_validate(row)


@measurements_router.get("", response_model=MeasurementPage)
def list_measurements(
    page: ListPage = 0,
    size: ListSizeMeasurements = 100,
    device_id: uuid.UUID | None = Query(
        default=None,
        description="Only rows for this energy meter / device (UUID).",
    ),
    local_time_from: datetime | None = Query(
        default=None,
        description="Inclusive lower bound on local_time (measurement instant).",
    ),
    local_time_to: datetime | None = Query(
        default=None,
        description="Inclusive upper bound on local_time (measurement instant).",
    ),
    sort_date: MeasurementListSortDate = Query(
        default=MeasurementListSortDate.local_time,
        description="Date/time column to sort by.",
    ),
    sort_order: SortOrder = Query(
        default=SortOrder.DESC,
        description="Sort direction for ``sort_date`` (ascending or descending).",
    ),
    db: Session = Depends(get_db),
) -> MeasurementPage:
    if (
        local_time_from is not None
        and local_time_to is not None
        and local_time_from > local_time_to
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="local_time_from must be less than or equal to local_time_to.",
        )
    offset = page * size
    rows, total = measurements_service.list_measurements(
        db,
        offset=offset,
        limit=size,
        device_id=device_id,
        local_time_from=local_time_from,
        local_time_to=local_time_to,
        sort_date=sort_date,
        sort_order=sort_order,
    )
    pages = math.ceil(total / size) if size else 0
    if page > 0 and (pages == 0 or page > pages - 1):
        return MeasurementPage(
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
    return MeasurementPage(
        items=[MeasurementRead.model_validate(i) for i in p.items],
        page=p.page,
        size=p.size,
        total=p.total,
        pages=p.pages,
        next_page=p.next_page,
        previous_page=p.previous_page,
    )


@measurements_router.get("/{measurement_id}", response_model=MeasurementRead)
def get_measurement(measurement_id: uuid.UUID, db: Session = Depends(get_db)) -> MeasurementRead:
    row = measurements_service.get_measurement(db, measurement_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Measurement not found")
    return MeasurementRead.model_validate(row)


@measurements_router.patch("/{measurement_id}", response_model=MeasurementRead)
def update_measurement(
    measurement_id: uuid.UUID,
    payload: MeasurementUpdate,
    db: Session = Depends(get_db),
) -> MeasurementRead:
    if payload.device_id is not None:
        device = devices_service.get_device(db, payload.device_id)
        if device is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found; register the device in /v1/devices first.",
            )
        if not device.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Device is not active.",
            )
    try:
        row = measurements_service.update_measurement(db, measurement_id, payload)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Update would duplicate device_id and local_time for another row.",
        ) from None
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Measurement not found")
    return MeasurementRead.model_validate(row)


@measurements_router.delete("/{measurement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_measurement(measurement_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    ok = measurements_service.delete_measurement(db, measurement_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Measurement not found")
