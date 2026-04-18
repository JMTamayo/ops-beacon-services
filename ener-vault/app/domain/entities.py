import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.entity import Entity
from app.schemas.entity import EntityCreate, EntityUpdate
from app.schemas.list_sort import EntityListSortDate, SortOrder

_ENTITY_SORT_COLUMNS = {
    EntityListSortDate.created_at: Entity.created_at,
    EntityListSortDate.updated_at: Entity.updated_at,
}


def create_entity(db: Session, data: EntityCreate) -> Entity:
    row = Entity(name=data.name.strip())
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(row)
    return row


def get_entity(db: Session, entity_id: uuid.UUID) -> Entity | None:
    return db.get(Entity, entity_id)


def list_entities(
    db: Session,
    *,
    offset: int = 0,
    limit: int = 100,
    sort_date: EntityListSortDate = EntityListSortDate.created_at,
    sort_order: SortOrder = SortOrder.DESC,
) -> tuple[list[Entity], int]:
    count_stmt = select(func.count()).select_from(Entity)
    total = int(db.scalar(count_stmt) or 0)
    col = _ENTITY_SORT_COLUMNS[sort_date]
    order_clause = col.desc() if sort_order == SortOrder.DESC else col.asc()
    stmt = select(Entity).order_by(order_clause).offset(offset).limit(limit)
    items = list(db.execute(stmt).scalars().all())
    return items, total


def update_entity(db: Session, entity_id: uuid.UUID, data: EntityUpdate) -> Entity | None:
    row = db.get(Entity, entity_id)
    if row is None:
        return None
    payload = data.model_dump(exclude_unset=True)
    if "name" in payload and payload["name"] is not None:
        row.name = payload["name"].strip()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(row)
    return row


def delete_entity(db: Session, entity_id: uuid.UUID) -> bool:
    row = db.get(Entity, entity_id)
    if row is None:
        return False
    db.delete(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    return True
