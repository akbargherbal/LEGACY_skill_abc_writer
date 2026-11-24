"""Small, dependency-free error type shared by the remixer tools."""

from __future__ import annotations


class RemixError(RuntimeError):
    """A user-facing remixer failure with an optional exit code."""

    def __init__(self, message: str, code: int = 2):
        super().__init__(message)
        self.code = code
