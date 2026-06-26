.PHONY: test install dev

FIXTURE = tests/fixture.json

test:
	python3 -m py_compile comandi/cli.py
	COMANDI_FILE="$(FIXTURE)" bin/commands list >/dev/null
	COMANDI_FILE="$(FIXTURE)" bin/commands show test-cmd >/dev/null
	COMANDI_FILE="$(FIXTURE)" bin/commands show test-cmd | grep -q "Keywords:    comando1"
	COMANDI_FILE="$(FIXTURE)" bin/commands run --action run comando1 | grep -q '^hello$$'
	COMANDI_FILE="$(FIXTURE)" bin/commands shell-init | grep -q '^comando1() {'
	COMANDI_FILE="$(FIXTURE)" bash -c 'eval "$$(bin/commands shell-init)"; comando1' | grep -q '^hello$$'
	COMANDI_FILE="$(FIXTURE)" bash -c 'eval "$$(bin/commands shell-init)"; use_test; test "$$TEST" = "1"'
	cp "$(FIXTURE)" /tmp/commands-cli-keywords.json
	COMANDI_FILE="/tmp/commands-cli-keywords.json" bin/commands keywords test-cmd --add comando2 | grep -q "test-cmd: comando1, comando2"
	COMANDI_FILE="/tmp/commands-cli-keywords.json" bin/commands shell-init | grep -q '^comando2() {'
	COMANDI_FILE="$(FIXTURE)" bin/commands show param-cmd | grep -q "env: optional, default=staging, choices=dev, staging, prod"
	COMANDI_FILE="$(FIXTURE)" bin/commands show param-cmd | grep -q "service: required"
	COMANDI_FILE="$(FIXTURE)" bin/commands show param-cmd | grep -q "token: optional, secret"
	COMANDI_FILE="$(FIXTURE)" bin/commands print test-cmd >/dev/null
	COMANDI_FILE="$(FIXTURE)" bin/commands _preview 0 >/dev/null
	COMANDI_FILE="$(FIXTURE)" bin/commands mode test-eval | grep -q '^eval$$'
	@if COMANDI_FILE="tests/invalid-params.json" bin/commands list 2>/tmp/commands-cli-invalid-params.err; then echo "Expected invalid params to fail"; exit 1; fi
	grep -q "Error: Invalid params for 'bad-param.env': required must be true or false" /tmp/commands-cli-invalid-params.err
	@if COMANDI_FILE="$(FIXTURE)" bin/commands add bad-keyword --keyword "bad-key" --cmd "echo bad" 2>/tmp/commands-cli-invalid-keyword.err; then echo "Expected invalid keyword to fail"; exit 1; fi
	grep -q "keyword must match" /tmp/commands-cli-invalid-keyword.err
	@if COMANDI_FILE="$(FIXTURE)" bin/commands add --cmd "echo missing" 2>/tmp/commands-cli-add-no-name.err; then echo "Expected add without name to fail"; exit 1; fi
	grep -q "Error: Command name is required" /tmp/commands-cli-add-no-name.err
	@if COMANDI_FILE="$(FIXTURE)" bin/commands add missing-cmd 2>/tmp/commands-cli-add-no-cmd.err; then echo "Expected add without --cmd to fail"; exit 1; fi
	grep -q "Error: --cmd is required when stdin is not a TTY" /tmp/commands-cli-add-no-cmd.err
	@echo "All checks passed."

dev:
	pip install -e .

install:
	./install.sh
