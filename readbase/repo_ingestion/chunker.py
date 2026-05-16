from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Iterable

from readbase.settings import (
    CHUNK_LINES,
    CHUNK_OVERLAP,
    MAX_FILE_BYTES,
    SKIP_DIRS,
    TEXT_EXTENSIONS,
    TEXT_FILENAMES,
)


# Walk the repo and yield only files that look useful for code Q&A. `os.walk`
# gives us mutable `dirs`, so editing it in-place prevents descending into
# skipped folders like node_modules or .git.
def iter_source_files(root: Path) -> Iterable[Path]:
    for current, dirs, files in os.walk(root):
        dirs[:] = [
            d
            for d in dirs
            if d not in SKIP_DIRS and not (d.startswith(".") and d != ".github")
        ]
        for file_name in files:
            path = Path(current) / file_name
            if should_index(path):
                yield path


# Cheap file filter before reading bytes. We keep known text filenames and code
# extensions, and ignore most hidden files to avoid editor/cache metadata.
def should_index(path: Path) -> bool:
    if path.name.startswith(".") and path.name not in TEXT_FILENAMES:
        return False
    if path.name in TEXT_FILENAMES:
        return True
    if path.suffix in TEXT_EXTENSIONS:
        return True
    return False


# Safely read a candidate source file. Returning None means "skip this file";
# that is easier for the caller than raising errors for unreadable/binary files.
def read_text_file(path: Path) -> str | None:
    try:
        # Very large files can dominate an index and slow down simple retrieval.
        if path.stat().st_size > MAX_FILE_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    # Null bytes are a strong signal that the file is binary, not text/code.
    if b"\x00" in data[:2048]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        # Keep partially readable files instead of failing the whole indexing job.
        return data.decode("utf-8", errors="ignore")


# Convert every readable file into chunk dictionaries and count indexed files.
# The retriever later stores these dictionaries in a JSON index.
def chunk_repository(root: Path) -> tuple[list[dict], int]:
    chunks: list[dict] = []
    file_count = 0
    for path in iter_source_files(root):
        text = read_text_file(path)
        if not text:
            continue
        file_count += 1
        relative_path = path.relative_to(root).as_posix()
        chunks.extend(chunk_text(relative_path, text))
    return chunks, file_count


# Split one file into overlapping line windows. The overlap is intentional:
# if a function starts near the end of one chunk, the next chunk still sees it.
def chunk_text(relative_path: str, text: str) -> list[dict]:
    lines = text.splitlines()
    if not lines:
        return []

    chunks = []
    step = max(1, CHUNK_LINES - CHUNK_OVERLAP)
    for start in range(0, len(lines), step):
        end = min(start + CHUNK_LINES, len(lines))
        selected = lines[start:end]
        chunk_text_value = "\n".join(selected).strip()
        if not chunk_text_value:
            continue

        # Each chunk carries citation metadata so answers can point back to files.
        chunk_id = stable_chunk_id(relative_path, start + 1, end, chunk_text_value)
        chunks.append(
            {
                "id": chunk_id,
                "path": relative_path,
                "start_line": start + 1,
                "end_line": end,
                "text": chunk_text_value,
            }
        )

        if end == len(lines):
            break
    return chunks


# Deterministic ids make saved indexes stable across runs when content is unchanged.
def stable_chunk_id(path: str, start_line: int, end_line: int, text: str) -> str:
    raw = f"{path}:{start_line}:{end_line}:{text[:200]}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:16]
