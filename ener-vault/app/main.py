from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import server_router
from app.config.conf import CONFIG

app = FastAPI(
    title=CONFIG.SERVER_API_NAME,
    description=CONFIG.SERVER_API_DESCRIPTION,
    version=CONFIG.SERVER_API_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(server_router)
