from fastapi import APIRouter

from app.api.routes import (
    auth,
    chat,
    client_config,
    documents,
    health,
    workspaces,
)

router = APIRouter(prefix="/api")

router.include_router(auth.router)
router.include_router(chat.router)
router.include_router(client_config.router)
router.include_router(documents.router)
router.include_router(health.router)
router.include_router(workspaces.router)
