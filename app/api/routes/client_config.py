from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_app_settings
from app.infrastructure.config import Settings

router = APIRouter(tags=["client-config"])


@router.get("/client-config")
def client_config(settings: Settings = Depends(get_app_settings)):
    """Return only browser-safe configuration required by the product UI."""
    if not settings.supabase_url_value or not settings.supabase_publishable_key:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")
    return {
        "supabase_url": settings.supabase_url_value,
        "supabase_publishable_key": settings.supabase_publishable_key,
    }
