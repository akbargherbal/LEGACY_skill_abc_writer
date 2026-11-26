.PHONY: test selftest acceptance zip zip-public release check-corpus craft offline-check session13 session14 session16 asset-build asset-stats asset-test measure-session ostris-sync ostris-audit ostris-build ostris-features ostris-priors ostris-idioms ostris-similarity ostris-online ostris-bundle ostris-plan ostris-check ostris-eval suno-build suno-check remix-build remix-verify remix-test remix-offline remix-zip remix-zip-public remix-release clean

CORPUS ?= $(HOME)/Jupyter_Notebooks/OpenCode/arabmaqamrock/datasets/five_stars
DIST := dist
SKILL_NAME := abc-score-writer
VERSION := $(shell python3 -c "import sys; sys.path.insert(0, '02_maqam-score/scripts'); from ostris.contract import SKILL_VERSION; print(SKILL_VERSION)")
SKILL_RELEASE ?= 1.0.1
SESSION_STEPS ?= 40
REMIX_VERSION := $(shell python3 -c "import sys; sys.path.insert(0, '03_abc_remixer/scripts'); from remix.shared import REMIX_VERSION; print(REMIX_VERSION)")
REMIX_DATA := 03_abc_remixer/data/remix
SUNO_PKL ?= data/SUNO_ABC_SCORE_DATASET.pkl
SUNO_DATA ?= data/suno
REMIX_ZIP := $(DIST)/abc_remixer.zip
ZIP := $(DIST)/$(SKILL_NAME).zip
# Raw corpus inputs: fetched on demand with `make ostris-sync`, git-ignored,
# and never copied into the skill bundle (see 02_maqam-score/data/README.md).
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

acceptance:
	python3 analysis/verify_0_4_0.py

zip:
	scripts/package_skill.sh "$(DIST)"

# Public variant: skill code only, no bundled corpus artifacts (licensing, see
# docs/ostris-licensing.md). Reader commands then need explicit --out/--priors.
zip-public:
	scripts/package_skill.sh --public "$(DIST)"

# Build, verify, and archive a versioned release. The unversioned zips stay as
# the "current" aliases; dist/releases/ keeps every version, including 0.2.0.
release: asset-build test selftest acceptance offline-check zip zip-public
	@test -n "$(VERSION)" || { echo "release: cannot read SKILL_VERSION"; exit 1; }
	@mkdir -p "$(DIST)/releases"
	@cp "$(DIST)/$(SKILL_NAME).zip" "$(DIST)/releases/$(SKILL_NAME)-$(SKILL_RELEASE).zip"
	@cp "$(DIST)/$(SKILL_NAME)-public.zip" "$(DIST)/releases/$(SKILL_NAME)-$(SKILL_RELEASE)-public.zip"
	@cd "$(DIST)/releases" && sha256sum "$(SKILL_NAME)-$(SKILL_RELEASE)"*.zip > "SHA256SUMS-$(SKILL_RELEASE).txt"
	@echo "release $(SKILL_RELEASE):"
	@cat "$(DIST)/releases/SHA256SUMS-$(SKILL_RELEASE).txt"

check-corpus:
	python3 analysis/test_checker_corpus.py --corpus "$(CORPUS)"

craft:
	python3 analysis/measure_craft.py --corpus "$(CORPUS)" --out analysis/out

# Build the session drops (skill + input + one-line prompt + agent config).
# session-13/14 are the 0.9.0 line-workflow pilots, pinned to the archived docs
# so they stay reproducible after 1.0 became the default.
session13: zip
	SKILL_DOC=SKILL-v0.9.md COMPOSER_DOC=composer-v0.9.md \
	SESSION_NAME=session-13 SESSION_STEPS=40 scripts/package_session.sh "$(DIST)"

session14: zip
	SKILL_DOC=SKILL-v0.9.md COMPOSER_DOC=composer-v0.9.md \
	SESSION_NAME=session-14 SESSION_STEPS=$(SESSION_STEPS) scripts/package_session.sh "$(DIST)"

