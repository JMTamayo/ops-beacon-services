from fastapi import APIRouter

from app.api.routes.device_entity_assignments import assignments_router
from app.api.routes.devices import devices_router
from app.api.routes.entities import entities_router
from app.api.routes.health import health_router
from app.api.routes.measurements import measurements_router

server_router = APIRouter()
server_router.include_router(health_router)
server_router.include_router(devices_router)
server_router.include_router(measurements_router)
server_router.include_router(entities_router)
server_router.include_router(assignments_router)
