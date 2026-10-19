#!/usr/bin/env python3
"""Tests for remote-tint.zsh.

Each case starts an interactive zsh in a pseudo-terminal, sources
remote-tint.zsh, and runs one command against fake `ssh` and `herdr`
binaries. It then checks which escape sequences reached the terminal.
No Ghostty, no network, no real hosts. Your own shell config is not loaded.
"""
import os
import pty
import select
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TINT = os.path.join(os.path.dirname(HERE), "remote-tint.zsh")

FAKE = """#!/bin/sh
echo "FAKE $(basename "$0") $*"
exit "${FAKE_RC:-0}"
"""


def tint(color, label):
    return f"\x1b]11;{color}\x07\x1b]2;REMOTE: {label}\x07".encode()


RESET = b"\x1b]111\x07"
PURPLE = "#1e1033"


def run(command, term="xterm-ghostty", pre="", env_extra=None):
    """Run `command` in an interactive zsh on a pty; return all output bytes."""
    env = {
        "PATH": f"{BIN}:/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
        "HOME": HOME,
        "ZDOTDIR": HOME,
        "TERM": term,
    }
    env.update(env_extra or {})
    script = f"{pre}\nsource {TINT}\n{command}\nprint -r -- RC=$?"
    pid, fd = pty.fork()
    if pid == 0:
        os.execve(shutil.which("zsh"), ["zsh", "-f", "-i", "-c", script], env)
    out = b""
    while True:
        r, _, _ = select.select([fd], [], [], 10)
        if not r:
            break
        try:
            chunk = os.read(fd, 4096)
        except OSError:
            break
        if not chunk:
            break
        out += chunk
    os.waitpid(pid, 0)
    return out


CASES = [
    # (name, command, expect tint label or None, extra kwargs, extra checks)
    ("plain host", "ssh home", "home", {}),
    ("-p 22 takes the next word", "ssh -p 22 home", "home", {}),
    ("-p22 carries its value", "ssh -p22 home", "home", {}),
    ("-o takes the next word", "ssh -o ConnectTimeout=5 home", "home", {}),
    ("-v is not a value option", "ssh -v home", "home", {}),
    ("-- then host", "ssh -- home", "home", {}),
    ("user@, domain and -ts are dropped from the label",
     "ssh me@home-ts.example.dev", "home", {}),
    ("remote command: no tint", "ssh home uptime", None, {}),
    ("-N (no shell): no tint", "ssh -N home", None, {}),
    ("-T (no tty): no tint", "ssh -T home", None, {}),
    ("-fN combined: no tint", "ssh -fN home", None, {}),
    ("no host: no tint", "ssh -V", None, {}),
    ("not Ghostty: no tint", "ssh home", None, {"term": "xterm-256color"}),
    ("Ghostty detected by GHOSTTY_RESOURCES_DIR", "ssh home", "home",
     {"term": "xterm-256color", "env_extra": {"GHOSTTY_RESOURCES_DIR": "/x"}}),
    ("piped output: no tint", "ssh home | cat", None, {}),
    ("herdr --remote tints", "herdr --remote home-ts", "home", {}),
    ("herdr --remote with --session", "herdr --remote home-ts --session agents",
     "home", {}),
    ("local herdr: no tint", "herdr session list", None, {}),
    ("hr-home tints", "hr-home", "home", {}),
]


def main():
    global BIN, HOME
    if not shutil.which("zsh"):
        print("zsh not found")
        return 1
    tmp = tempfile.mkdtemp(prefix="remote-tint-test.")
    BIN = os.path.join(tmp, "bin")
    HOME = os.path.join(tmp, "home")
    os.makedirs(BIN)
    os.makedirs(HOME)
    for name in ("ssh", "herdr"):
        p = os.path.join(BIN, name)
        with open(p, "w") as f:
            f.write(FAKE)
        os.chmod(p, 0o755)

    failed = 0

    def check(name, ok, out):
        nonlocal failed
        if ok:
            print(f"ok    {name}")
        else:
            failed += 1
            print(f"FAIL  {name}\n      output: {out!r}")

    for name, command, label, kw in CASES:
        out = run(command, **kw)
        ran = b"FAKE " in out and b"RC=0" in out
        if label:
            ok = ran and tint(PURPLE, label) in out and RESET in out
            # The reset must come after the command's output.
            ok = ok and out.index(RESET) > out.index(b"FAKE ")
        else:
            ok = ran and b"\x1b]11;" not in out and RESET not in out
        check(name, ok, out)

    # The exit code passes through, and the reset still runs on failure.
    out = run("ssh home", env_extra={"FAKE_RC": "3"})
    check("failed ssh: exit code kept, tint reset",
          tint(PURPLE, "home") in out and RESET in out and b"RC=3" in out, out)

    # Per-host colors and the default for unknown hosts.
    pre = "typeset -gA REMOTE_TINT_COLORS=(work '#102a18'); REMOTE_TINT_DEFAULT='#2a2010'"
    out = run("ssh work", pre=pre)
    check("custom color per host", tint("#102a18", "work") in out, out)
    out = run("ssh elsewhere", pre=pre)
    check("default color for an unknown host",
          tint("#2a2010", "elsewhere") in out, out)

    # Arguments reach the real command unchanged.
    out = run("ssh -p 2222 -o 'ProxyCommand=x %h' home")
    check("arguments pass through unchanged",
          b"FAKE ssh -p 2222 -o ProxyCommand=x %h home" in out, out)

    shutil.rmtree(tmp, ignore_errors=True)
    total = len(CASES) + 4
    print(f"\n{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
