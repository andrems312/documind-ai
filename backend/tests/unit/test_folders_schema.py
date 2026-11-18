import pytest
from pydantic import ValidationError

from app.schemas.folders import FolderCreate, FolderUpdate


def test_name_is_stripped() -> None:
    assert FolderCreate(name="  Contratos  ").name == "Contratos"


def test_blank_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        FolderCreate(name="   ")


def test_valid_hex_color_is_lowercased() -> None:
    assert FolderCreate(name="X", color="#7C6CF6").color == "#7c6cf6"


@pytest.mark.parametrize("color", ["roxo", "#fff", "7c6cf6", "#12345g"])
def test_invalid_color_is_rejected(color: str) -> None:
    with pytest.raises(ValidationError):
        FolderCreate(name="X", color=color)


def test_empty_color_becomes_none() -> None:
    assert FolderCreate(name="X", color="  ").color is None


def test_update_allows_partial_fields() -> None:
    update = FolderUpdate(color="#34d5c8")
    assert update.name is None
    assert "name" not in update.model_fields_set
    assert update.color == "#34d5c8"
