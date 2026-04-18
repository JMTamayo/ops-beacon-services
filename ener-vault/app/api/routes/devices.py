import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pygination.errors import PaginationError
from pygination.pygination import Page
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.pagination_query import ListPage, ListSizeDevices
from app.db.session import get_db
from app.domain import devices as devices_service
from app.schemas.device import DeviceCreate, DeviceRead
from app.schemas.list_sort import DeviceListSortDate, SortOrder
from app.schemas.pagination import DevicePage

devices_router = APIRouter(prefix="/v1/devices", tags=["devices"])


@devices_router.post("", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
def create_device(payload: DeviceCreate, db: Session = Depends(get_db)) -> DeviceRead:
    try:
        row = devices_service.create_device(db, payload)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate serial_number or invalid device data.",
        ) from None
    return DeviceRead.model_validate(row)


@devices_router.get("", response_model=DevicePage)
def list_devices(
    page: ListPage = 0,
    size: ListSizeDevices = 100,
    sort_date: DeviceListSortDate = Query(
        default=DeviceListSortDate.created_at,
        description="Date/time column to sort by.",
    ),
    sort_order: SortOrder = Query(
        default=SortOrder.DESC,
        description="Sort direction for ``sort_date`` (ascending or descending).",
    ),
    db: Session = Depends(get_db),
) -> DevicePage:
    offset = page * size
    rows, total = devices_service.list_devices(
        db,
        offset=offset,
        limit=size,
        sort_date=sort_date,
        sort_order=sort_order,
    )
    pages = math.ceil(total / size) if size else 0
    if page > 0 and (pages == 0 or page > pages - 1):
        return DevicePage(
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
    return DevicePage(
        items=[DeviceRead.model_validate(i) for i in p.items],
        page=p.page,
        size=p.size,
        total=p.total,
        pages=p.pages,
        next_page=p.next_page,
        previous_page=p.previous_page,
    )


@devices_router.get("/{device_id}", response_model=DeviceRead)
def get_device(device_id: uuid.UUID, db: Session = Depends(get_db)) -> DeviceRead:
    row = devices_service.get_device(db, device_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return DeviceRead.model_validate(row)
