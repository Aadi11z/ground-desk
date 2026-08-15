"""Immutable, authorization-derived tenant values."""

from __future__ import annotations

from dataclasses import dataclass

from .permissions import Permission, WorkspaceRole, has_permission


@dataclass(frozen=True)
class ActiveMembership:
    """A durable active workspace membership resolved after authentication."""

    workspace_id: str
    user_id: str
    role: WorkspaceRole


@dataclass(frozen=True)
class TenantScope:
    """Server-derived workspace boundary used for each authorized request."""

    workspace_id: str
    user_id: str
    role: WorkspaceRole

    def allows(self, permission: Permission) -> bool:
        return has_permission(self.role, permission)
