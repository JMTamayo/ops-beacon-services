import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.device import Device
from app.schemas.device import DeviceCreate
from app.schemas.list_sort import DeviceListSortDate, SortOrder

_DEVICE_SORT_COLUMNS = {
    DeviceListSortDate.created_at: Device.created_at,
    DeviceListSortDate.updated_at: Device.updated_at,
}


def create_device(db: Session, data: DeviceCreate) -> Device:
    if data.id is not None:
        row = Device(
            id=data.id,
            name=data.name,
            serial_number=data.serial_number,
            is_active=data.is_active,
        )
    else:
        row = Device(
            name=data.name,
            serial_number=data.serial_number,
            is_active=data.is_active,
        )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(row)
    return row


def get_device(db: Session, device_id: uuid.UUID) -> Device | None:
    return db.get(Device, device_id)


def list_devices(
    db: Session,
    *,
    offset: int = 0,
    limit: int = 100,
    sort_date: DeviceListSortDate = DeviceListSortDate.created_at,
    sort_order: SortOrder = SortOrder.DESC,
) -> tuple[list[Device], int]:
    count_stmt = select(func.count()).select_from(Device)
    total = int(db.scalar(count_stmt) or 0)
    col = _DEVICE_SORT_COLUMNS[sort_date]
    order_clause = col.desc() if sort_order == SortOrder.DESC else col.asc()
    stmt = select(Device).order_by(order_clause).offset(offset).limit(limit)
    items = list(db.execute(stmt).scalars().all())
    return items, total
