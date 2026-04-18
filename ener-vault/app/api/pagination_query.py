"""Shared ``page`` / ``size`` query parameters for list endpoints (pygination).

``page`` matches List Measurements. ``size`` uses the same sentence pattern:
``Number of <resource> per page (matches response ``size``).``
"""

from typing import Annotated

from fastapi import Query

ListPage = Annotated[
    int,
    Query(
        ge=0,
        description="Zero-based page index (matches pygination / response ``page`` field).",
    ),
]

ListSizeMeasurements = Annotated[
    int,
    Query(
        ge=1,
        le=500,
        description="Number of measurements per page (matches response ``size``).",
    ),
]

ListSizeDevices = Annotated[
    int,
    Query(
        ge=1,
        le=500,
        description="Number of devices per page (matches response ``size``).",
    ),
]

ListSizeEntities = Annotated[
    int,
    Query(
        ge=1,
        le=500,
        description="Number of entities per page (matches response ``size``).",
    ),
]

ListSizeDeviceEntityAssignments = Annotated[
    int,
    Query(
        ge=1,
        le=500,
        description=(
            "Number of device-entity assignments per page (matches response ``size``)."
        ),
    ),
]
