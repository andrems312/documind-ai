"""Armazenamento em disco local, para desenvolvimento e testes."""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.storage.base import StorageError, ensure_safe_path


class LocalStorage:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str) -> Path:
        full = (self.root / ensure_safe_path(path)).resolve()
        if self.root not in full.parents:
            raise ValueError("Caminho fora do diretório de armazenamento.")
        return full

    async def put(self, path: str, data: bytes, content_type: str = "application/pdf") -> None:
        target = self._resolve(path)

        def _write() -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(".tmp")
            tmp.write_bytes(data)
            tmp.replace(target)

        await asyncio.to_thread(_write)

    async def get(self, path: str) -> bytes:
        target = self._resolve(path)
        try:
            return await asyncio.to_thread(target.read_bytes)
        except FileNotFoundError as exc:
            raise StorageError("Arquivo não encontrado no armazenamento.") from exc

    async def delete(self, path: str) -> None:
        target = self._resolve(path)
        await asyncio.to_thread(target.unlink, True)

    async def aclose(self) -> None:
        return None
