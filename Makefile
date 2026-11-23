.PHONY: test selftest zip zip-public check-corpus offline-check ostris-sync ostris-audit ostris-build ostris-features ostris-priors ostris-idioms ostris-similarity ostris-online ostris-bundle ostris-plan ostris-check ostris-eval clean

CORPUS ?= $(HOME)/Jupyter_Notebooks/OpenCode/arabmaqamrock/datasets/five_stars
DIST := dist
ZIP := $(DIST)/02_maqam-score.zip
OSTRIS_CACHE ?= analysis/out/ostris/source
OSTRIS_OUT ?= analysis/out/ostris
MANIFEST ?= song.json
PLAN_OUT ?= plans/song
SCORE ?= score.abc
REPORT ?= report.json
RUNS ?= runs

test:
	cd 02_maqam-score && python3 -m unittest discover -s tests -v

selftest:
	cd 02_maqam-score && bash scripts/selftest.sh

zip:
	mkdir -p $(DIST)
	rm -f $(ZIP)
	zip -r $(ZIP) 02_maqam-score -x '*.pyc' -x '*__pycache__*' \
		-x '02_maqam-score/data/README.md'

# Public variant: skill code only, no bundled corpus artifacts (licensing, see
# docs/ostris-licensing.md). Reader commands then need explicit --out/--priors.
zip-public:
	mkdir -p $(DIST)
	rm -f $(DIST)/02_maqam-score-public.zip
	zip -r $(DIST)/02_maqam-score-public.zip 02_maqam-score \
		-x '*.pyc' -x '*__pycache__*' -x '02_maqam-score/data/*'

check-corpus:
	python3 analysis/test_checker_corpus.py --corpus "$(CORPUS)"

ostris-sync:
	@test -n "$(DATA_ROOT)" || { echo "set DATA_ROOT=gs://<bucket> or a local data root"; exit 1; }
	python3 02_maqam-score/scripts/ostris_cli.py sync --data-root "$(DATA_ROOT)" --cache "$(OSTRIS_CACHE)"

ostris-bundle:
	scripts/bundle_data.sh "$(OSTRIS_OUT)"

offline-check:
	@tmp=$$(mktemp -d); trap 'rm -rf "$$tmp"' EXIT; \
	printf '%s\n' '{"title":"Offline check","key":"C","tempo":120,"meter":"4/4","bars":8,"sections":["intro","verse 1"]}' > "$$tmp/song.json"; \
	python3 02_maqam-score/scripts/ostris_cli.py exemplar --function cadence --bars 2 >/dev/null; \
	python3 02_maqam-score/scripts/ostris_cli.py plan --manifest "$$tmp/song.json" --out "$$tmp/plans" >/dev/null; \
	python3 02_maqam-score/scripts/ostris_cli.py similarity --score 02_maqam-score/example/score.abc --json >/dev/null; \
	python3 02_maqam-score/scripts/ostris_cli.py check 02_maqam-score/example/score.abc --plan 02_maqam-score/example/plan.json --json >/dev/null; \
	echo "offline corpus tools: PASS (bundled defaults, no network, no flags)"

ostris-audit:
	python3 02_maqam-score/scripts/ostris_cli.py audit --cache "$(OSTRIS_CACHE)" --out "$(OSTRIS_OUT)"

ostris-build:
	python3 02_maqam-score/scripts/ostris_cli.py build --cache "$(OSTRIS_CACHE)" --out "$(OSTRIS_OUT)" --require-contract

ostris-features:
	python3 02_maqam-score/scripts/ostris_cli.py features --cache "$(OSTRIS_CACHE)" --out "$(OSTRIS_OUT)" --require-contract

ostris-priors:
	python3 02_maqam-score/scripts/ostris_cli.py priors --out "$(OSTRIS_OUT)" --require-contract --strict

ostris-idioms:
	python3 02_maqam-score/scripts/ostris_cli.py idioms --out "$(OSTRIS_OUT)" --strict

ostris-similarity:
	python3 02_maqam-score/scripts/ostris_cli.py similarity --out "$(OSTRIS_OUT)" --build

ostris-online: ostris-build ostris-priors ostris-idioms ostris-similarity
	python3 02_maqam-score/scripts/ostris_cli.py eval --cache "$(OSTRIS_CACHE)" --out "$(OSTRIS_OUT)" --build-split --strict

ostris-plan:
	python3 02_maqam-score/scripts/ostris_cli.py plan --manifest "$(MANIFEST)" \
		--priors "$(OSTRIS_OUT)/priors/priors.json" --out "$(PLAN_OUT)" --strict

ostris-check:
	python3 02_maqam-score/scripts/ostris_cli.py check "$(SCORE)" \
		--plan "$(PLAN_OUT)/skill_plan.json" --out "$(OSTRIS_OUT)" \
		--report "$(REPORT)" --require-final-rest

ostris-eval:
	python3 02_maqam-score/scripts/ostris_cli.py eval --runs "$(RUNS)" --out "$(OSTRIS_OUT)" --strict

clean:
	find . -path ./.git -prune -o -name '__pycache__' -type d -exec rm -rf {} +
	rm -f $(DIST)/*.tmp
