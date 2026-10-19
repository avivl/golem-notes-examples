# 03-mobile-relay

Companion to part 3 of My Agentic Setup: **My agents on two laptops, controlled
from one phone app**.

The phone side of that post is
[herdr-mobile-relay](https://github.com/0cv/herdr-mobile-relay), a third-party
Herdr plugin with its own setup wizard. Follow its docs for that part. This
folder has the two small pieces around it that you can use on their own.

## What is here

| File | What it does |
|---|---|
| `remote-tint.zsh` | Tints the Ghostty background and sets a `REMOTE: <host>` title while you are in an interactive `ssh` or `herdr --remote` session, and resets both when you leave |
| `tailscale-policy.json` | A Tailscale policy that allows one thing: your devices to port 22 on machines tagged `tag:home`. Everything else is denied |
| `tests/run.py` | Tests for `remote-tint.zsh` with fake `ssh` and `herdr`, in a pseudo-terminal |
| `Makefile` | `make test`, `make lint` |

## remote-tint.zsh

Add it to `~/.zshrc`:

```sh
source /path/to/remote-tint.zsh
```

Then `ssh home` turns the background deep purple until you exit. Colors per
host, set before the `source` line:

```sh
typeset -gA REMOTE_TINT_COLORS=(home '#1e1033' build '#102a18')
REMOTE_TINT_DEFAULT='#2a2010'   # any other host
```

The label is the host as you typed it, without `user@`, the domain, or a
trailing `-ts`. So `me@home-ts.example.dev` gets the `home` color.

It tints only when it makes sense:

- `ssh host` and `herdr --remote host` tint.
- `ssh host uptime` (a remote command), `ssh -N`, `ssh -T`, `ssh -f` don't,
  because there is no interactive shell to tint.
- Outside Ghostty, or with output going to a pipe, it does nothing.
- The escape codes go to `/dev/tty`, so they never end up in piped output.
- The reset runs in a zsh `always` block, so it also runs when ssh fails.

`hr-home` is a shortcut for `herdr --remote home-ts`. `home-ts` is a `Host`
entry in `~/.ssh/config`. Change it, or set `HR_HOME_HOST`.

Inside Herdr, the tint shows only where Herdr doesn't paint its own panel
colors.

## tailscale-policy.json

The default Tailscale policy lets every device reach every other device. This
one lets your own devices reach port 22 on machines tagged `tag:home`, and
nothing else. Traffic into an untagged machine, such as a laptop that holds
work credentials, is denied.

1. In the Tailscale admin console, open **Access controls**, replace the
   policy with this file, and save.
2. Tag the one machine that should accept SSH: **Machines**, its **...** menu,
   **Edit ACL tags**, add `tag:home`. Do this after saving the policy, because
   the tag has to exist first.
3. Check it. From another device: `ssh <home-machine> hostname` works. From the
   home machine: `nc -vz -G 3 <other-device> 22` fails.

`tailscale ping` may still answer between devices. Ping is not covered by the
policy.

On the machines that should never accept connections, also turn on Shields Up
(`tailscale set --shields-up=true`) and keep their SSH server off. The policy
is one lock; those are two more.

## Test

```sh
make test
```

Needs zsh and Python 3. The tests run an interactive `zsh -f` in a
pseudo-terminal, so your own zsh config is not loaded, and they use fake
`ssh` and `herdr` binaries, so nothing connects anywhere. Tested with zsh 5.9
on Linux.

The policy file is checked only for valid JSON here. Tailscale checks the rest
when you save it.
