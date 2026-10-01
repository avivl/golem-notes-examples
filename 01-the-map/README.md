# 01: One set of agent instructions for every tool

From [Part 1 of My Agentic Setup](https://golemnotes.substack.com) (link when published).

Every coding agent reads its global instructions from a different file:
`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.pi/agent/AGENTS.md`, and so on.
Copy them by hand and they drift. This folder is a small working version of how
I fixed that: write the rules once as fragments, compile one flat `AGENTS.md`
per profile, and symlink it into every tool's path.

## Try it

Needs `make` and `bash`. Nothing here touches your real home unless you ask.

```sh
make build              # compile build/personal/AGENTS.md
make deploy             # symlink it into ./fake-home, all 7 tool paths
ls -la fake-home/.codex # AGENTS.md -> .../build/personal/AGENTS.md
make PROFILE=work build # the work profile adds 50-work-only.md
make clean              # remove build/ and fake-home/
```

See the drift check fail:

```sh
make build
echo "- a new rule" >> fragments/10-voice.md
make check   # check: build/personal/AGENTS.md is out of date. Run: make build
```

## Layout

| Path | What it is |
|---|---|
| `fragments/*.md` | The rules, one topic per file. Edit these. |
| `machines/<profile>.txt` | Which fragments a profile gets, in order. |
| `build/<profile>/AGENTS.md` | Generated. Never edit it. |
| `githooks/pre-commit` | Runs `make check`, so a stale build can't be committed. |

## Why flat files

Codex, Pi and Cursor don't expand any include syntax. So the modular part lives
in the source, and every tool gets one plain file.

## Using it for real

1. Copy this folder into your own dotfiles repo.
2. Replace the sample fragments with your rules.
3. Back up any real instruction files you already have. `deploy` skips a real
   file in the way instead of overwriting it, and tells you which one.
4. `make deploy TARGET_HOME=$HOME`
5. Optional: `git config core.hooksPath <path-to-this-folder>/githooks`

After that, edit a fragment and run `make build`. Every tool picks up the change
in its next session, because they all point at the same file.
