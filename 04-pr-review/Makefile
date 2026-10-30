.PHONY: test lint
test:
	@python3 tests/run.py

lint:
	@for f in bin/*; do bash -n "$$f" || exit 1; done
	@if command -v shellcheck >/dev/null; then shellcheck bin/*; fi
	@echo "bin/* parse"
