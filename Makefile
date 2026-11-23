.PHONY: test selftest zip check-corpus clean

CORPUS ?= $(HOME)/Jupyter_Notebooks/OpenCode/arabmaqamrock/datasets/five_stars
DIST := dist
ZIP := $(DIST)/02_maqam-score.zip

test:
	cd 02_maqam-score && python3 -m unittest discover -s tests -v

selftest:
	cd 02_maqam-score && bash scripts/selftest.sh

zip:
	mkdir -p $(DIST)
	rm -f $(ZIP)
	zip -r $(ZIP) 02_maqam-score -x '*.pyc' -x '*__pycache__*'

check-corpus:
	python3 analysis/test_checker_corpus.py --corpus "$(CORPUS)"

clean:
	find . -path ./.git -prune -o -name '__pycache__' -type d -exec rm -rf {} +
	rm -f $(DIST)/*.tmp
