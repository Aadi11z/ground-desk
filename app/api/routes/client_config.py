
@app.get("/api/client-config")
def client_config():
    """Return only browser-safe configuration required by the product UI."""
    authenticated = settings.auth_mode.lower() == "supabase"
    return {
        "auth_mode": settings.auth_mode.lower(),
        "default_workspace_id": settings.default_workspace_id,
        "supabase_url": settings.supabase_url if authenticated else None,
        # Supabase publishable/anon keys are designed for browser clients;
        # database and provider secrets are never exposed here.
        "supabase_publishable_key": (
            settings.supabase_publishable_key if authenticated else None
        ),
    }
