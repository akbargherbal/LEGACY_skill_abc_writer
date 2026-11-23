"""Populate a local cache from the project data root.

Usage::

    python3 scripts/ostris_cli.py sync \
        --data-root gs://akbar-december-2024-backup \
        --cache analysis/out/ostris/source

The cache mirrors the data-root paths, so ``audit`` can run offline afterwards.
Only lightweight inputs are copied: manifests, YT500 ABC shards, FADL album
JSONs, the FADL shortlist, and the FADL reference ABCs.  The 2.95 GiB audio
bundle is never downloaded.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

INSTRUMENTAL_MANIFEST = "OSTRIS_Arabic_Suno_Finetuning/arabic_instrumental_dataset_manifest.json"
V3_MANIFEST = "OSTRIS_Arabic_Suno_Finetuning/v3_arabmaqamrock_dataset_manifest.json"
YT500_MANIFEST = "TRANSCRIPTS/YT500/_manifest.jsonl"
YT500_ABC_GLOB = "TRANSCRIPTS/YT500/YT500/abc/*.json"
FADL_ALBUM_GLOB = "TRANSCRIPTS/FADL_SHAKER/abc/*.json"
FADL_SHORTLIST = "DATASET/fadhl_shaker_instrumental_18_shortlist/shortlist.json"
FADL_REFERENCE_GLOB = "DATASET/fadhl_shaker_instrumental_18/abc/*.abc"
FADL_SELECTED_MANIFEST = "TRANSCRIPTS/fadhl_shaker_selected_scores/transcribe_manifest.json"
FADL_SELECTED_PREFIX = "TRANSCRIPTS/fadhl_shaker_selected_scores"

# Individual files that anchor the inventory.  Keep this list small and stable.
FILES = (
    INSTRUMENTAL_MANIFEST,
    V3_MANIFEST,
    YT500_MANIFEST,
    FADL_SHORTLIST,
    FADL_SELECTED_MANIFEST,
)

# Directory globs.  The destination keeps the same relative directory.
GLOBS = (
    ("TRANSCRIPTS/YT500/YT500/abc", "*.json"),
    ("TRANSCRIPTS/FADL_SHAKER/abc", "*.json"),
    ("DATASET/fadhl_shaker_instrumental_18/abc", "*.abc"),
)


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, text=True, capture_output=True)


def _is_gcs(root: str) -> bool:
    return root.startswith("gs://")


def _copy_one(src: str, dst: Path, force: bool) -> None:
    if dst.is_file() and not force:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if _is_gcs(src):
        _run(["gsutil", "-q", "cp", src, str(dst)])
    else:
        shutil.copy2(src, dst)


def _copy_glob(base: str, pattern: str, dst_dir: Path, force: bool) -> int:
    dst_dir.mkdir(parents=True, exist_ok=True)
    if _is_gcs(base):
        if not force and any(dst_dir.glob(pattern)):
            return len(list(dst_dir.glob(pattern)))
        _run(["gsutil", "-q", "-m", "cp", f"{base.rstrip('/')}/{pattern}", str(dst_dir) + "/"])
        return len(list(dst_dir.glob(pattern)))
    copied = 0
    for src in sorted(Path(base).glob(pattern)):
        dst = dst_dir / src.name
        if not dst.is_file() or force:
            shutil.copy2(src, dst)
            copied += 1
    return copied


def _copy_selected_scores(
    cache: Path, force: bool, data_root: str
) -> dict:
    """Copy the per-song reference ABCs named by the selected-scores manifest.

    The manifest stores local ``abc`` paths; the bucket keeps the same tree under
    ``TRANSCRIPTS/fadhl_shaker_selected_scores/<stem>/score.abc``.  This is the
    only place where a bucket layout is inferred from a manifest, so failures
    are reported instead of raised.
    """
    manifest_path = cache / FADL_SELECTED_MANIFEST
    if not manifest_path.is_file():
        return {"copied": 0, "missing": [], "manifest": False}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    out_dir = cache / FADL_SELECTED_PREFIX
    out_dir.mkdir(parents=True, exist_ok=True)
    copied, missing = 0, []
    for track in manifest.get("tracks", []):
        stem = track.get("stem")
        if not stem:
            continue
        rel = f"{stem}/score.abc"
        dst = out_dir / rel
        if dst.is_file() and not force:
            copied += 1
            continue
        src = f"{data_root.rstrip('/')}/{FADL_SELECTED_PREFIX}/{rel}"
        try:
            _copy_one(src, dst, force=True)
            copied += 1
        except subprocess.CalledProcessError:
            missing.append(rel)
    return {"copied": copied, "missing": missing, "manifest": True}


def sync(data_root: str, cache: str | Path, force: bool = False) -> dict:
    """Copy the lightweight corpus inputs into ``cache``.

    Returns a small JSON-serialisable summary.  Missing optional inputs are
    reported, not fatal; ``audit`` decides what it needs.
    """
    root = Path(cache).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    copied_files, missing_files = 0, []
    for rel in FILES:
        dst = root / rel
        try:
            _copy_one(f"{data_root.rstrip('/')}/{rel}", dst, force)
            copied_files += 1
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing_files.append(rel)

    globbed = {}
    for base, pattern in GLOBS:
        dst_dir = root / base
        try:
            n = _copy_glob(f"{data_root.rstrip('/')}/{base}", pattern, dst_dir, force)
            globbed[base] = n
        except (subprocess.CalledProcessError, FileNotFoundError):
            globbed[base] = 0
            missing_files.append(f"{base}/{pattern}")

    selected = _copy_selected_scores(root, force, data_root)
    return {
        "data_root": data_root,
        "cache": str(root),
        "files": copied_files,
        "missing_files": missing_files,
        "globbed": globbed,
        "selected_scores": selected,
    }
