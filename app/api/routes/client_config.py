from fastapi import APIRouter, Depends

from app.api.dependencies import get_app_settings
from app.infrastructure.config import Settings

router = APIRouter(tags=["client-config"])


@router.get("/client-config")
def client_config(settings: Settings = Depends(get_app_settings)):
    """Return only browser-safe configuration required by the product UI."""
    authenticated = settings.auth_mode.lower() == "supabase"
    return {
        "auth_mode": settings.auth_mode.lower(),
        "registration_enabled": authenticated,
        "default_workspace_id": settings.default_workspace_id,
        "supabase_url": settings.supabase_url_value if authenticated else None,
        "supabase_publishable_key": (
            settings.supabase_publishable_key if authenticated else None
        ),
        "demo_user": (
            {
                "display_name": settings.demo_user_name,
                "email": settings.demo_user_email,
            }
            if not authenticated
            else None
        ),
    }
