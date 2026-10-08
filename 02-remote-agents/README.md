# 02-remote-agents

Companion to part 2 of My Agentic Setup: **Close the laptop, the agent keeps working**.

One script that puts you in a tmux session on a remote machine. The agent runs
there, so it keeps working when you close the laptop, and you get the same
session back from any laptop.

## What is here

| File | What it does |
|---|---|
| `agent-session.sh` | Attach to (or create) a tmux session on a remote machine, over ssh or `gcloud compute ssh` with IAP |
| `tests/run.sh` | Tests with a private tmux socket and fake `ssh`/`gcloud`. No VM needed, and it never touches your own tmux server |
| `Makefile` | `make test`, `make lint` |

## Use it

You need ssh access to a Linux machine with tmux installed. Copy the script
somewhere on your PATH, then:

```sh
agent-session.sh my-vm                        # attach, or create the session
agent-session.sh my-vm --list                 # what is running over there
agent-session.sh my-vm --session review       # a second, separate session
agent-session.sh my-vm --run 'omp "audit the auth module"'   # start a job
agent-session.sh my-vm --forward-auth         # so `claude login` can finish
```

On GCP, with a VM that has no external IP:

```sh
agent-session.sh my-vm --gcloud --project <project> --zone <zone>
```

Set the defaults once and stop typing them:

```sh
export AGENT_SESSION_HOST=my-vm
export AGENT_SESSION_PROJECT=<project>
export AGENT_SESSION_ZONE=<zone>

agent-session.sh --gcloud --list
```

Detach with `Ctrl-b d`, or just close the laptop. Run the same command later,
from this laptop or another one, and you are back where you left off.

## Things worth knowing

- **Logins.** An agent CLI on the VM waits for its OAuth callback on the VM's
  `localhost`. `--forward-auth` forwards ports 54545, 54546 and 8976 back to
  your laptop so the browser can reach it. `--auth-port` changes the list.
- **Copy login links from a plain terminal.** A boxed TUI panel wraps the URL,
  and a cut-off URL fails with `Unknown scope`.
- **`--run` quoting.** The command goes through ssh, the remote shell and tmux.
  The script base64-encodes it on your side and decodes it on the VM, so
  quotes, `$` and backticks arrive as you typed them.
- **Running it on the VM itself** attaches locally instead of ssh-ing to
  itself.
- **`--run` keeps the window open** after the command exits, so the result is
  still on screen when you come back.
- **`command not found` inside the session** after installing a tool: the tmux
  server kept the old PATH. `tmux kill-server`, then reconnect.
- **Memory.** A 1 GB VM is too small for agent CLIs. Mine got killed while
  generating shell completions.

## Test

```sh
make test
```

Needs bash and tmux. Tested with tmux 3.4 on Linux; also checked once against a
real sshd on localhost.
