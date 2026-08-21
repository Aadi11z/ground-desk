from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import update

from app.core.auth import AuthenticatedUser
from app.domain.permissions import WorkspaceRole
from app.infrastructure.config import Settings
from app.main import create_app


def _settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        app_environment="test",
        data_dir=tmp_path / "data",
        corpus_dir=tmp_path / "corpus",
        embedding_provider="hashing",
        embedding_model="hashing",
        embedding_dimensions=(384,),
        generation_provider="template",
        vector_store_backend="local",
        persistence_backend="database",
        database_url=f"sqlite:///{tmp_path / 'grounddesk.sqlite'}",
        database_auto_create=True,
        supabase_url="https://example.supabase.co",
        supabase_publishable_key="publishable-key",
    )


def test_document_permissions_and_cross_workspace_resources_are_hidden(tmp_path):
    user_ids = {
        "owner-token": "11111111-1111-1111-1111-111111111111",
        "viewer-token": "22222222-2222-2222-2222-222222222222",
    }

    class _Verifier:
        def verify(self, token: str) -> AuthenticatedUser:
            return AuthenticatedUser(user_id=user_ids[token])

    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        repository = app.state.services.product_repository
        repository.add_workspace_member(
            "acme", user_ids["owner-token"], role=WorkspaceRole.OWNER
        )
        repository.add_workspace_member(
            "acme", user_ids["viewer-token"], role=WorkspaceRole.VIEWER
        )
        repository.add_workspace_member(
            "globex", user_ids["owner-token"], role=WorkspaceRole.OWNER
        )
        app.state.services.access_controller.verifier = _Verifier()

        owner_acme = {
            "Authorization": "Bearer owner-token",
            "X-Workspace-ID": "acme",
        }
        owner_globex = {
            "Authorization": "Bearer owner-token",
            "X-Workspace-ID": "globex",
        }
        viewer_acme = {
            "Authorization": "Bearer viewer-token",
            "X-Workspace-ID": "acme",
        }
        acme_upload = client.post(
            "/api/documents",
            headers=owner_acme,
            files={"file": ("acme.txt", b"Acme policy", "text/plain")},
        )
        globex_upload = client.post(
            "/api/documents",
            headers=owner_globex,
            files={"file": ("globex.txt", b"Globex policy", "text/plain")},
        )
        assert acme_upload.status_code == 200
        assert globex_upload.status_code == 200

        assert client.get("/api/documents", headers=viewer_acme).status_code == 200
        assert (
            client.post(
                "/api/documents",
                headers=viewer_acme,
                files={"file": ("blocked.txt", b"blocked", "text/plain")},
            ).status_code
            == 403
        )
        assert (
            client.get(
                f"/api/documents/{globex_upload.json()['document_id']}/preview",
                headers=viewer_acme,
            ).status_code
            == 404
        )
        assert (
            client.get(
                "/api/documents",
                headers={
                    "Authorization": "Bearer viewer-token",
                    "X-Workspace-ID": "globex",
                },
            ).status_code
            == 404
        )


def test_disabled_canonical_membership_cannot_fall_back_to_legacy_membership(tmp_path):
    user_id = "11111111-1111-1111-1111-111111111111"

    class _Verifier:
        def verify(self, token: str) -> AuthenticatedUser:
            assert token == "disabled-token"
            return AuthenticatedUser(user_id=user_id)

    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        repository = app.state.services.product_repository
        repository.add_workspace_member(
            "acme", user_id, role=WorkspaceRole.SUPPORT_AGENT
        )
        with repository._operation() as connection:
            connection.execute(
                update(repository.memberships)
                .where(
                    repository.memberships.c.workspace_id == "acme",
                    repository.memberships.c.user_id == user_id,
                )
                .values(status="disabled")
            )
        app.state.services.access_controller.verifier = _Verifier()

        response = client.get(
            "/api/documents",
            headers={
                "Authorization": "Bearer disabled-token",
                "X-Workspace-ID": "acme",
            },
        )

    assert response.status_code == 404
