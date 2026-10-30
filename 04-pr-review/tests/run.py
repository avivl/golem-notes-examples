#!/usr/bin/env python3
"""Tests for the 04-pr-review scripts.

Everything runs against fakes: a fake agent CLI and a fake herdr that keeps
pane geometry. Nothing talks to GitHub, starts an agent, or touches your own
herdr server.
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin")
FAKES = os.path.join(ROOT, "tests", "fakes")

failures = 0
passed = 0


def check(name, cond, detail=""):
    global failures, passed
    if cond:
        passed += 1
        print(f"ok   {name}")
    else:
        failures += 1
        print(f"FAIL {name}" + (f"\n     {detail}" if detail else ""))


def run(cmd, env=None, cwd=None):
    e = dict(os.environ)
    e["PATH"] = FAKES + os.pathsep + BIN + os.pathsep + e["PATH"]
    if env:
        e.update(env)
    return subprocess.run(cmd, env=e, cwd=cwd, capture_output=True, text=True)


# --- pr-ref ------------------------------------------------------------------

cases = [
    (["https://github.com/acme/api/pull/123"], "acme/api#123"),
    (["https://github.com/acme/api/pull/123/files"], "acme/api#123"),
    (["https://github.com/acme/api/pull/123?w=1"], "acme/api#123"),
    (["acme/api#123"], "acme/api#123"),
    (["acme/api:123"], "acme/api#123"),
    (["123", "acme/api"], "acme/api#123"),
]
for args, want in cases:
    r = run([os.path.join(BIN, "pr-ref")] + args)
    check(f"pr-ref {' '.join(args)}", r.returncode == 0 and r.stdout.strip() == want,
          f"rc={r.returncode} out={r.stdout!r}")

r = run([os.path.join(BIN, "pr-ref"), "123"])
check("pr-ref bare number without a repo: empty, success",
      r.returncode == 0 and r.stdout == "")

for bad in ["acme", "https://github.com/acme/api/issues/5", "acme/api#x", ""]:
    r = run([os.path.join(BIN, "pr-ref"), bad])
    check(f"pr-ref rejects {bad!r}", r.returncode == 1)

# --- review-pr -----------------------------------------------------------------

with tempfile.TemporaryDirectory() as tmp:
    clone = os.path.join(tmp, "acme", "api")
    os.makedirs(clone)
    env = {"REVIEW_PR_ROOT": tmp, "REVIEW_PR_AGENT": "agent"}
    url = "https://github.com/acme/api/pull/123"

    r = run([os.path.join(BIN, "review-pr"), url], env=env)
    lines = r.stdout.splitlines()
    check("review-pr runs the agent in the PR's clone",
          r.returncode == 0 and lines[0] == "cwd=" + os.path.realpath(clone),
          r.stdout + r.stderr)
    check("review-pr passes /review-pr <url> as one argument",
          lines[1:] == ["arg=/review-pr " + url], r.stdout)

    # An agent command with words of its own, like a wrapper.
    r = run([os.path.join(BIN, "review-pr"), url],
            env={"REVIEW_PR_ROOT": tmp, "REVIEW_PR_AGENT": "agent --model reviewer"})
    check("review-pr splits REVIEW_PR_AGENT into words",
          r.stdout.splitlines()[1:] == ["arg=--model", "arg=reviewer", "arg=/review-pr " + url],
          r.stdout)

    r = run([os.path.join(BIN, "review-pr"), "https://github.com/acme/web/pull/9"], env=env)
    check("review-pr fails when the clone is missing",
          r.returncode == 1 and "repo directory not found" in r.stderr, r.stderr)

    r = run([os.path.join(BIN, "review-pr"), "https://gitlab.com/acme/api/-/merge_requests/1"], env=env)
    check("review-pr rejects a non-GitHub URL",
          r.returncode == 1 and "not a valid GitHub PR URL" in r.stderr, r.stderr)

    r = run([os.path.join(BIN, "review-pr")], env=env)
    check("review-pr without arguments prints usage",
          r.returncode == 1 and "Usage" in r.stderr)

# --- review-pr-many-herdr --------------------------------------------------------


def launch(urls, down=False):
    tmp = tempfile.mkdtemp()
    env = {"FAKE_LOG": os.path.join(tmp, "log"), "FAKE_STATE": os.path.join(tmp, "state")}
    if down:
        env["FAKE_HERDR_DOWN"] = "1"
    r = run([os.path.join(BIN, "review-pr-many-herdr")] + urls, env=env)
    calls = []
    if os.path.exists(env["FAKE_LOG"]):
        with open(env["FAKE_LOG"]) as f:
            calls = [json.loads(line) for line in f]
    state = {}
    if os.path.exists(env["FAKE_STATE"]):
        with open(env["FAKE_STATE"]) as f:
            state = json.load(f)
    return r, calls, state


def close(a, b):
    return abs(a - b) < 1e-4


for n in range(1, 8):
    urls = [f"https://github.com/acme/api/pull/{100 + i}" for i in range(n)]
    r, calls, state = launch(urls)
    runs = [c for c in calls if c[:2] == ["pane", "run"]]
    renames = [c for c in calls if c[:2] == ["pane", "rename"]]
    splits = [c for c in calls if c[:2] == ["pane", "split"]]

    ok = r.returncode == 0 and len(runs) == n and len(splits) == n - 1
    check(f"{n} PR(s): {n} panes from {n - 1} split(s)", ok, r.stderr)
    if not ok:
        continue

    rects = [state["panes"][c[2]] for c in runs]

    # Row-major: argument order reads left to right, then top to bottom.
    order = sorted(range(n), key=lambda i: (round(rects[i][1], 4), round(rects[i][0], 4)))
    check(f"{n} PR(s): panes read in argument order", order == list(range(n)), str(rects))

    # Every row is the same height, and within a row every pane the same width.
    rows = {}
    for x, y, w, h in rects:
        rows.setdefault(round(y, 4), []).append((w, h))
    heights = {round(h, 4) for row in rows.values() for _, h in row}
    widths_ok = all(len({round(w, 4) for w, _ in row}) == 1 for row in rows.values())
    check(f"{n} PR(s): equal rows and equal panes per row",
          len(heights) == 1 and widths_ok, str(rects))

    # The panes cover the whole workspace, no gaps.
    area = sum(w * h for _, _, w, h in rects)
    check(f"{n} PR(s): panes fill the workspace", close(area, 1.0), str(area))

    labels = [c[3] for c in renames]
    check(f"{n} PR(s): panes are named owner/repo#number",
          labels == [f"acme/api#{100 + i}" for i in range(n)], str(labels))

# A URL with a quote and a query string must reach review-pr unchanged.
tricky = "https://github.com/acme/api/pull/7?note=it's"
r, calls, _ = launch([tricky])
pane_runs = [c for c in calls if c[:2] == ["pane", "run"]]
cmd = pane_runs[0][3] if pane_runs else ""
out = subprocess.run(["sh", "-c", cmd.replace("review-pr ", "printf '%s' ", 1)],
                     capture_output=True, text=True).stdout if cmd else ""
check("the pane command quotes the URL as one shell word", out == tricky, f"{cmd!r} -> {out!r}")

r, calls, _ = launch(["https://github.com/acme/api/pull/1"], down=True)
check("refuses to run without a herdr server",
      r.returncode == 1 and "no herdr server" in r.stderr
      and not any(c[:2] == ["workspace", "create"] for c in calls), r.stderr)

r, calls, _ = launch(["https://github.com/acme/api/pull/1", "not-a-url"])
check("checks every URL before touching herdr", r.returncode == 1 and calls == [], r.stderr)

# --- fmreview-prompt -------------------------------------------------------------

r = run([os.path.join(BIN, "fmreview-prompt"),
         "https://github.com/acme/api/pull/123", "acme/web:45", "--repo", "acme/infra", "7"])
check("fmreview-prompt lists every PR",
      r.returncode == 0 and "- acme/api PR #123" in r.stdout
      and "- acme/web PR #45" in r.stdout and "- acme/infra PR #7" in r.stdout, r.stdout + r.stderr)
check("fmreview-prompt pins the reviewer model",
      "harness omp, model openai-codex/gpt-6.1-sol, effort high" in r.stdout, r.stdout)
check("fmreview-prompt makes the scouts read-only",
      "must not comment, review, approve, request changes, push, or merge" in r.stdout)
check("fmreview-prompt tells the first mate to stop after relaying",
      "then STOP" in r.stdout)

r = run([os.path.join(BIN, "fmreview-prompt"), "acme/api#1"], env={"FMREVIEW_MODEL": "some/other-model"})
check("fmreview-prompt takes the model from FMREVIEW_MODEL", "model some/other-model," in r.stdout)

r = run([os.path.join(BIN, "fmreview-prompt"), "7"])
check("fmreview-prompt asks for --repo on a bare number",
      r.returncode == 2 and "needs --repo" in r.stderr, r.stderr)

r = run([os.path.join(BIN, "fmreview-prompt"), "nonsense"])
check("fmreview-prompt rejects what it cannot parse",
      r.returncode == 2 and "cannot parse" in r.stderr, r.stderr)

r = run([os.path.join(BIN, "fmreview-prompt")])
check("fmreview-prompt needs at least one PR", r.returncode == 2)

print(f"\n{passed} passed, {failures} failed")
sys.exit(1 if failures else 0)
