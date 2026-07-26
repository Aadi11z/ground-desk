from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["client-config"])


@router.get("/client-config")
def client_config():
    """Return only browser-safe configuration required by the product UI."""
    authenticated = settings.auth_mode.lower() == "supabase"
    return {
        "auth_mode": settings.auth_mode.lower(),
        "default_workspace_id": settings.default_workspace_id,
        "supabase_url": settings.supabase_url if authenticated else None,
        "supabase_publishable_key": (
            settings.supabase_publishable_key if authenticated else None
        ),
    }
