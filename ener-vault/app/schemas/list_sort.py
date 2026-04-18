"""Enums for list endpoints: sort direction and which date column to order by."""

from enum import StrEnum


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class DeviceListSortDate(StrEnum):
    created_at = "created_at"
    updated_at = "updated_at"


class EntityListSortDate(StrEnum):
    created_at = "created_at"
    updated_at = "updated_at"


class MeasurementListSortDate(StrEnum):
    created_at = "created_at"
    updated_at = "updated_at"
    local_time = "local_time"


class DeviceEntityAssignmentListSortDate(StrEnum):
    created_at = "created_at"
    updated_at = "updated_at"
    started_at = "started_at"
    ended_at = "ended_at"