# Session 16: the 1.0 whole-draft loop in a clean room, low thinking.
session16:
	SESSION_VARIANT=low SESSION_NAME=session-16 SESSION_STEPS=100 \
	scripts/package_session.sh "$(DIST)"

# Build the offline phrase-level asset index from the 670-score SUNO store.
asset-build:
	python3 02_maqam-score/scripts/asset_bank.py build \
		--songs 03_abc_remixer/data/remix/songs \
		--out 02_maqam-score/data/assets/assets.jsonl.gz \
		--meta 02_maqam-score/data/assets/assets.meta.json --cells

asset-stats:
	python3 02_maqam-score/scripts/asset_bank.py stats

asset-test:
	cd 02_maqam-score && python3 -m unittest tests.test_asset_bank tests.test_verify_loans -v

# Measure an exported session against the 10x budget.
SESSION ?= analysis/eval/inbox/deepseek_session_11/opencode_session_11.json
measure-session:
	python3 analysis/measure_session.py "$(SESSION)" --score "$(SCORE)"

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

suno-build:
	python3 tools/build_suno_library.py --pkl $(SUNO_PKL) --out $(SUNO_DATA)

suno-check:
	python3 tools/build_suno_library.py --pkl $(SUNO_PKL) --out $(SUNO_DATA) --check

remix-build: suno-build
	python3 03_abc_remixer/scripts/remix_cli.py library build \
		--dataset suno --data $(SUNO_DATA) --out $(REMIX_DATA)

remix-verify:
	python3 03_abc_remixer/scripts/remix_cli.py library verify

remix-test:
	cd 03_abc_remixer && python3 -m unittest discover -s tests -t . -v

remix-zip:
	scripts/package_remixer.sh "$(DIST)"

remix-zip-public:
	scripts/package_remixer.sh --public "$(DIST)"

remix-release: remix-test remix-verify remix-zip remix-zip-public
	@test -n "$(REMIX_VERSION)" || { echo "remix-release: cannot read REMIX_VERSION"; exit 1; }
	@mkdir -p "$(DIST)/releases"
	@cp "$(DIST)/abc_remixer.zip" "$(DIST)/releases/abc_remixer-$(REMIX_VERSION).zip"
	@if [ -f "$(DIST)/abc_remixer-public.zip" ]; then \
		cp "$(DIST)/abc_remixer-public.zip" "$(DIST)/releases/abc_remixer-$(REMIX_VERSION)-public.zip"; \
	fi
	@cd "$(DIST)/releases" && sha256sum "abc_remixer-$(REMIX_VERSION)"*.zip > "SHA256SUMS-remixer-$(REMIX_VERSION).txt"
	@echo "remix release $(REMIX_VERSION):"
	@cat "$(DIST)/releases/SHA256SUMS-remixer-$(REMIX_VERSION).txt"

remix-offline:
	@tmp=$$(mktemp -d); trap 'rm -rf "$$tmp"' EXIT; \
	python3 03_abc_remixer/scripts/remix_cli.py catalog --limit 3 --ledger "$$tmp/ledger" >/dev/null; \
	python3 03_abc_remixer/scripts/remix_cli.py songmap suno-0024 --ledger "$$tmp/ledger" >/dev/null; \
	python3 03_abc_remixer/scripts/remix_cli.py slice suno-0024 --bars 34-37 --ledger "$$tmp/ledger" >/dev/null; \
	python3 03_abc_remixer/scripts/remix_cli.py motif-find --intervals "0,-2,0,-2" --limit 2 --ledger "$$tmp/ledger" >/dev/null; \
	python3 03_abc_remixer/scripts/remix_cli.py budget --ledger "$$tmp/ledger" >/dev/null; \
	echo "remix offline: PASS"

clean:
	find . -path ./.git -prune -o -name '__pycache__' -type d -exec rm -rf {} +
	rm -f $(DIST)/*.tmp
