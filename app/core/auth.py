"""Supabase-authenticated workspace resolution for GroundDesk."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from jwt import InvalidTokenError, PyJWKClient, decode
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

from app.domain.tenancy import TenantScope

from .workspace import normalize_workspace_id


class AccessError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    email: str | None = None
    display_name: str | None = None


@dataclass(frozen=True)
class AccessContext(TenantScope):
    email: str | None = None

    @property
    def authenticated(self) -> bool:
        return True


class UserVerifier(Protocol):
    def verify(self, token: str) -> AuthenticatedUser: ...


class SupabaseUserVerifier:
    """Validate asymmetric Supabase JWTs against a cached JWKS key set."""

    def __init__(self, supabase_url: str, audience: str):
        self.issuer = f"{supabase_url.rstrip('/')}/auth/v1"
        self.audience = audience
        self.jwks = PyJWKClient(
            f"{self.issuer}/.well-known/jwks.json",
            cache_jwk_set=True,
            lifespan=300,
        )

    def verify(self, token: str) -> AuthenticatedUser:
        try:
            signing_key = self.jwks.get_signing_key_from_jwt(token)
            payload = decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["sub", "exp", "iss", "aud"]},
            )
        except PyJWKClientConnectionError as exc:
            raise AccessError(503, "Authentication provider is unavailable.") from exc
        except (InvalidTokenError, PyJWKClientError) as exc:
            raise AccessError(401, "Missing or invalid access token.") from exc
        user_id = payload.get("id")
        if not user_id:
            user_id = payload.get("sub")
        if not isinstance(user_id, str) or not user_id:
            raise AccessError(401, "Missing or invalid access token.")
        metadata = payload.get("user_metadata")
        display_name = (
            metadata.get("display_name")
            if isinstance(metadata, dict)
            and isinstance(metadata.get("display_name"), str)
            else None
        )
        return AuthenticatedUser(
            user_id=user_id,
            email=payload.get("email")
            if isinstance(payload.get("email"), str)
            else None,
            display_name=display_name,
        )


class AccessController:
    def __init__(self, settings, repository, verifier: UserVerifier | None = None):
        self.settings = settings
        self.repository = repository
        self.verifier = verifier
        if self.verifier is None:
            self.validate_configuration()
            supabase_url = self.settings.supabase_url_value
            self.verifier = SupabaseUserVerifier(
                supabase_url, self.settings.supabase_jwt_audience
            )

    def healthcheck_configuration(self) -> None:
        self.validate_configuration()
        self.repository.auth_healthcheck()

    def validate_configuration(self) -> None:
        """Verify that the application can authorize Supabase users."""
        self.validate_settings(self.settings)

    @staticmethod
    def validate_settings(settings) -> None:
        """Fail before constructing external clients from incomplete settings."""
        if settings.persistence_backend.lower() != "database":
            raise RuntimeError(
                "Supabase authentication requires PERSISTENCE_BACKEND=database."
            )
        if not settings.supabase_url_value or not settings.supabase_publishable_key:
            raise RuntimeError(
                "Supabase authentication requires SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY."
            )

    def authenticate(self, authorization: str | None) -> AuthenticatedUser:
        self.validate_configuration()
        if not authorization or not authorization.startswith("Bearer "):
            raise AccessError(401, "Authorization Bearer token is required.")
        token = authorization.removeprefix("Bearer ").strip()
        if not token or self.verifier is None:
            raise AccessError(401, "Authorization Bearer token is required.")
        return self.verifier.verify(token)

    def resolve(
        self,
        *,
        authorization: str | None,
        requested_workspace_id: str | None,
        require_authenticated: bool = False,
    ) -> AccessContext:
        try:
            workspace_id = normalize_workspace_id(requested_workspace_id, default=None)
        except ValueError as exc:
            raise AccessError(400, str(exc)) from exc

        user = self.authenticate(authorization)
        membership = self.repository.get_active_membership(user.user_id, workspace_id)
        if membership is None:
            # Do not reveal whether the requested workspace exists to non-members.
            raise AccessError(404, "Workspace is not available.")
        return AccessContext(
            workspace_id=workspace_id,
            user_id=user.user_id,
            role=membership.role,
            email=user.email,
        )
