from __future__ import annotations

from pathlib import Path

import chromadb

_clients: dict[str, chromadb.PersistentClient] = {}


def get_chroma_client(chroma_dir: Path) -> chromadb.PersistentClient:
    key = str(chroma_dir.resolve())
    chroma_dir.mkdir(parents=True, exist_ok=True)
    client = _clients.get(key)
    if client is None:
        client = chromadb.PersistentClient(path=key)
        _clients[key] = client
    return client


def reset_chroma_clients() -> None:
    _clients.clear()
