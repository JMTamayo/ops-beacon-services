from fastapi import APIRouter

from app.api.routes.agent import agent_router
from app.api.routes.health import health_router

server_router = APIRouter()
server_router.include_router(health_router)
server_router.include_router(agent_router)
