# Agent evaluation runs

This directory supports the workflow in
[`docs/agent-eval-protocol.md`](../../docs/agent-eval-protocol.md): you drop
exported sessions and their outputs, the analyst normalises them and writes the
post-mortem.

- `inbox/` — **drop raw sessions here.** Gitignored. No template required.
- `_template/` — the normalised shape the analyst fills in.
- `runs/` — normalised runs with post-mortems. Gitignored.
- `index.jsonl` — optional metadata-only roll-up; safe to commit when it has no
  transcript text.

## Drop-folder workflow

```
analysis/eval/inbox/<batch-date>/
  session-01-<agent>/
    chat.*          # .md, .json, .txt, .html — whatever the export gives
    output/         # score.abc, plan.json, reports, logs, screenshots
    prompt.md       # optional, if the task is not in the chat
    notes.md        # optional
  session-02-...
```

Then ask for the post-mortem. The analyst will:

1. normalise each session into `runs/<run-id>/` (task, gate, turns, tool calls,
   token estimate, waste tags);
2. write `postmortem.md` per session — what went right, what went wrong,
   confusion, inefficiency, token burn, root cause, smallest fix;
3. write `batch-summary.md` (cross-session themes, ranked changes) and
   `skill-changes.md` (proposed edits + do-not-change list).

## What to include

Minimum: the session export and the outputs.

Helpful, when available: agent/model/harness, the exact task prompt, token or
cost usage, wall-clock time, the skill zip hash, and whether the agent had the
unpacked skill or only pasted text.

## Rules

- One session = one agent + one task + one skill version (mark repeats).
- Never edit the chat log. Redact secrets only.
- Re-run `output/score.abc` through the pinned `checker.py` before believing
  the agent's report.
- A session without outputs is still analysable, but say why they are absent.
