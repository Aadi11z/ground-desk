from fastapi import APIRouter

from app.api.routes import (
    analytics,
    benchmark,
    chat,
    client_config,
    documents,
    evals,
    feedback,
    health,
    history,
    workflows,
    workspaces,
)

router = APIRouter(prefix="/api")

router.include_router(analytics.router)
router.include_router(benchmark.router)
router.include_router(chat.router)
router.include_router(client_config.router)
router.include_router(documents.router)
router.include_router(evals.router)
router.include_router(feedback.router)
router.include_router(health.router)
router.include_router(history.router)
router.include_router(workflows.router)
router.include_router(workspaces.router)
