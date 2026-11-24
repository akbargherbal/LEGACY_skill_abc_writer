"""Session ledger: the context budget for library reads.

Only retrieval tools are charged: catalog, songmap, slice, and motif-find.  The
ledger is a local JSON-lines file in the working directory by default; it is
never shipped with the skill.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .errors import RemixError
from .shared import default_ledger

DEFAULT_CAP = 30_000


def resolve_path(path: str | Path | None) -> Path:
    if path:
        return Path(path).expanduser().resolve()
    env = os.environ.get("REMIX_LEDGER")
    if env:
        return Path(env).expanduser().resolve()
    return default_ledger().resolve()


def resolve_cap(cap: int | None) -> int:
    if cap is not None:
        if cap <= 0:
            raise RemixError("--cap must be positive")
        return int(cap)
    env = os.environ.get("REMIX_BUDGET")
    if env:
        try:
            value = int(env)
        except ValueError as error:
            raise RemixError(f"REMIX_BUDGET is not an integer: {env!r}") from error
        if value <= 0:
            raise RemixError("REMIX_BUDGET must be positive")
        return value
    return DEFAULT_CAP


@dataclass
class Ledger:
    path: Path
    cap: int = DEFAULT_CAP

    @classmethod
    def open(cls, path: str | Path | None = None, cap: int | None = None) -> "Ledger":
        return cls(resolve_path(path), resolve_cap(cap))

    def entries(self) -> list[dict]:
        if not self.path.is_file():
            return []
        rows = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                # A corrupt line is ignored for the total; never make the model
                # unable to inspect its own budget.
                continue
        return rows

    def total(self) -> int:
        return sum(int(row.get("chars", 0)) for row in self.entries())

    def charge(self, tool: str, song_id: str | None, text: str) -> str:
        chars = len(text)
        total = self.total()
        if total + chars > self.cap:
            raise RemixError(
                f"remix budget exceeded: {total} + {chars} > {self.cap}; "
                "run `budget --reset` or raise --cap",
                code=3,
            )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "tool": tool,
            "song_id": song_id,
            "chars": chars,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return text

    def reset(self) -> None:
        if self.path.exists():
            self.path.unlink()

    def summary(self) -> dict:
        rows = self.entries()
        per_tool: dict[str, int] = {}
        for row in rows:
            tool = str(row.get("tool", "unknown"))
            per_tool[tool] = per_tool.get(tool, 0) + int(row.get("chars", 0))
        total = sum(int(row.get("chars", 0)) for row in rows)
        return {
            "ledger": str(self.path),
            "cap": self.cap,
            "total": total,
            "remaining": max(0, self.cap - total),
            "calls": len(rows),
            "per_tool": dict(sorted(per_tool.items())),
        }
