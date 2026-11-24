# Remix example

This is a **workflow example**, not a claim that the example is a good remix.
It shows the funnel commands and the shape of a plan with two declared sources.

```bash
# 1. Discover candidates
python3 scripts/remix_cli.py catalog --key Dm --mode minor --limit 8

# 2. Inspect the shortlist
python3 scripts/remix_cli.py songmap suno-0024

# 3. Extract two fragments
python3 scripts/remix_cli.py slice suno-0024 --bars 17-20 --voice Vocal
python3 scripts/remix_cli.py slice suno-0000 --bars 34-37 --voice Ins

# 4. Write plan.json from the template, then score.abc by hand

# 5. Verify
python3 scripts/remix_cli.py remix check score.abc --plan plan.json --require-final-rest
```

The template uses the 15 checker targets plus the `remix` block. Replace the
source ids and bars with the material you actually used; a declared quote that
is not in the score is reported as `not_found`.
