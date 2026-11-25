#!/usr/bin/env python3
"""Measure an OpenCode session export against the 10x score budget.

    python3 analysis/measure_session.py opencode_session_12.json \
        --score session-12/score.abc --max-ratio 10 --max-message 8000
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

try:
    import tiktoken
except Exception:  # noqa: BLE001
    tiktoken = None


def tokens_of(message: dict) -> tuple[int, int, int, int]:
    t = message.get("tokens") or {}
    cache = t.get("cache") or {}
    return (int(t.get("input", 0)), int(t.get("output", 0)),
            int(t.get("reasoning", 0)), int(cache.get("read", 0)))


def parts(message: dict, kind: str) -> list[dict]:
    return [p for p in (message.get("content") or [])
            if isinstance(p, dict) and p.get("type") == kind]


def tool_calls(message: dict) -> list[tuple[str, dict]]:
    out = []
    for part in parts(message, "tool"):
        out.append((str(part.get("name")), (part.get("state") or {}).get("input") or {}))
    return out


def score_tokens(path: Path | None) -> int | None:
    if path is None or not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    if tiktoken is not None:
        try:
            return len(tiktoken.get_encoding("cl100k_base").encode(text))
        except Exception:  # noqa: BLE001
            pass
    return max(1, round(len(text) / 4))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("session", type=Path, help="opencode_session_*.json")
    ap.add_argument("--score", type=Path, default=None, help="score.abc for the ratio")
    ap.add_argument("--max-ratio", type=float, default=None,
                    help="fail if generated / score tokens exceeds this")
    ap.add_argument("--max-message", type=int, default=None,
                    help="fail if a single message exceeds this generated token count")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args(argv)

    data = json.loads(args.session.read_text(encoding="utf-8"))
    info = data.get("info") or {}
    messages = data.get("messages") or []
    total_input = int((info.get("tokens") or {}).get("input", 0))
    total_output = int((info.get("tokens") or {}).get("output", 0))
    total_reasoning = int((info.get("tokens") or {}).get("reasoning", 0))
    generated = total_output + total_reasoning

    rows = []
    model_gen: Counter = Counter()
    for index, message in enumerate(messages):
        tin, tout, tre, cache = tokens_of(message)
        gen = tout + tre
        rows.append({"index": index, "type": message.get("type"), "model": (message.get("model") or {}).get("id"),
                     "input": tin, "output": tout, "reasoning": tre, "cache_read": cache, "generated": gen})
        if gen:
            model_gen[(message.get("model") or {}).get("id") or "?"] += gen

    max_message = max((r["generated"] for r in rows), default=0)
    score = score_tokens(args.score)
    ratio = (generated / score) if score else None

    shell_cmds = []
    writes = []
    for message in messages:
        for name, inp in tool_calls(message):
            if name == "shell":
                shell_cmds.append(str(inp.get("command", "")))
            elif name == "write":
                writes.append((str(inp.get("path", "")), str(inp.get("content", ""))))

    checker_runs = sum(len(re.findall(r"checker\.py\s+score\.abc", c)) for c in shell_cmds)
    score_writes = sum(1 for path, _ in writes if path.endswith("score.abc"))
    hand_scripts = sum(1 for path, _ in writes if path.endswith(".py"))
    source_reads = sum(1 for c in shell_cmds if re.search(
        r"(sed -n|grep -n|cat ).*(scripts/[a-z_]+\.py|SKILL\.md)", c))
    repair_uses = sum(1 for c in shell_cmds if "repair.py" in c)
    doctor_uses = sum(1 for c in shell_cmds if "abc_doctor.py" in c)
    quality_uses = sum(1 for c in shell_cmds if "quality.py" in c)

    result = {
        "session": str(args.session), "model_info": info.get("model"),
        "input": total_input, "output": total_output, "reasoning": total_reasoning,
        "generated": generated, "score_tokens": score, "ratio": ratio,
        "max_message": max_message,
        "model_generated": dict(model_gen),
        "checker_runs": checker_runs, "score_writes": score_writes,
        "hand_scripts": hand_scripts, "source_reads": source_reads,
        "repair_uses": repair_uses, "doctor_uses": doctor_uses,
        "quality_uses": quality_uses,
        "top_messages": sorted(rows, key=lambda r: -r["generated"])[:8],
    }

    print(f"session        {args.session}")
    print(f"generated      {generated:,}  (output {total_output:,} + reasoning {total_reasoning:,})")
    if score:
        print(f"score.abc      {score:,} tokens")
        print(f"ratio          {ratio:.1f}x  (10x budget {score * 10:,})")
    print(f"max message    {max_message:,}")
    print("model split    " + ", ".join(f"{k} {v:,}" for k, v in model_gen.most_common()))
    print(f"checker runs   {checker_runs}   (budget 4)")
    print(f"score writes   {score_writes}   (budget 0 direct; CLI only)")
    print(f"hand scripts   {hand_scripts}  (budget 0)")
    print(f"source reads   {source_reads}  (budget 0)")
    print(f"repair/doctor  {repair_uses}/{doctor_uses}  (quality {quality_uses})")
    print("\ntop messages")
    for r in result["top_messages"]:
        print(f"  m{r['index']:<4} {str(r['type']):<10} {str(r['model']):<32} "
              f"gen {r['generated']:>7,} (out {r['output']:,}, rea {r['reasoning']:,})")

    failed = []
    if args.max_ratio is not None and ratio is not None and ratio > args.max_ratio:
        failed.append(f"ratio {ratio:.1f}x > {args.max_ratio}x")
    if args.max_message is not None and max_message > args.max_message:
        failed.append(f"max message {max_message:,} > {args.max_message:,}")
    if args.max_ratio is not None and score is None:
        failed.append("--max-ratio needs --score")

    if args.json:
        result["failed"] = failed
        args.json.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n",
                             encoding="utf-8")
        print(f"\nwrote {args.json}")

    if failed:
        print("\nFAIL: " + "; ".join(failed), file=sys.stderr)
        return 1
    print("\nPASS: inside the declared budget")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
