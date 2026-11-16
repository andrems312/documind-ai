"""Validação de tokens JWT emitidos pelo Supabase Auth.

Suporta os dois esquemas de assinatura do Supabase:
- HS256 com o segredo legado do projeto (`SUPABASE_JWT_SECRET`);
- chaves assimétricas (ES256/RS256) publicadas no JWKS do projeto, quando o segredo não é informado.

O backend nunca cria sessões nem armazena senhas: apenas verifica assinatura, expiração e audiência,
e extrai a identidade do usuário.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

import jwt
from jwt import PyJWKClient

from app.core.config import Settings
from app.core.exceptions import UnauthorizedError

_SYMMETRIC_ALGS = ["HS256"]
_ASYMMETRIC_ALGS = ["ES256", "RS256"]


@dataclass(frozen=True, slots=True)
class AuthUser:
    id: uuid.UUID
    email: str | None
    role: str
    full_name: str | None = None
    avatar_url: str | None = None


class JWTVerifier:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._jwks_client: PyJWKClient | None = None
        if not settings.supabase_jwt_secret:
            self._jwks_client = PyJWKClient(settings.supabase_jwks_url, cache_keys=True)

    def decode(self, token: str) -> dict[str, Any]:
        try:
            if self._settings.supabase_jwt_secret:
                return jwt.decode(
                    token,
                    self._settings.supabase_jwt_secret,
                    algorithms=_SYMMETRIC_ALGS,
                    audience=self._settings.jwt_audience,
                    options={"require": ["exp", "sub"]},
                )
            assert self._jwks_client is not None
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=_ASYMMETRIC_ALGS,
                audience=self._settings.jwt_audience,
                options={"require": ["exp", "sub"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise UnauthorizedError("Sessão expirada. Faça login novamente.") from exc
        except jwt.PyJWTError as exc:
            raise UnauthorizedError("Token de autenticação inválido.") from exc

    def user_from_token(self, token: str) -> AuthUser:
        claims = self.decode(token)
        try:
            user_id = uuid.UUID(str(claims["sub"]))
        except (KeyError, ValueError) as exc:
            raise UnauthorizedError("Token sem identificador de usuário válido.") from exc

        metadata = claims.get("user_metadata") or {}
        return AuthUser(
            id=user_id,
            email=claims.get("email"),
            role=str(claims.get("role", "authenticated")),
            full_name=metadata.get("full_name") or metadata.get("name"),
            avatar_url=metadata.get("avatar_url"),
        )
