PYTHON ?= python

.PHONY: test validate sandbox bench smoke
test:
	$(PYTHON) -m pytest -q

validate:
	$(PYTHON) bench/validate.py bench/tasks

sandbox:
	docker build -t sandbox:py312 .

bench: sandbox
	$(PYTHON) bench/validate.py bench/tasks --backend docker
	$(PYTHON) bench/run.py --agent single --tasks bench/tasks --n 3

smoke:
	$(PYTHON) bench/run.py --agent reference --backend local --tasks bench/tasks --n 3
	$(PYTHON) bench/run.py --agent noop --backend local --tasks bench/tasks --n 1
