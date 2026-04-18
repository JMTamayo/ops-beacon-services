import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.device_entity_assignment import DeviceEntityAssignment
from app.schemas.device_entity_assignment import (
    DeviceEntityAssignmentCreate,
    DeviceEntityAssignmentUpdate,
)
from app.schemas.list_sort import DeviceEntityAssignmentListSortDate, SortOrder

_ASSIGNMENT_SORT_COLUMNS = {
    DeviceEntityAssignmentListSortDate.created_at: DeviceEntityAssignment.created_at,
    DeviceEntityAssignmentListSortDate.updated_at: DeviceEntityAssignment.updated_at,
    DeviceEntityAssignmentListSortDate.started_at: DeviceEntityAssignment.started_at,
    DeviceEntityAssignmentListSortDate.ended_at: DeviceEntityAssignment.ended_at,
}


def _ilike_fragment(fragment: str) -> str:
    """Wrap ``fragment`` for case-insensitive substring match; escape LIKE metacharacters."""
    esc = (
        fragment.replace("\\", "\\\\")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )
    return f"%{esc}%"


def create_assignment(db: Session, data: DeviceEntityAssignmentCreate) -> DeviceEntityAssignment:
    row = DeviceEntityAssignment(
        device_id=data.device_id,
        entity_id=data.entity_id,
        started_at=data.started_at,
        ended_at=data.ended_at,
        description=data.description,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(row)
    return row


def get_assignment(db: Session, assignment_id: uuid.UUID) -> DeviceEntityAssignment | None:
    return db.get(DeviceEntityAssignment, assignment_id)


def _interval_overlap_conditions(
    *,
    device_id: uuid.UUID | None,
    entity_id: uuid.UUID | None,
    interval_from: datetime | None,
    interval_to: datetime | None,
) -> list:
    conditions: list = []
    if device_id is not None:
        conditions.append(DeviceEntityAssignment.device_id == device_id)
    if entity_id is not None:
        conditions.append(DeviceEntityAssignment.entity_id == entity_id)

    if interval_from is not None and interval_to is not None:
        # Assignment [started_at, ended_at) overlaps closed [interval_from, interval_to].
        conditions.append(DeviceEntityAssignment.started_at <= interval_to)
        conditions.append(
            or_(
                DeviceEntityAssignment.ended_at.is_(None),
                DeviceEntityAssignment.ended_at > interval_from,
            )
        )
    elif interval_from is not None:
        conditions.append(
            or_(
                DeviceEntityAssignment.ended_at.is_(None),
                DeviceEntityAssignment.ended_at > interval_from,
            )
        )
    elif interval_to is not None:
        conditions.append(DeviceEntityAssignment.started_at <= interval_to)
    return conditions


def list_assignments(
    db: Session,
    *,
    offset: int = 0,
    limit: int = 100,
    device_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
    interval_from: datetime | None = None,
    interval_to: datetime | None = None,
    description_like: str | None = None,
    sort_date: DeviceEntityAssignmentListSortDate = DeviceEntityAssignmentListSortDate.started_at,
    sort_order: SortOrder = SortOrder.DESC,
) -> tuple[list[DeviceEntityAssignment], int]:
    conditions = _interval_overlap_conditions(
        device_id=device_id,
        entity_id=entity_id,
        interval_from=interval_from,
        interval_to=interval_to,
    )
    if description_like is not None and description_like.strip():
        conditions.append(
            DeviceEntityAssignment.description.ilike(
                _ilike_fragment(description_like.strip()),
                escape="\\",
            )
        )
    stmt = select(DeviceEntityAssignment)
    count_stmt = select(func.count()).select_from(DeviceEntityAssignment)
    if conditions:
        stmt = stmt.where(*conditions)
        count_stmt = count_stmt.where(*conditions)

    total = int(db.scalar(count_stmt) or 0)
    col = _ASSIGNMENT_SORT_COLUMNS[sort_date]
    order_clause = col.desc() if sort_order == SortOrder.DESC else col.asc()
    stmt = stmt.order_by(order_clause).offset(offset).limit(limit)
    items = list(db.execute(stmt).scalars().all())
    return items, total


def update_assignment(
    db: Session, assignment_id: uuid.UUID, data: DeviceEntityAssignmentUpdate
) -> DeviceEntityAssignment | None:
    row = db.get(DeviceEntityAssignment, assignment_id)
    if row is None:
        return None
    payload = data.model_dump(exclude_unset=True)
    new_started = payload.get("started_at", row.started_at)
    new_ended = payload.get("ended_at", row.ended_at)
    if new_ended is not None and new_ended <= new_started:
        raise ValueError("ended_at must be after started_at for the resulting interval.")

    for key, value in payload.items():
        setattr(row, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(row)
    return row


def delete_assignment(db: Session, assignment_id: uuid.UUID) -> bool:
    row = db.get(DeviceEntityAssignment, assignment_id)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True
