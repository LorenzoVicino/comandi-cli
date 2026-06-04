.PHONY: test install dev

DATA = comandi/data/commands.json

test:
	python3 -m py_compile comandi/cli.py
	COMANDI_FILE="$(DATA)" bin/commands list >/dev/null
	COMANDI_FILE="$(DATA)" bin/commands show ssh-agent >/dev/null
	COMANDI_FILE="$(DATA)" bin/commands print ssh-agent >/dev/null
	COMANDI_FILE="$(DATA)" bin/commands _preview 0 >/dev/null
	COMANDI_FILE="$(DATA)" bin/commands mode ssh-agent | grep -q '^eval$$'
	@echo "All checks passed."

dev:
	pip install -e .

install:
	./install.sh
