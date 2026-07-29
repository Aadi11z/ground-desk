"""Authenticated workspace resolution for GroundDesk.

The public portfolio mode is deliberately restricted to one demo workspace.
The B2B mode validates Supabase access tokens server-side and then authorizes
workspace access through durable membership records.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol
from urllib import error, request

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


@dataclass(frozen=True)
class AccessContext:
    workspace_id: str
    role: str
    user_id: str | None = None
    email: str | None = None

    @property
    def authenticated(self) -> bool:
        return self.user_id is not None


class UserVerifier(Protocol):
    def verify(self, token: str) -> AuthenticatedUser: ...


class SupabaseUserVerifier:
    """Validate a Supabase Auth access token through its Auth server.

    This route supports Supabase projects using legacy shared-secret tokens as
    well as newer signing keys. A JWKS verifier can later replace it to reduce
    per-request network cost for projects using asymmetric signing keys.
    """

    def __init__(self, supabase_url: str, publishable_key: str):
        self.supabase_url = supabase_url.rstrip("/")
        self.publishable_key = publishable_key

    def verify(self, token: str) -> AuthenticatedUser:
        auth_request = request.Request(
            f"{self.supabase_url}/auth/v1/user",
            headers={
                "apikey": self.publishable_key,
                "Authorization": f"Bearer {token}",
            },
            method="GET",
        )
        try:
            with request.urlopen(auth_request, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            raise AccessError(401, "Missing or invalid access token.") from exc
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AccessError(503, "Authentication provider is unavailable.") from exc
        user_id = payload.get("id")
        if not user_id:
            raise AccessError(401, "Missing or invalid access token.")
        return AuthenticatedUser(user_id=str(user_id), email=payload.get("email"))


class AccessController:
    def __init__(self, settings, repository, verifier: UserVerifier | None = None):
        self.settings = settings
        self.repository = repository
        self.mode = settings.auth_mode.lower()
        self.verifier = verifier
        if self.mode == "supabase" and self.verifier is None:
            self.verifier = SupabaseUserVerifier(
                settings.supabase_url, settings.supabase_publishable_key
            )

    def healthcheck_configuration(self) -> None:
        self._validate_configuration()
        if self.mode == "supabase":
            self.repository.auth_healthcheck()

    def _validate_configuration(self) -> None:
        if self.mode == "demo":
            return
        if self.mode != "supabase":
            raise RuntimeError("AUTH_MODE must be either demo or supabase.")
        if self.settings.persistence_backend.lower() != "database":
            raise RuntimeError(
                "AUTH_MODE=supabase requires PERSISTENCE_BACKEND=database."
            )
        if not self.settings.supabase_url or not self.settings.supabase_publishable_key:
            raise RuntimeError(
                "AUTH_MODE=supabase requires SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY."
            )

    def authenticate(self, authorization: str | None) -> AuthenticatedUser:
        if self.mode != "supabase":
            raise AccessError(
                401, "Sign-in is not enabled in the public demo workspace."
            )
        self._validate_configuration()
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
            workspace_id = normalize_workspace_id(
                requested_workspace_id, default=self.settings.default_workspace_id
            )
        except ValueError as exc:
            raise AccessError(400, str(exc)) from exc

        if self.mode == "demo":
            if require_authenticated:
                raise AccessError(
                    401, "This endpoint requires a signed-in workspace user."
                )
            if workspace_id != self.settings.default_workspace_id:
                raise AccessError(
                    403, "The public demo can only access the demo workspace."
                )
            return AccessContext(
                workspace_id=self.settings.default_workspace_id,
                role="public_demo",
            )

        user = self.authenticate(authorization)
        role = self.repository.membership_role(user.user_id, workspace_id)
        if role is None:
            raise AccessError(403, "User is not a member of this workspace.")
        return AccessContext(
            workspace_id=workspace_id,
            role=role,
            user_id=user.user_id,
            email=user.email,
        )
