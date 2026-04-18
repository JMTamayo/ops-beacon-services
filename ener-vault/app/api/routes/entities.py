import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pygination.errors import PaginationError
from pygination.pygination import Page
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.integrity import integrity_error_detail
from app.api.pagination_query import ListPage, ListSizeEntities
from app.db.session import get_db
from app.domain import entities as entities_service
from app.schemas.entity import EntityCreate, EntityRead, EntityUpdate
from app.schemas.list_sort import EntityListSortDate, SortOrder
from app.schemas.pagination import EntityPage

entities_router = APIRouter(prefix="/v1/entities", tags=["entities"])


@entities_router.post("", response_model=EntityRead, status_code=status.HTTP_201_CREATED)
def create_entity(payload: EntityCreate, db: Session = Depends(get_db)) -> EntityRead:
    try:
        row = entities_service.create_entity(db, payload)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=integrity_error_detail(exc),
        ) from None
    return EntityRead.model_validate(row)


@entities_router.get("", response_model=EntityPage)
def list_entities(
    page: ListPage = 0,
    size: ListSizeEntities = 100,
    sort_date: EntityListSortDate = Query(
        default=EntityListSortDate.created_at,
        description="Date/time column to sort by.",
    ),
    sort_order: SortOrder = Query(
        default=SortOrder.DESC,
        description="Sort direction for ``sort_date`` (ascending or descending).",
    ),
    db: Session = Depends(get_db),
) -> EntityPage:
    offset = page * size
    rows, total = entities_service.list_entities(
        db,
        offset=offset,
        limit=size,
        sort_date=sort_date,
        sort_order=sort_order,
    )
    pages = math.ceil(total / size) if size else 0
    if page > 0 and (pages == 0 or page > pages - 1):
        return EntityPage(
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
    return EntityPage(
        items=[EntityRead.model_validate(i) for i in p.items],
        page=p.page,
        size=p.size,
        total=p.total,
        pages=p.pages,
        next_page=p.next_page,
        previous_page=p.previous_page,
    )


@entities_router.get("/{entity_id}", response_model=EntityRead)
def get_entity(entity_id: uuid.UUID, db: Session = Depends(get_db)) -> EntityRead:
    row = entities_service.get_entity(db, entity_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    return EntityRead.model_validate(row)


@entities_router.patch("/{entity_id}", response_model=EntityRead)
def update_entity(
    entity_id: uuid.UUID,
    payload: EntityUpdate,
    db: Session = Depends(get_db),
) -> EntityRead:
    try:
        row = entities_service.update_entity(db, entity_id, payload)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=integrity_error_detail(exc),
        ) from None
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    return EntityRead.model_validate(row)


@entities_router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entity(entity_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    try:
        ok = entities_service.delete_entity(db, entity_id)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=integrity_error_detail(exc),
        ) from None
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
