"""Framework-independent tenancy and authorization rules."""

from .permissions import Permission, WorkspaceRole, has_permission
from .tenancy import ActiveMembership, TenantScope

__all__ = [
    "ActiveMembership",
    "Permission",
    "TenantScope",
    "WorkspaceRole",
    "has_permission",
]
