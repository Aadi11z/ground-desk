from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.auth import AuthenticatedUser
from app.domain.permissions import WorkspaceRole
from app.infrastructure.config import Settings
from app.main import create_app

USER_ID = "11111111-1111-1111-1111-111111111111"
ACCESS_TOKEN = "valid-token"
WORKSPACE_ID = "acme"


def _settings(tmp_path, **overrides) -> Settings:
    values = {
        "_env_file": None,
        "app_environment": "test",
        "data_dir": tmp_path / "data",
        "corpus_dir": tmp_path / "corpus",
        "embedding_provider": "hashing",
        "embedding_model": "hashing",
        "embedding_dimensions": (384,),
        "generation_provider": "template",
        "vector_store_backend": "local",
        "persistence_backend": "database",
        "database_url": f"sqlite:///{tmp_path / 'grounddesk.db'}",
        "database_auto_create": True,
        "supabase_url": "https://example.supabase.co",
        "supabase_publishable_key": "publishable-key",
        "admin_api_key": "test-admin",
    }
    values.update(overrides)
    return Settings(**values)


class FakeVerifier:
    def verify(self, token: str) -> AuthenticatedUser:
        assert token == ACCESS_TOKEN
        return AuthenticatedUser(
            user_id=USER_ID,
            email="owner@example.test",
            display_name="Workspace Owner",
        )


def _authenticated_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "X-Workspace-ID": WORKSPACE_ID,
    }


def _grant_workspace_access(app) -> None:
    repository = app.state.services.product_repository
    repository.add_workspace_member(WORKSPACE_ID, USER_ID, role=WorkspaceRole.OWNER)
    app.state.services.access_controller.verifier = FakeVerifier()


def test_factory_exposes_health_probes_and_supabase_client_configuration(tmp_path):
    with TestClient(create_app(_settings(tmp_path))) as client:
        assert client.get("/health/live").json() == {"status": "ok"}
        assert client.get("/api/health/live").json() == {"status": "ok"}
        assert client.get("/health/ready").json()["status"] == "ok"
        response = client.get("/api/client-config")

    assert response.json() == {
        "supabase_url": "https://example.supabase.co/",
        "supabase_publishable_key": "publishable-key",
    }


def test_authenticated_user_can_chat_and_preview_an_uploaded_document(tmp_path):
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        _grant_workspace_access(app)
        headers = _authenticated_headers()
        chat = client.post(
            "/api/chat",
            headers=headers,
            json={"question": "What document have I uploaded?"},
        )
        upload = client.post(
            "/api/documents",
            headers=headers,
            files={
                "file": (
                    "getting-started.txt",
                    b"GroundDesk uploads documents at runtime for retrieval.",
                    "text/plain",
                )
            },
        )
        preview = client.get(
            f"/api/documents/{upload.json()['document_id']}/preview",
            headers=headers,
        )

    assert chat.status_code == 200
    assert chat.json()["evidence_status"] == "no_documents"
    assert upload.status_code == 200
    assert (
        preview.json()["text"]
        == "GroundDesk uploads documents at runtime for retrieval."
    )


def test_onboarding_creates_the_first_workspace_for_an_authenticated_user(tmp_path):
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        app.state.services.access_controller.verifier = FakeVerifier()
        response = client.post(
            "/api/onboarding",
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
            json={
                "organization_name": "Acme Support",
                "workspace_name": "Customer Success",
            },
        )
        profile = client.get(
            "/api/me", headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
        )

    assert response.status_code == 200
    assert profile.json()["workspaces"] == [response.json()["workspace"]]


def test_api_has_no_legacy_product_or_demo_session_routes(tmp_path):
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        assert client.post("/api/auth/demo-session").status_code == 404
        assert client.get("/").status_code == 404
        assert client.get("/app").status_code == 404
