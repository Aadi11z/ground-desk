from __future__ import annotations

import pytest

from app.core.auth import AccessController, AccessError, AuthenticatedUser
from app.domain.permissions import Permission, WorkspaceRole, has_permission
from app.domain.tenancy import ActiveMembership, TenantScope
from app.infrastructure.config import Settings


class _Verifier:
    def verify(self, token: str) -> AuthenticatedUser:
        assert token == "valid-token"
        return AuthenticatedUser(user_id="11111111-1111-1111-1111-111111111111")


class _Repository:
    def __init__(self, membership: ActiveMembership | None):
        self.membership = membership

    def get_active_membership(self, user_id: str, workspace_id: str):
        if self.membership is None:
            return None
        if (self.membership.user_id, self.membership.workspace_id) != (
            user_id,
            workspace_id,
        ):
            return None
        return self.membership


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (WorkspaceRole.OWNER, {permission for permission in Permission}),
        (WorkspaceRole.ADMIN, {permission for permission in Permission}),
        (
            WorkspaceRole.KNOWLEDGE_MANAGER,
            {
                Permission.WORKSPACE_VIEW,
                Permission.DOCUMENTS_READ,
                Permission.DOCUMENTS_WRITE,
            },
        ),
        (
            WorkspaceRole.SUPPORT_AGENT,
            {Permission.WORKSPACE_VIEW, Permission.DOCUMENTS_READ},
        ),
        (
            WorkspaceRole.VIEWER,
            {Permission.WORKSPACE_VIEW, Permission.DOCUMENTS_READ},
        ),
    ],
)
def test_named_roles_have_an_exhaustive_permission_matrix(role, expected):
    assert {
        permission for permission in Permission if has_permission(role, permission)
    } == expected


def test_tenant_scope_is_immutable_and_checks_named_permissions():
    scope = TenantScope(
        workspace_id="acme",
        user_id="11111111-1111-1111-1111-111111111111",
        role=WorkspaceRole.VIEWER,
    )

    assert scope.allows(Permission.DOCUMENTS_READ)
    assert not scope.allows(Permission.DOCUMENTS_WRITE)
    with pytest.raises(AttributeError):
        scope.workspace_id = "globex"  # type: ignore[misc]


def test_access_controller_derives_role_from_active_membership_not_jwt_metadata():
    user_id = "11111111-1111-1111-1111-111111111111"
    settings = Settings(
        _env_file=None,
        auth_mode="supabase",
        persistence_backend="database",
        database_url="sqlite://",
        supabase_url="https://example.supabase.co",
        supabase_publishable_key="publishable-key",
    )
    controller = AccessController(
        settings,
        _Repository(
            ActiveMembership(
                workspace_id="acme", user_id=user_id, role=WorkspaceRole.VIEWER
            )
        ),
        verifier=_Verifier(),
    )

    context = controller.resolve(
        authorization="Bearer valid-token", requested_workspace_id="acme"
    )

    assert context.role is WorkspaceRole.VIEWER
    assert context.allows(Permission.DOCUMENTS_READ)
    assert not context.allows(Permission.DOCUMENTS_WRITE)


def test_inaccessible_workspace_is_not_distinguished_from_a_missing_workspace():
    settings = Settings(
        _env_file=None,
        auth_mode="supabase",
        persistence_backend="database",
        database_url="sqlite://",
        supabase_url="https://example.supabase.co",
        supabase_publishable_key="publishable-key",
    )
    controller = AccessController(settings, _Repository(None), verifier=_Verifier())

    with pytest.raises(AccessError) as exc_info:
        controller.resolve(
            authorization="Bearer valid-token", requested_workspace_id="unknown"
        )

    assert exc_info.value.status_code == 404


def test_demo_inaccessible_workspace_is_opaque_not_forbidden():
    settings = Settings(
        _env_file=None,
        auth_mode="demo",
        default_workspace_id="demo",
    )
    controller = AccessController(settings, _Repository(None))

    with pytest.raises(AccessError) as exc_info:
        controller.resolve(
            authorization="Bearer grounddesk-demo-session",
            requested_workspace_id="another-workspace",
        )

    assert exc_info.value.status_code == 404
