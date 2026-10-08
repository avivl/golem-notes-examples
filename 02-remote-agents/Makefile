.PHONY: test lint
test:
	@tests/run.sh

lint:
	@bash -n agent-session.sh tests/run.sh
	@command -v shellcheck >/dev/null && shellcheck agent-session.sh tests/run.sh || echo "shellcheck not installed, skipped"
