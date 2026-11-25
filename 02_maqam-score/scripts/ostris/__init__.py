"""OSTRIS corpus tools for the maqam-score skill.

The package has two halves:

* offline corpus work (``sync``, ``audit``, ``build``, ``features``,
  ``priors``, ``idioms``, ``similarity --build``, ``eval``) that turns the
  OSTRIS manifests and SheetSage2 transcripts into canonical feature records,
  objective priors, a structural idiom bank, and an objective evaluation split;
* online composition helpers (``plan``, ``exemplar``, ``similarity --score``,
  ``check``) that the skill calls while writing a score.

The offline results ship with the skill under ``<skill>/data/ostris/``: the
source cache, feature records, priors, the idiom bank, the similarity index, and
the evaluation split.  The reader commands default to that directory, so the
skill runs with no network access.  ``sync`` exists only to refresh the bundle
from the project data root.

No module emits a maqam label.  ``mode_hypothesis`` is unreviewed, every prior
records ``maqam_conditioned: false``, and ``check`` reports
``maqam_fit.available: false``.

Everything is standard-library only and runs on CPU.  The vendored
``abc_tools.py`` next to this package is the parser contract; do not replace it.
"""

__version__ = "0.8.0"
