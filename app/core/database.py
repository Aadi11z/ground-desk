"""Database values shared without depending on SQLAlchemy infrastructure."""


def normalize_database_url(database_url: str) -> str:
    """Route common PostgreSQL URLs through the installed psycopg v3 driver."""
    for prefix in ("postgresql+psycopg2://", "postgresql://", "postgres://"):
        if database_url.startswith(prefix):
            return "postgresql+psycopg://" + database_url[len(prefix) :]
    return database_url
