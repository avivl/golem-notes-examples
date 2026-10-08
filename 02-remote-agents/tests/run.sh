#!/usr/bin/env bash
# Tests for agent-session.sh. Nothing here touches your real tmux server or
# needs a VM:
#   - tmux runs on a private socket dir with no config file, and `attach`
#     is turned into a no-op so tests run without a terminal
#   - `ssh` and `gcloud` are fakes that record their arguments; the fake ssh
#     runs the remote command through `sh -c`, the same way a real remote
#     shell would, so the quoting is tested for real
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
script="$here/../agent-session.sh"
work="$(mktemp -d)"
trap 'TMUX_TMPDIR="$work/sock" tmux kill-server 2>/dev/null || true; rm -rf "$work"' EXIT

real_tmux="$(command -v tmux)" || { echo "tmux is required" >&2; exit 1; }
mkdir -p "$work/bin" "$work/sock"

cat > "$work/bin/tmux" <<SHIM
#!/usr/bin/env bash
# No terminal in tests. attach does nothing. new-session -A on an existing
# session would attach, so it does nothing too; otherwise it starts detached.
real="$real_tmux"
args=() name="" new=0 prev=""
for a in "\$@"; do
  [ "\$a" = attach ] && exit 0
  [ "\$a" = new-session ] && new=1
  [ "\$prev" = -s ] && name="\$a"
  prev="\$a"
  [ "\$a" = -A ] || args+=("\$a")
done
if [ "\$new" = 1 ]; then
  [ -n "\$name" ] && "\$real" -f /dev/null has-session -t "\$name" 2>/dev/null && exit 0
  args+=(-d)
fi
exec "\$real" -f /dev/null "\${args[@]}"
SHIM

cat > "$work/bin/ssh" <<'SHIM'
#!/bin/sh
printf '%s\n' "$@" > "$FAKE_LOG"
while [ $# -gt 0 ]; do
  case "$1" in
    -t) shift ;;
    -L) shift 2 ;;
    *) break ;;
  esac
done
shift                       # the host
exec sh -c "$*"
SHIM

cat > "$work/bin/gcloud" <<'SHIM'
#!/bin/sh
printf '%s\n' "$@" > "$FAKE_LOG"
SHIM
chmod +x "$work/bin/"*

export PATH="$work/bin:$PATH" TMUX_TMPDIR="$work/sock" SHELL=/bin/sh FAKE_LOG="$work/log"
unset TMUX AGENT_SESSION_HOST AGENT_SESSION_PROJECT AGENT_SESSION_ZONE CLOUDSDK_CORE_PROJECT CLOUDSDK_COMPUTE_ZONE

pass=0
ok()   { pass=$((pass + 1)); echo "ok   $1"; }
fail() { echo "FAIL $1" >&2; exit 1; }

wait_for() {  # wait_for <file>: the --run job writes it when done
  for _ in $(seq 1 50); do [ -s "$1" ] && return 0; sleep 0.1; done
  return 1
}

this="$(hostname -s)"

# 1. A machine name is required.
if "$script" >/dev/null 2>&1; then fail "no host should fail"; fi
err="$("$script" 2>&1 || true)"
case "$err" in *"no machine given"*) ok "no host gives a clear error" ;; *) fail "no host: $err" ;; esac

# 2. --list when nothing runs, over ssh and locally.
[ "$("$script" my-vm --list)" = "no sessions" ] && ok "--list over ssh with no server"
[ "$("$script" "$this" --list)" = "no sessions" ] && ok "--list locally with no server"

# 3. --run over ssh, with every kind of quote in the command.
out="$work/out-ssh"
"$script" my-vm --session payments --run "printf '%s\n' \"it's \\\"quoted\\\" \\\$HOME and \\\`ticks\\\`\" > $out"
wait_for "$out" || fail "--run over ssh never ran"
# shellcheck disable=SC2016
expected='it'"'"'s "quoted" $HOME and `ticks`'
[ "$(cat "$out")" = "$expected" ] || fail "--run over ssh mangled the command: $(cat "$out")"
ok "--run over ssh keeps quotes, \$ and backticks"

tmux has-session -t payments 2>/dev/null && ok "--run created the named session"
[ "$(tmux list-windows -t payments | wc -l | tr -d ' ')" = 2 ] && ok "--run opened a new window"

# 4. The window stays open after the job finishes.
sleep 0.3
tmux list-panes -s -t payments -F '#{pane_dead}' | grep -qvx 1 && ok "--run leaves a shell in the window"

# 5. --list now shows the session.
"$script" my-vm --list | grep -q '^payments:' && ok "--list shows the session"

# 6. --run locally (the hostname matches), into a second session.
out="$work/out-local"
"$script" "$this" --session billing --run "echo local-ran > $out"
wait_for "$out" || fail "--run locally never ran"
[ "$(cat "$out")" = local-ran ] && ok "--run locally attaches without ssh"
[ "$(tmux list-sessions | wc -l | tr -d ' ')" = 2 ] && ok "two separate sessions"

# 7. Plain connect runs new-session -A, so it works twice.
"$script" my-vm --session payments
"$script" my-vm --session payments
grep -q 'new-session -A -s payments' "$FAKE_LOG" && ok "connecting twice reuses the session"

# 8. --forward-auth forwards the OAuth callback ports.
"$script" my-vm --forward-auth --list >/dev/null
for p in 54545 54546 8976; do grep -qx "$p:localhost:$p" "$FAKE_LOG" || fail "port $p not forwarded"; done
ok "--forward-auth forwards 54545 54546 8976"

# 9. --gcloud needs a project and a zone, and goes through IAP.
if "$script" my-vm --gcloud >/dev/null 2>&1; then fail "--gcloud without project should fail"; fi
ok "--gcloud without --project fails"
"$script" my-vm --gcloud --project my-project --zone my-zone --list
grep -qx -- '--tunnel-through-iap' "$FAKE_LOG" && grep -qx -- '--project=my-project' "$FAKE_LOG" \
  && ok "--gcloud uses IAP with the given project"

# 10. Environment variables replace the arguments.
AGENT_SESSION_HOST=my-vm AGENT_SESSION_PROJECT=p AGENT_SESSION_ZONE=z "$script" --gcloud --list
grep -qx my-vm "$FAKE_LOG" && ok "AGENT_SESSION_* variables work"

echo "$pass passed"
