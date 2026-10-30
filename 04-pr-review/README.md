# 04-pr-review

Companion to part 4 of My Agentic Setup: **Every PR gets an agent review
before a human sees it**.

[Read the post](https://golemnotes.substack.com/p/every-pr-gets-an-agent-review?utm_source=github&utm_medium=referral&utm_campaign=agentic-setup-04)

Sanitized copies of the scripts I use to send PRs to review agents, with tests
that run against fakes. Adapt the paths and the model IDs to your own setup.

## What is here

| File | What it does |
|---|---|
| `bin/review-pr` | Takes a PR URL, goes to your local clone of that repo, and starts an agent with `/review-pr <url>` |
| `bin/review-pr-many-herdr` | Opens a "PR reviews" workspace in herdr with one pane per PR, laid out as a grid, and runs `review-pr` in each |
| `bin/pr-ref` | Turns a URL, `owner/repo#123`, `owner/repo:123` or a bare number into `owner/repo#123` |
| `bin/fmreview-prompt` | Prints the message I send a Firstmate first mate: one read-only review scout per PR, pinned to the reviewer model |
| `charter.md` | The rules every review scout gets: read-only, a local report, what the report covers, which review tools win |
| `tests/run.py` | Tests with a fake agent CLI and a fake herdr |
| `Makefile` | `make test`, `make lint` |

## review-pr

```sh
review-pr https://github.com/acme/api/pull/123
```

It expects your clone at `~/GitHub/acme/api`. Change that with
`REVIEW_PR_ROOT`. The agent is Cursor's CLI (`agent`) by default. Change it
with `REVIEW_PR_AGENT`, which can have more than one word:

```sh
REVIEW_PR_AGENT="claude" review-pr https://github.com/acme/api/pull/123
```

`/review-pr` itself comes from the `pr-review-toolkit` plugin. The script only
starts the agent in the right folder with the right command. The review stays
in the pane. Nothing is posted.

## review-pr-many-herdr

```sh
review-pr-many-herdr \
  https://github.com/acme/api/pull/123 \
  https://github.com/acme/api/pull/124 \
  https://github.com/acme/web/pull/45
```

Needs a running herdr server and `review-pr` on your `PATH`. Each pane is named
`owner/repo#number`, so the border shows the PR, not the agent's name. Five
PRs make a grid of three panes on top and two below.

Two things in it that took a while:

- herdr's `--ratio` is the share the original pane keeps, not the share the new
  pane gets. Carving `n` equal slices means a ratio of `1/n` at each step.
- It reads `herdr status server` into a variable instead of piping it into
  `grep -q`. Under `set -o pipefail`, `grep -q` exits on the first match,
  herdr gets SIGPIPE, and the pipeline fails even though the server is up.

## fmreview-prompt and charter.md

In my setup, `fmreview` is a zsh function that starts a Firstmate home, writes
`charter.md` into it, and sends this message to the first mate. That part
depends on my Firstmate and herdr setup, so here you get the two pieces you can
reuse: the message and the charter.

```sh
fmreview-prompt https://github.com/acme/api/pull/123 acme/web:45
fmreview-prompt --repo acme/api 123 124 125
FMREVIEW_MODEL=openai/your-reviewer fmreview-prompt acme/api#123
```

Put the reviewer on a different vendor than the model that writes your code.

## Test

```sh
make test
```

Needs bash and Python 3. The fake herdr keeps the geometry of every pane, so
the tests check the real layout for 1 to 7 PRs: argument order, equal sizes,
no gaps. They also check URL quoting, PR parsing, and the read-only lines in
the prompt. Nothing connects to GitHub or to your own herdr server. Tested with bash 5.1
and 5.2 on Linux.
