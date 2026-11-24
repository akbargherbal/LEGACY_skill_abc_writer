# The composing dialect (remixer reference)

The runtime parser is `scripts/abc_tools.py`. It fails closed. A stored library
song may use `L:1/16` or `L:1/32`; both are valid. A remix score may use either
as long as the plan's `unit` matches.

## Header — exactly eight lines

```abc
X:1
T:
M:4/4
L:1/16
Q:1/4=73
V: Vocal clef=treble name="Vocal Melody" snm="Vocal"
V: Ins clef=treble name="Ins Melody" snm="Inst."
K:Dm
```

- `K:` accepts a standard major or minor key only. Spell other degrees with
  `_`/`^` at each occurrence.
- `L:` denominator must be a power of two. `L:1/16` and `L:1/32` are the
  practical choices.
- `Q:` is an integer quarter-note tempo.
- No extra header lines. A provenance comment goes after the header and starts
  with `% `.

## Body

- `% section` then `V: Vocal` + 1–4 bars, then `V: Ins` + the same number of
  bars. Repeat.
- Every music line ends with a plain `|`. No `]`, repeats, or double barlines.
- `Z`/`Z2`–`Z4` must be the whole bar. `z` is a partial rest.
- A meter change is `M:n/d` after `V:` and before the music line.
- An inline key change is `[K:...]` inside a bar.
- Allowed durations are `1,2,3,4,6,8,12,16,24,32,48` in `L` units. Split a long
  note with ties (`-`), never with an unsupported duration.
- No blank line in the body. A blank line ends the tune for the parser.
- End with a full-bar rest in both voices before rendering.

## Slice output

`slice` emits one bar per voice group, with a `% src=...` provenance comment.
That output is a reference fragment; copy the material you need into your own
score. **Delete the provenance line when pasting**; the checker treats `% `
comments as section names. Do not paste a whole section and call it a remix.

## Transposition

`--to-key` chooses the smallest absolute interval in `[-6,+6]` (ties upward).
`--transpose N` is explicit. Both are chromatic 12-TET; the corpus has no
quarter tones. A range that crosses an inline key change is refused by default.
