"""OSTRIS corpus tools for the maqam-score skill.

The package has two halves:

* offline corpus work (``sync``, ``audit``, ``build``, ``features``,
  ``priors``, ``idioms``, ``similarity --build``, ``eval``) that turns the
  OSTRIS manifests and SheetSage2 transcripts into canonical feature records,
  objective priors, a structural idiom bank, and an objective evaluation split;
* online composition helpers (``plan``, ``exemplar``, ``similarity --score``,
  ``check``) that the skill calls while writing a score.

No module emits a maqam label.  ``mode_hypothesis`` is unreviewed, every prior
records ``maqam_conditioned: false``, and ``check`` reports
``maqam_fit.available: false``.

Everything is standard-library only and runs on CPU.  The vendored
``abc_tools.py`` next to this package is the parser contract; do not replace it.
"""

__version__ = "0.3.0"
