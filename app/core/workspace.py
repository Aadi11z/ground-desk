"""Workspace scoping helpers.

The current product uses a lightweight workspace header as a production seam.
This is not a replacement for full user authentication, but it prevents the RAG
path from accidentally retrieving documents across tenant boundaries once auth is
added in front of the API.
"""

from __future__ import annotations

import re

from .models import ChatRequest, RetrievalFilters


_WORKSPACE_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


def normalize_workspace_id(value: str | None, *, default: str) -> str:
    workspace_id = (value or default).strip()
    if not _WORKSPACE_PATTERN.fullmatch(workspace_id):
        raise ValueError(
            "Workspace IDs must be 1-64 characters and contain only letters, numbers, underscores, or hyphens."
        )
    return workspace_id


def apply_workspace_filter(request: ChatRequest, workspace_id: str) -> ChatRequest:
    filters = request.filters or RetrievalFilters()
    metadata = dict(filters.metadata)
    metadata["workspace_id"] = workspace_id
    scoped_filters = filters.model_copy(update={"metadata": metadata})
    return request.model_copy(update={"filters": scoped_filters})


def metadata_matches_workspace(
    metadata: dict[str, str], workspace_id: str, *, default: str
) -> bool:
    return (metadata.get("workspace_id") or default) == workspace_id
