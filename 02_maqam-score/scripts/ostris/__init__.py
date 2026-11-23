"""OSTRIS corpus tools for the maqam-score skill.

The package has two halves:

* offline corpus work (``sync``, ``audit``, ``build``, ``features``) that turns
  the OSTRIS manifests and SheetSage2 transcripts into linkable, canonical
  feature records;
* online composition helpers (later ``plan``, ``exemplar``, ``check``) that the
  skill calls while writing a score.

Everything is standard-library only and runs on CPU.  The vendored
``abc_tools.py`` next to this package is the parser contract; do not replace it.
"""

__version__ = "0.3.0.dev0"
