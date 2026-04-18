import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.measurement import Measurement
from app.schemas.measurement import MeasurementCreate, MeasurementUpdate
from app.schemas.list_sort import MeasurementListSortDate, SortOrder

_MEASUREMENT_SORT_COLUMNS = {
    MeasurementListSortDate.created_at: Measurement.created_at,
    MeasurementListSortDate.updated_at: Measurement.updated_at,
    MeasurementListSortDate.local_time: Measurement.local_time,
}


def create_measurement(db: Session, data: MeasurementCreate) -> Measurement:
    row = Measurement(
        device_id=data.device_id,
        local_time=data.local_time,
        voltage=data.voltage,
        current=data.current,
        active_power=data.active_power,
        active_energy=data.active_energy,
        frequency=data.frequency,
        power_factor=data.power_factor,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(row)
    return row


def get_measurement(db: Session, measurement_id: uuid.UUID) -> Measurement | None:
    return db.get(Measurement, measurement_id)


def list_measurements(
    db: Session,
    *,
    offset: int = 0,
    limit: int = 100,
    device_id: uuid.UUID | None = None,
    local_time_from: datetime | None = None,
    local_time_to: datetime | None = None,
    sort_date: MeasurementListSortDate = MeasurementListSortDate.local_time,
    sort_order: SortOrder = SortOrder.DESC,
) -> tuple[list[Measurement], int]:
    """Return a slice ``[offset : offset + limit]`` and the total row count for the filters."""
    conditions = []
    if device_id is not None:
        conditions.append(Measurement.device_id == device_id)
    if local_time_from is not None:
        conditions.append(Measurement.local_time >= local_time_from)
    if local_time_to is not None:
        conditions.append(Measurement.local_time <= local_time_to)

    stmt = select(Measurement)
    count_stmt = select(func.count()).select_from(Measurement)
    if conditions:
        stmt = stmt.where(*conditions)
        count_stmt = count_stmt.where(*conditions)

    total = int(db.scalar(count_stmt) or 0)
    col = _MEASUREMENT_SORT_COLUMNS[sort_date]
    order_clause = col.desc() if sort_order == SortOrder.DESC else col.asc()
    stmt = stmt.order_by(order_clause).offset(offset).limit(limit)
    items = list(db.execute(stmt).scalars().all())
    return items, total


def update_measurement(
    db: Session, measurement_id: uuid.UUID, data: MeasurementUpdate
) -> Measurement | None:
    row = db.get(Measurement, measurement_id)
    if row is None:
        return None
    payload = data.model_dump(exclude_unset=True)
    for key, value in payload.items():
        setattr(row, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(row)
    return row


def delete_measurement(db: Session, measurement_id: uuid.UUID) -> bool:
    row = db.get(Measurement, measurement_id)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True
