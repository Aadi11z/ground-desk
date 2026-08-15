"""Named workspace permissions and their deliberately small RBAC matrix."""

from __future__ import annotations

from enum import StrEnum


class Permission(StrEnum):
    """Actions authorized by the application, never by JWT metadata."""

    WORKSPACE_VIEW = "workspace.view"
    DOCUMENTS_READ = "documents.read"
    DOCUMENTS_WRITE = "documents.write"


class WorkspaceRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    KNOWLEDGE_MANAGER = "knowledge_manager"
    SUPPORT_AGENT = "support_agent"
    VIEWER = "viewer"


ROLE_PERMISSIONS: dict[WorkspaceRole, frozenset[Permission]] = {
    WorkspaceRole.OWNER: frozenset(Permission),
    WorkspaceRole.ADMIN: frozenset(Permission),
    WorkspaceRole.KNOWLEDGE_MANAGER: frozenset(
        {
            Permission.WORKSPACE_VIEW,
            Permission.DOCUMENTS_READ,
            Permission.DOCUMENTS_WRITE,
        }
    ),
    WorkspaceRole.SUPPORT_AGENT: frozenset(
        {Permission.WORKSPACE_VIEW, Permission.DOCUMENTS_READ}
    ),
    WorkspaceRole.VIEWER: frozenset(
        {Permission.WORKSPACE_VIEW, Permission.DOCUMENTS_READ}
    ),
}


def has_permission(role: WorkspaceRole, permission: Permission) -> bool:
    """Return whether a known active role authorizes the named action."""
    return permission in ROLE_PERMISSIONS[role]
