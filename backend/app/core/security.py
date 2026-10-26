"""Supabase JWT verification for FastAPI dependencies.

Supports the classic symmetric secret (SUPABASE_JWT_SECRET, HS256) and
asymmetric JWKS keys published at SUPABASE_URL/.well-known/jwks.json
(RS256/ES256), used by newer Supabase projects.
"""

from __future__ import annotations

from dataclasses import dataclass

import jwt

from app.core.exceptions import AuthenticationError


@dataclass(frozen=True)
class AuthUser:
    user_id: str
    email: str | None
    full_name: str | None

    def display_name(self) -> str:
        if self.full_name:
            return self.full_name
        if self.email:
            return self.email.split("@", 1)[0]
        return self.user_id[:8]


def _decode_hs256(token: str, secret: str) -> dict:
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired token") from exc


def _decode_jwks(token: str, jwks_url: str) -> dict:
    try:
        client = jwt.PyJWKClient(jwks_url, cache_keys=True)
        signing_key = client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired token") from exc


def verify_supabase_token(
    token: str,
    *,
    jwt_secret: str,
    supabase_url: str,
) -> AuthUser:
    """Verify a Supabase access token and return the authenticated user.

    The token's declared algorithm selects the verifier. Both paths validate
    the signature with a fixed allowlist of algorithms.
    """
    try:
        algorithm = jwt.get_unverified_header(token).get("alg")
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired token") from exc

    if algorithm == "HS256" and jwt_secret.strip():
        claims = _decode_hs256(token, jwt_secret.strip())
    elif algorithm in {"RS256", "ES256"} and supabase_url.strip():
        url = supabase_url.strip().rstrip("/")
        claims = _decode_jwks(token, f"{url}/auth/v1/.well-known/jwks.json")
    else:
        raise AuthenticationError("Unsupported token signing algorithm")

    user_id = claims.get("sub")
    if not user_id:
        raise AuthenticationError("Token does not identify a user")

    email = claims.get("email")
    metadata = claims.get("user_metadata") or {}
    return AuthUser(
        user_id=str(user_id),
        email=email if isinstance(email, str) else None,
        full_name=metadata.get("full_name") or metadata.get("name"),
    )


def ConfigurationErrorMissingJWT() -> AuthenticationError:
    return AuthenticationError("Server authentication is not configured")
