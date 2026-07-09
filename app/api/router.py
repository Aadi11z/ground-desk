from fastapi import FastAPI, APIRouter
from app.core.config import settings
from app.api.routes import analytics, benchmark, chat, client_config, demo, documents, evals, feedback, health, history, workflows, workspaces
from fastapi.staticfiles import StaticFiles

app = FastAPI(title=settings.app_name, version="0.2.0")

router = APIRouter()

router.include_router(analytics.router)
router.include_router(benchmark.router)
router.include_router(chat.router)
router.include_router(client_config.router)
router.include_router(demo.router)
router.include_router(documents.router)
router.include_router(evals.router)
router.include_router(feedback.router)
router.include_router(health.router)
router.include_router(history.router)
router.include_router(workflows.router)
router.include_router(workspaces.router)

app.include_router(router)