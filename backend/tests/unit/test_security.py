import pytest

from app.core.exceptions import UnauthorizedError
from app.core.security import JWTVerifier
from tests.conftest import make_token


def test_valid_token_returns_user(settings) -> None:
    uid, token = make_token(email="ana@example.com", full_name="Ana Souza")
    user = JWTVerifier(settings).user_from_token(token)
    assert user.id == uid
    assert user.email == "ana@example.com"
    assert user.full_name == "Ana Souza"
    assert user.role == "authenticated"


def test_expired_token_is_rejected(settings) -> None:
    _, token = make_token(expires_in=-10)
    with pytest.raises(UnauthorizedError, match="expirada"):
        JWTVerifier(settings).user_from_token(token)


def test_wrong_secret_is_rejected(settings) -> None:
    _, token = make_token(secret="outro-segredo-qualquer-com-32-caracteres!!")
    with pytest.raises(UnauthorizedError, match="inválido"):
        JWTVerifier(settings).user_from_token(token)


def test_wrong_audience_is_rejected(settings) -> None:
    _, token = make_token(audience="anon")
    with pytest.raises(UnauthorizedError):
        JWTVerifier(settings).user_from_token(token)


def test_garbage_token_is_rejected(settings) -> None:
    with pytest.raises(UnauthorizedError):
        JWTVerifier(settings).user_from_token("nao.e.um.jwt")
