"""M4/M5: one check that combines the skill checker, priors, and similarity.

Gate policy (D8): ``contract`` + ``sanity`` checks are hard; ``style`` warnings
are reported and do not fail the run unless the caller passes
``--strict-style``.  A maqam-fit component is not available: there are no
reviewed maqam labels, and the report says so instead of inventing a score.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .contract import SKILL_ROOT
from .plan import validate_plan
from .priors import load_priors, select_prior
from .similarity import load_index, query_score_text
from .sources import SourceError
from .stats import percentile_of

CHECKER = SKILL_ROOT / "scripts" / "checker.py"
HARD_CLASSES = {"contract", "sanity", "structure", "exact"}
PRIOR_METRICS = (
    "chords_per_bar",
    "silence_share",
    "top_duration_share",
    "notes_per_syllable",
    "register_mean",
    "distinct_durations",
    "tessitura_share_ge_c5",
    "verse_chorus_semitones",
)


def _run_checker(score: Path, plan: Path, *, require_final_rest: bool,
                 strict_style: bool, lyrics_path: Path | None = None,
                 waive_lyrics: bool = False) -> tuple[dict | None, str]:
    if not CHECKER.is_file():
        raise SourceError(f"missing the skill checker: {CHECKER}")
    with tempfile.TemporaryDirectory(prefix="ostris-check-") as tmp:
        report = Path(tmp) / "checker.json"
        command = [
            sys.executable,
            str(CHECKER),
            str(score),
            "--plan",
            str(plan),
            "--json",
            str(report),
        ]
        if lyrics_path is not None:
            command.extend(["--lyrics", str(lyrics_path)])
        elif waive_lyrics:
            command.append("--waive-lyrics")
        if require_final_rest:
            command.append("--require-final-rest")
        if strict_style:
            command.append("--strict-style")
        completed = subprocess.run(command, capture_output=True, text=True)
        if not report.is_file():
            detail = (completed.stderr or completed.stdout or "").strip()
            return None, detail or "checker produced no report"
        return json.loads(report.read_text(encoding="utf-8")), completed.stdout


def _prior_fit(priors: dict, plan: dict, measured: dict) -> dict:
    selection = select_prior(
        priors,
        meter=plan.get("meter"),
        tempo=plan.get("tempo"),
        bars=plan.get("bars"),
    )
    data = selection["data"]["metrics"]
    percentiles = {}
    outside = []
    for metric in PRIOR_METRICS:
        value = measured.get(metric)
        result = percentile_of(value, data.get(metric))
        percentiles[metric] = result
        if result is not None and (result < 10 or result > 90):
            outside.append(
                {
                    "code": f"prior_{metric}",
                    "detail": f"{metric}={value} is at the {result:.0f}th "
                              f"percentile of `{selection['stratum']}`",
                    "class": "style",
                }
            )
    return {
        "stratum": selection["stratum"],
        "n": selection["n"],
        "confidence": selection["confidence"],
        "backoff": selection["backoff"],
        "percentiles": percentiles,
        "outside_p10_p90": [item["code"] for item in outside],
        "warnings": outside,
        "maqam_conditioned": False,
    }


def check(score_path: str | Path, plan_path: str | Path,
          report_path: str | Path | None = None,
          out_dir: str | Path | None = None, *,
          require_final_rest: bool = False,
          strict_style: bool = False,
          lyrics_path: str | Path | None = None,
          waive_lyrics: bool = False) -> dict:
    score = Path(score_path)
    plan_file = Path(plan_path)
    if not score.is_file():
        raise SourceError(f"missing score: {score}")
    if not plan_file.is_file():
        raise SourceError(f"missing plan: {plan_file}")
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    if "targets" in plan and "request" in plan:
        raise SourceError(
            f"{plan_file} is a brief.json; pass skill_plan.json to `check`"
        )
    plan_errors = validate_plan(plan)

    failures: list[dict] = []
    warnings: list[dict] = []
    skill_report = None
    if plan_errors:
        failures.append(
            {
                "code": "plan_invalid",
                "class": "contract",
                "detail": "; ".join(plan_errors),
            }
        )
    else:
        skill_report, output = _run_checker(
            score,
            plan_file,
            require_final_rest=require_final_rest,
            strict_style=strict_style,
            lyrics_path=Path(lyrics_path) if lyrics_path else None,
            waive_lyrics=waive_lyrics,
        )
        if skill_report is None:
            failures.append(
                {"code": "skill_checker", "class": "contract", "detail": output}
            )
        else:
            for item in skill_report.get("checks", []):
                if item["tag"] == "FAIL":
                    failures.append(
                        {
                            "code": item["name"],
                            "class": item["class"],
                            "detail": item["detail"],
                        }
                    )
                elif item["tag"] == "WARN":
                    warnings.append(
                        {
                            "code": item["name"],
                            "class": item["class"],
                            "detail": item["detail"],
                        }
                    )

    measured = (skill_report or {}).get("measured", {})
    prior = None
    if skill_report and plan_errors == []:
        priors_path = Path(out_dir) / "priors" / "priors.json" if out_dir else None
        if priors_path and priors_path.is_file():
            try:
                prior = _prior_fit(load_priors(priors_path), plan, measured)
                warnings.extend(prior["warnings"])
            except SourceError as error:
                warnings.append(
                    {"code": "prior_unavailable", "class": "style", "detail": str(error)}
                )

    similarity = None
    if out_dir and (Path(out_dir) / "similarity" / "index.json").is_file():
        try:
            similarity = query_score_text(
                score.read_text(encoding="utf-8"), load_index(out_dir)
            )
        except Exception as error:  # similarity is advisory, never a gate
            warnings.append(
                {
                    "code": "similarity_unavailable",
                    "class": "style",
                    "detail": f"{type(error).__name__}: {error}",
                }
            )
    quotation = (similarity or {}).get(
        "quotation",
        {"used": False, "source_id": None, "bars": 0, "confidence": 0.0},
    )

    class_name = "fail" if failures else "warn" if warnings else "pass"
    report = {
        "stage": "M4-check",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "score": str(score),
        "plan": str(plan_file),
        "pass": not failures,
        "class": class_name,
        "failures": failures,
        "warnings": warnings,
        "hard_classes": sorted(HARD_CLASSES),
        "strict_style": strict_style,
        "require_final_rest": require_final_rest,
        "measured": measured,
        "plan_valid": not plan_errors,
        "skill_report": skill_report,
        "prior": prior,
        "similarity": similarity,
        "quotation": quotation,
        "maqam_fit": {
            "available": False,
            "reason": "no reviewed maqam labels exist in this corpus",
        },
        "maqam_conditioned": False,
    }
    if report_path:
        path = Path(report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        report["report"] = str(path)
    return report
