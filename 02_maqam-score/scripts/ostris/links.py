"""Link the 482-track instrumental library to its source transcripts.

The library is the union of two source datasets:

* ``yt500`` — 460 tracks, linked by ``video_id`` to the YT500 ABC shard index;
* ``fadhl_shaker_shortlist`` — 22 tracks, linked by shortlist name to the
  Fadl Shaker reference ABC and (when present) the selected-scores transcript.

The 35 YT500 transcripts not used by the library are the natural held-out set.
No field is guessed silently: every link carries the source URI it came from.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .sources import Cache, SourceError

INSTRUMENTAL_MANIFEST = "OSTRIS_Arabic_Suno_Finetuning/arabic_instrumental_dataset_manifest.json"
V3_MANIFEST = "OSTRIS_Arabic_Suno_Finetuning/v3_arabmaqamrock_dataset_manifest.json"
YT500_MANIFEST = "TRANSCRIPTS/YT500/_manifest.jsonl"
YT500_SHARD_GLOB = "TRANSCRIPTS/YT500/YT500/abc/shard-*.json"
FADL_SHORTLIST = "DATASET/fadhl_shaker_instrumental_18_shortlist/shortlist.json"
FADL_SELECTED_MANIFEST = "TRANSCRIPTS/fadhl_shaker_selected_scores/transcribe_manifest.json"
FADL_ALBUM_GLOB = "TRANSCRIPTS/FADL_SHAKER/abc/*.json"
FADL_SELECTED_PREFIX = "TRANSCRIPTS/fadhl_shaker_selected_scores"

YT_OUT_NAME = re.compile(r"^yt500-(\d+)-([A-Za-z0-9_-]+)$")
FADL_OUT_NAME = re.compile(r"^fs18-(.+)_(\d+)$")

# The shortlist uses transliterated slugs; the selected-scores manifest uses the
# original Arabic stem.  Twenty-two entries, kept here so the link is explicit
# and reviewable rather than a fuzzy title match.
FADL_SLUG_TO_STEM = {
    "al_dawr_ala_meen": "الدور على مين",
    "al_hal": "الحال",
    "al_qissa_wama_fiha": "القصة وما فيها",
    "ana_min_akhiraha": "أنا من آخرها",
    "awwal_ma_bashufak": "أول مابشوفك",
    "badeet_atib": "بديت أطيب",
    "bafakker_bil_sa3at": "بفكر بالساعات",
    "feen_layalik": "فين لياليك",
    "fustan_alhelwa": "فستان الحلوة",
    "ghayb": "غيب",
    "habeetak": "حبيتك",
    "hazak_ya_albi": "حظك ياقلبي",
    "leh_aljarh": "ليه الجرح",
    "lissa_alhala_matasarish": "لسه الحاله ماتسرش",
    "ma3_alsalama": "مع السلامة",
    "ma_khalas": "ما خلاص",
    "mata_habibi_mata": "متى حبيبي متى",
    "min_kothr_hobbi_feek": "من كثر حبي فيك",
    "saharni_alshawq": "سهرني الشوق",
    "saneen_alshawq": "سنين الشوق",
    "waynak_habib": "وينك حبيب",
    "ya_hawa_alghaleen": "يا هوى الغالين",
}


def rel_from_uri(uri: str) -> str:
    """Return the cache-relative path for a bucket or local source URI."""
    text = str(uri)
    for marker in ("OSTRIS_Arabic_Suno_Finetuning/", "TRANSCRIPTS/", "DATASET/"):
        if marker in text:
            return marker + text.split(marker, 1)[1]
    raise SourceError(f"cannot derive a data-root path from {uri!r}")


def record_id(link: dict) -> str:
    """Stable per-track identifier, shared by audit and build."""
    if link.get("source_dataset") == "yt500" and link.get("video_id"):
        return f"yt500-{int(link['source_rank']):04d}-{link['video_id']}"
    return link.get("out_name", "unknown")


@dataclass
class Inventory:
    instrumental: dict
    v3: dict
    yt_header: dict
    yt_manifest: list[dict]
    yt_tracks: list[dict]
    fadl_shortlist: dict
    fadl_selected: dict
    fadl_albums: list[dict] = field(default_factory=list)

    @property
    def yt_by_video(self) -> dict[str, dict]:
        return {t.get("video_id"): t for t in self.yt_tracks if t.get("video_id")}

    @property
    def yt_manifest_by_video(self) -> dict[str, dict]:
        return {t.get("video_id"): t for t in self.yt_manifest if t.get("video_id")}

    @property
    def fadl_shortlist_by_name(self) -> dict[str, dict]:
        return {t.get("name"): t for t in self.fadl_shortlist.get("tracks", [])}

    @property
    def fadl_selected_by_stem(self) -> dict[str, dict]:
        return {t.get("stem"): t for t in self.fadl_selected.get("tracks", [])}

    @property
    def fadl_selected_by_track_id(self) -> dict[str, dict]:
        return {t.get("track_id"): t for t in self.fadl_selected.get("tracks", [])}


def load_inventory(cache: Cache) -> Inventory:
    for rel in (INSTRUMENTAL_MANIFEST, V3_MANIFEST, YT500_MANIFEST, FADL_SHORTLIST):
        if not cache.exists(rel):
            raise SourceError(
                f"missing {rel}; run `ostris_cli.py sync --data-root <root> --cache {cache.root}`"
            )
    yt_records = cache.read_jsonl(YT500_MANIFEST)
    header = yt_records[0] if yt_records and yt_records[0].get("record") == "header" else {}
    manifest_tracks = [r for r in yt_records if r.get("record") == "track"]

    shard_files = cache.glob(YT500_SHARD_GLOB)
    if not shard_files:
        raise SourceError(f"missing YT500 ABC shards under {YT500_SHARD_GLOB}")
    yt_tracks: list[dict] = []
    for path in shard_files:
        shard = cache.read_json(cache.rel(path))
        yt_tracks.extend(shard.get("tracks", []))

    fadl_selected: dict = {}
    if cache.exists(FADL_SELECTED_MANIFEST):
        fadl_selected = cache.read_json(FADL_SELECTED_MANIFEST)

    albums: list[dict] = []
    for path in cache.glob(FADL_ALBUM_GLOB):
        albums.append(cache.read_json(cache.rel(path)))

    return Inventory(
        instrumental=cache.read_json(INSTRUMENTAL_MANIFEST),
        v3=cache.read_json(V3_MANIFEST),
        yt_header=header,
        yt_manifest=manifest_tracks,
        yt_tracks=yt_tracks,
        fadl_shortlist=cache.read_json(FADL_SHORTLIST),
        fadl_selected=fadl_selected,
        fadl_albums=albums,
    )


def held_out_yt500(inv: Inventory) -> list[dict]:
    """YT500 tracks that never entered the 482-track library."""
    used = set()
    for track in inv.instrumental.get("tracks", []):
        match = YT_OUT_NAME.match(track.get("out_name", ""))
        if match:
            used.add(match.group(2))
    return [t for t in inv.yt_manifest if t.get("video_id") not in used]


def duplicate_groups(inv: Inventory) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for track in inv.yt_manifest:
        group = track.get("duplicate_group")
        if group:
            groups.setdefault(group, []).append(
                {
                    "track_id": track.get("track_id"),
                    "video_id": track.get("video_id"),
                    "source_rank": track.get("source_rank"),
                    "title": track.get("title"),
                    "duplicate_of": track.get("duplicate_of"),
                }
            )
    return [{"group": name, "tracks": tracks} for name, tracks in groups.items()]


def link_library(inv: Inventory, cache: Cache) -> list[dict]:
    """Return one link record per instrumental track, in manifest order."""
    yt_by_video = inv.yt_by_video
    shortlist = inv.fadl_shortlist_by_name
    selected = inv.fadl_selected_by_stem
    duplicate_group_by_video = {
        t.get("video_id"): t.get("duplicate_group")
        for t in inv.yt_manifest
        if t.get("duplicate_group")
    }
    links: list[dict] = []

    for track in inv.instrumental.get("tracks", []):
        out_name = track.get("out_name", "")
        base = {
            "out_name": out_name,
            "source_dataset": track.get("source_dataset"),
            "title": track.get("title"),
            "artist": track.get("artist"),
            "audio_uri": track.get("source_uri"),
            "audio_duration_s": track.get("audio_duration_s"),
            "audio_sha256": track.get("audio_sha256"),
            "caption_status": track.get("caption_status"),
            "matched": False,
            "match_method": None,
            "transcript_id": None,
            "abc_uri": None,
            "abc_text": None,
            "abc_kind": None,
            "reference_abc_uri": None,
            "reference_abc_text": None,
            "selected_transcript_uri": None,
            "selected_abc_text": None,
            "transcribe_status": None,
            "selected_transcribe_status": None,
            "source_qc": None,
            "duplicate_of": None,
            "duplicate_group": None,
            "notes": [],
        }
        if track.get("source_dataset") == "yt500":
            match = YT_OUT_NAME.match(out_name)
            if not match:
                base["notes"].append("out_name does not match yt500-<rank>-<video_id>")
                links.append(base)
                continue
            rank, video_id = int(match.group(1)), match.group(2)
            rec = yt_by_video.get(video_id)
            base["match_method"] = "video_id"
            base["video_id"] = video_id
            base["source_rank"] = rank
            base["duplicate_group"] = duplicate_group_by_video.get(video_id)
            if rec is None:
                base["notes"].append("video_id not present in YT500 shard index")
                links.append(base)
                continue
            base.update(
                matched=True,
                transcript_id=rec.get("track_id"),
                abc_uri=rec.get("raw_gcs"),
                abc_text=rec.get("abc"),
                abc_kind="source_transcript",
                transcribe_status=rec.get("transcribe_status"),
                source_qc=rec.get("qc"),
                duplicate_of=rec.get("duplicate_of"),
            )
            if not rec.get("abc"):
                base["notes"].append("YT500 transcript has no ABC")
            if rec.get("duplicate_of"):
                base["notes"].append(f"duplicate of {rec['duplicate_of']}")
            if rank != rec.get("source_rank"):
                base["notes"].append(
                    f"rank mismatch: manifest {rank}, transcript {rec.get('source_rank')}"
                )
        elif track.get("source_dataset") == "fadhl_shaker_shortlist":
            base["match_method"] = "shortlist_name"
            short = shortlist.get(out_name)
            if short is None:
                base["notes"].append("out_name not present in FADL shortlist")
                links.append(base)
                continue
            name = short.get("name", out_name)
            slug = FADL_OUT_NAME.match(name)
            slug = slug.group(1) if slug else name.removeprefix("fs18-")
            stem = FADL_SLUG_TO_STEM.get(slug)
            base["fadl_slug"] = slug
            base["fadl_stem"] = stem
            base["matched"] = True
            base["transcript_id"] = short.get("source_track_id")
            base["reference_abc_uri"] = short.get("input_uri")
            base["duplicate_of"] = short.get("duplicate_of")
            base["transcribe_status"] = "ok" if short.get("input_uri") else "missing-abc"
            if short.get("input_uri"):
                rel = rel_from_uri(short["input_uri"])
                if cache.exists(rel):
                    base["reference_abc_text"] = cache.read_text(rel)
                else:
                    base["notes"].append(f"reference ABC not in cache: {rel}")
            if stem:
                sel = selected.get(stem)
                if sel:
                    base["selected_transcribe_status"] = sel.get("status")
                    sel_rel = f"{FADL_SELECTED_PREFIX}/{stem}/score.abc"
                    base["selected_transcript_uri"] = sel_rel
                    if cache.exists(sel_rel):
                        base["selected_abc_text"] = cache.read_text(sel_rel)
                    else:
                        base["notes"].append(f"selected transcript not in cache: {sel_rel}")
                    if sel.get("status") != "ok" or not sel.get("abc"):
                        base["notes"].append(
                            f"selected transcript status {sel.get('status')!r}"
                        )
                else:
                    base["notes"].append(f"no selected-scores transcript for stem {stem!r}")
            else:
                base["notes"].append(f"no Arabic stem mapping for slug {slug!r}")
            # Prefer the original-song transcript; fall back to the reference
            # conditioner that was actually used for the instrumental render.
            if base["selected_abc_text"]:
                base["abc_uri"] = base["selected_transcript_uri"]
                base["abc_text"] = base["selected_abc_text"]
                base["abc_kind"] = "selected_source_transcript"
                base["transcribe_status"] = base["selected_transcribe_status"]
            elif base["reference_abc_text"]:
                base["abc_uri"] = base["reference_abc_uri"]
                base["abc_text"] = base["reference_abc_text"]
                base["abc_kind"] = "reference_conditioner"
        else:
            base["notes"].append(f"unknown source_dataset {track.get('source_dataset')!r}")
        links.append(base)
    return links
