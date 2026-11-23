"""Local cache access for the corpus tools.

``sync.py`` is the only module allowed to touch the network.  Everything else
reads the cache through :class:`Cache`, so an audit is reproducible from a
directory and tests never need credentials.
"""
from __future__ import annotations

import json
from pathlib import Path


class SourceError(RuntimeError):
    """A required corpus file is missing or unreadable."""


class Cache:
    """A directory that mirrors the project data root.

    Paths are always relative to the data root, for example
    ``OSTRIS_Arabic_Suno_Finetuning/arabic_instrumental_dataset_manifest.json``.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()

    def path(self, relpath: str) -> Path:
        path = (self.root / relpath).resolve()
        if self.root not in path.parents and path != self.root:
            raise SourceError(f"path escapes the cache: {relpath!r}")
        return path

    def exists(self, relpath: str) -> bool:
        return self.path(relpath).is_file()

    def read_text(self, relpath: str) -> str:
        path = self.path(relpath)
        if not path.is_file():
            raise SourceError(f"missing cache file: {relpath}")
        return path.read_text(encoding="utf-8")

    def read_json(self, relpath: str):
        return json.loads(self.read_text(relpath))

    def read_jsonl(self, relpath: str) -> list[dict]:
        return [json.loads(line) for line in self.read_text(relpath).splitlines() if line.strip()]

    def glob(self, pattern: str) -> list[Path]:
        return sorted(self.root.glob(pattern))

    def rel(self, path: Path) -> str:
        return str(Path(path).resolve().relative_to(self.root))


def read_jsonl_file(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
