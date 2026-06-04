.PHONY: test install dev

FIXTURE = tests/fixture.json

test:
	python3 -m py_compile comandi/cli.py
	COMANDI_FILE="$(FIXTURE)" bin/commands list >/dev/null
	COMANDI_FILE="$(FIXTURE)" bin/commands show test-cmd >/dev/null
	COMANDI_FILE="$(FIXTURE)" bin/commands print test-cmd >/dev/null
	COMANDI_FILE="$(FIXTURE)" bin/commands _preview 0 >/dev/null
	COMANDI_FILE="$(FIXTURE)" bin/commands mode test-eval | grep -q '^eval$$'
	@echo "All checks passed."

dev:
	pip install -e .

install:
	./install.sh
