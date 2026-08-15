from __future__ import annotations

from fastapi.testclient import TestClient

from app.infrastructure.config import Settings
from app.main import create_app


def _offline_settings(tmp_path, **overrides) -> Settings:
    values = {
        "_env_file": None,
        "app_environment": "test",
        "data_dir": tmp_path / "data",
        "sample_dir": tmp_path / "sample_corpus",
        "embedding_provider": "hashing",
        "embedding_model": "hashing",
        "embedding_dimensions": (384,),
        "generation_provider": "template",
        "vector_store_backend": "local",
        "persistence_backend": "jsonl",
        "auth_mode": "demo",
        "admin_api_key": "test-admin",
        "demo_bootstrap_sample_corpus": False,
    }
    values.update(overrides)
    return Settings(**values)


def test_factory_owns_services_and_public_probes_do_not_touch_dependencies(tmp_path):
    app = create_app(_offline_settings(tmp_path))

    with TestClient(app) as client:
        assert app.state.services.vector_store is not None
        assert client.get("/health/live").json() == {"status": "ok"}
        assert client.get("/api/health/live").json() == {"status": "ok"}
        assert client.get("/health/ready").json()["status"] == "ok"
        response = client.get("/")
        assert response.status_code == 200
        assert "Continue as Demo User" in response.text


def test_demo_session_exposes_the_seeded_workspace(tmp_path):
    app = create_app(
        _offline_settings(
            tmp_path,
            persistence_backend="database",
            database_url=f"sqlite:///{tmp_path / 'grounddesk.db'}",
            database_auto_create=True,
        )
    )

    with TestClient(app) as client:
        session = client.post("/api/auth/demo-session")
        profile = client.get(
            "/api/me",
            headers={"Authorization": f"Bearer {session.json()['access_token']}"},
        )
        assert app.state.services.database_runtime.engine.pool.checkedout() == 0

    assert session.status_code == 200
    assert profile.json()["user"]["display_name"] == "Demo User"
    assert profile.json()["workspaces"] == [{"id": "demo", "name": "Demo Workspace"}]


def test_empty_workspace_chat_explains_that_documents_must_be_uploaded(tmp_path):
    app = create_app(_offline_settings(tmp_path))

    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            headers={"Authorization": "Bearer grounddesk-demo-session"},
            json={"question": "What document have I uploaded?"},
        )

    assert response.status_code == 200
    assert response.json()["evidence_status"] == "no_documents"
    assert response.json()["needs_escalation"] is False
    assert response.json()["citations"] == []
    assert "no documents have been uploaded" in response.json()["answer"].lower()


def test_uploaded_document_can_be_previewed_from_the_product_interface(tmp_path):
    app = create_app(_offline_settings(tmp_path))

    with TestClient(app) as client:
        upload = client.post(
            "/api/documents",
            headers={
                "Authorization": "Bearer grounddesk-demo-session",
                "X-Workspace-ID": "demo",
            },
            files={
                "file": (
                    "getting-started.txt",
                    b"GroundDesk uploads documents at runtime for retrieval.",
                    "text/plain",
                )
            },
        )
        document_id = upload.json()["document_id"]
        preview = client.get(
            f"/api/documents/{document_id}/preview",
            headers={
                "Authorization": "Bearer grounddesk-demo-session",
                "X-Workspace-ID": "demo",
            },
        )

    assert upload.status_code == 200
    assert preview.status_code == 200
    assert (
        preview.json()["text"]
        == "GroundDesk uploads documents at runtime for retrieval."
    )


def test_onboarding_creates_a_workspace_for_authenticated_user(tmp_path):
    user_id = "11111111-1111-1111-1111-111111111111"

    class FakeVerifier:
        def verify(self, token: str):
            assert token == "valid-token"
            from app.core.auth import AuthenticatedUser

            return AuthenticatedUser(
                user_id=user_id,
                email="owner@example.test",
                display_name="Workspace Owner",
            )

    app = create_app(
        _offline_settings(
            tmp_path,
            auth_mode="supabase",
            persistence_backend="database",
            database_url=f"sqlite:///{tmp_path / 'grounddesk.db'}",
            database_auto_create=True,
            supabase_url="https://example.supabase.co",
            supabase_publishable_key="publishable-key",
        )
    )

    with TestClient(app) as client:
        app.state.services.access_controller.verifier = FakeVerifier()
        headers = {"Authorization": "Bearer valid-token"}
        created = client.post(
            "/api/onboarding",
            headers=headers,
            json={
                "organization_name": "Acme Support",
                "workspace_name": "Customer Success",
            },
        )
        second = client.post(
            "/api/onboarding",
            headers=headers,
            json={
                "organization_name": "Globex",
                "workspace_name": "Technical Support",
            },
        )
        profile = client.get("/api/me", headers=headers)

    assert created.status_code == 200
    assert created.json()["workspace"] == {
        "id": created.json()["workspace"]["id"],
        "name": "Customer Success",
    }
    assert second.status_code == 200
    assert profile.json()["workspaces"] == [
        created.json()["workspace"],
        second.json()["workspace"],
    ]


def test_dependency_diagnostics_are_private_and_redact_failures(tmp_path):
    app = create_app(_offline_settings(tmp_path))

    class BrokenStore:
        def count_chunks(self):
            raise RuntimeError("database password must never be returned")

    with TestClient(app) as client:
        app.state.services.vector_store = BrokenStore()

        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 200
        response = client.get(
            "/internal/health/dependencies",
            headers={"X-Admin-API-Key": "test-admin"},
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "Dependencies are unavailable."}


def test_production_app_serves_product_interface_without_legacy_demo_route():
    settings = Settings(
        _env_file=None,
        app_environment="production",
        auth_mode="supabase",
        persistence_backend="database",
        database_url="postgresql+psycopg://grounddesk:password@db.example/grounddesk",
        supabase_url="https://grounddesk.supabase.co",
        supabase_publishable_key="publishable-key",
        vector_store_backend="qdrant",
        qdrant_url="https://qdrant.example",
        admin_api_key=None,
    )

    with TestClient(create_app(settings)) as client:
        product = client.get("/")
        assert product.status_code == 200
        assert 'id="newWorkspaceButton"' in product.text
        assert client.get("/app").status_code == 404
