"""Library-aware remixer tools for the abc_score_writer runtime.

The package is intentionally small and standard-library only.  It never writes
a score; it retrieves bounded material, re-emits dialect-valid fragments, and
verifies declared borrowings.
"""

from .shared import REMIX_VERSION, STORE_VERSION

__all__ = ["REMIX_VERSION", "STORE_VERSION"]
