# Session 09 — quality pass

Load the `abc-score-writer` skill, then follow `SKILL.md` §3 for the pipeline
and §5 for the artifacts. Work in the current directory; create every file
there. Do not modify the skill.

## Inputs

- Key Dm (D Kurd, `_E` for the b2), 80 BPM, 4/4.
- Section layout for the syllabifier:
  `intro=7,verse 1=13,chorus=37,verse 2=46,chorus=65,outro=77`.
- Offline: no renderer; do not claim an audition.
- Do not retrieve an exemplar or a phrase bank.
- Do not create a task list.

## Session choices (the skill owns the rest)

- **Register:** use `example/plan.json`; do not override it.
- **Qafla:** every section end and the final line holds a quarter or longer;
  `end_long` 0.25–0.50; the final note ≥ half a bar, with a 3–5-note turn.
- **Rhythm:** break the eighth grid; hit `craft.md`'s rhythm targets
  (`rhythm_variety`, `distinct_bar_share`, `top_duration`); keep repeated
  inside its band with varied durations.
- **Chorus:** a new opening motif, not a sequence of the verse head; keep a
  distinct tail.
- **Bed:** if a guitar bed is needed, put it in `seed.abc` only; `score.abc`
  stays two voices.
- **Economy:** generated (`output + reasoning`) ≤ **52,460** = 10× (score +
  seed). This is a manual stop rule, not a quality target.

## Acceptance

1. All artifacts the skill lists (`SKILL.md` §5), including `STATE.md`,
   `verify.json`, `craft.json`.
2. `checker.py` PASS 0 hard; `verify_package.py` PASS; `craft.py` report saved.
3. 0 custom scripts; 1 full score write (2 max: one global sanity fix);
   ≤4 checker runs; stop after a pass.
4. `core_draft.abc` is the first 8–16 bars of `score.abc`.
5. `seed_sheet.md` and `notes.md` are 10 numbered lines each.
6. If the first `skill` call fails, stop and report the harness defect.

## Stop rules

- No `core_draft.abc` by the 8th **composition** call (documentation reads do
  not count) → stop; record "front-loaded".
- A second full score write beyond the one global fix → stop.
- A checker run after a pass → stop.
- 52,460 generated → the analyst stops.

## Lyrics and style

```
classical arabic, melismatic, microtonal ornaments, belting, tarab, emotive expressive delivery, symphonic metal, powerful operatic performance, rhythm guitar, epic, clear enunciation, vocal-forward mix, crisp consonants, audiophile, call and response, backing vocals, Maqam Kurd, mood: "somber, torment, night dread"

[Intro | single clean guitar | close-mic'd, plate reverb, short decay]
اعْتَضْتُ مِنْ وَجْهِ خِلِّي بَعْدَ فُرْقَتِهِ كَأْسًا
يُجَرَّعُ مِنْهَا مَا أُجَرَّعُهُ...

[Verse 1 | dark brooding vocals | muted rhythmic guitars and heavy bass]
اعْتَضْتُ مِنْ وَجْهِ خِلِّي بَعْدَ فُرْقَتِهِ كَأْسًا
يُجَرَّعُ مِنْهَا مَا أُجَرَّعُهُ...
كَمْ قَائِلٍ لِي ذُقْتَ الْبَيْنَ قُلْتُ لَهُ
الذَّنْبُ وَاللَّهِ ذَنْبِي لَسْتُ أَدْفَعُهُ...
أَلَا أَقَمْتَ فَكَانَ الرُّشْدُ أَجْمَعُهُ
لَوْ أَنَّنِي يَوْمَ بَانَ الرُّشْدُ أَتْبَعُهُ...
لَوْ أَنَّنِي لَمْ تَقَعْ عَيْنِي عَلَى بَلَدٍ
فِي سَفْرَتِي هَـٰذِهِ إِلَّا وَأَقْطَعُهُ...
إِنِّي لَأَقْطَعُ أَيَّامِي وَأُنْفِدُهَا
بِحَسْرَةٍ مِنْهُ فِي قَلْبِي تُقَطِّعُهُ...

[Chorus | anguished powerful vocals | heavy orchestral swell and distorted guitars — Kurd]
مَا كُنْتُ أَحْسَبُ أَنَّ الدَّهْرَ يَفْجَعُنِي بِهِ
وَلَا أَنَّ بِي الْأَيَّامَ تَفْجَعُهُ...

[Verse 2]
بِمَنْ إِذَا هَجَعَ النُّوَّامُ بِتُّ لَهُ
بِلَوْعَةٍ مِنْهُ لَيْلِي لَسْتُ أَهْجَعُهُ...
لَا يَطْمَئِنُّ لِجَنْبِي مَضْجَعٌ وَكَذَا
لَا يَطْمَئِنُّ لَهُ مُذْ بِنْتُ مَضْجَعُهُ...
حَتَّى جَرَى الْبَيْنُ فِيمَا بَيْنَنَا بِيَدٍ عَسْرَاءَ
تَمْنَعُنِي حَظِّي وَتَمْنَعُهُ...
قَدْ كُنْتُ مِنْ رَيْبِ دَهْرِي جَازِعًا فَرِقًا
فَلَمْ أُوَقَّ ٱلَّذِي قَدْ كُنْتُ أَجْزَعُهُ...

[Chorus]
مَا كُنْتُ أَحْسَبُ أَنَّ الدَّهْرَ يَفْجَعُنِي بِهِ
وَلَا أَنَّ بِي الْأَيَّامَ تَفْجَعُهُ...

[Outro | deep male vocals | clean electric guitar]
قَدْ كُنْتُ مِنْ رَيْبِ دَهْرِي جَازِعًا فَرِقًا
فَلَمْ أُوَقَّ ٱلَّذِي قَدْ كُنْتُ أَجْزَعُهُ...
```
