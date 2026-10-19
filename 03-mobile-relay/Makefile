.PHONY: test lint
test:
	@python3 tests/run.py

lint:
	@zsh -n remote-tint.zsh
	@python3 -m json.tool tailscale-policy.json >/dev/null && echo "remote-tint.zsh and tailscale-policy.json parse"
