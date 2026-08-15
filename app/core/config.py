"""Temporary compatibility import for the Phase 0 configuration move."""

from app.infrastructure.config import Settings, get_settings, settings

__all__ = ["Settings", "get_settings", "settings"]
