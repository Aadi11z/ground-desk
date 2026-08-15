"""Offline evaluation helpers use a fixed, isolated tenant scope."""

from app.domain.permissions import WorkspaceRole
from app.domain.tenancy import TenantScope

EVALUATION_SCOPE = TenantScope(
    workspace_id="evaluation",
    user_id="evaluation-runner",
    role=WorkspaceRole.OWNER,
)
