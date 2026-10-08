#!/usr/bin/env bash
# Attach to a persistent agent session on a remote machine.
#
# The agent runs on the VM inside tmux, so it keeps working after you
# disconnect, and the same session is there when you come back, from this
# laptop or another one.
#
#   agent-session.sh my-vm                      # attach, creating it if needed
#   agent-session.sh my-vm --session review     # a second, separate session
#   agent-session.sh my-vm --run 'omp'          # start a command in it
#   agent-session.sh my-vm --list               # what is running over there
#   agent-session.sh my-vm --forward-auth       # so `claude login` can finish
#   agent-session.sh my-vm --gcloud --project <project> --zone <zone>
#
# AGENT_SESSION_HOST, AGENT_SESSION_PROJECT and AGENT_SESSION_ZONE supply the
# defaults, so with them exported every call is just `agent-session.sh --list`.
#
# Detach with Ctrl-b d, or just close the connection: the session survives.
set -euo pipefail

SESSION="agents"
# Ports the agent CLIs listen on for their OAuth callback. Forwarded so the
# browser on this laptop can reach a login running on the VM.
AUTH_PORTS="54545 54546 8976"
FORWARD_AUTH=0
HOST="${AGENT_SESSION_HOST:-}"
RUN=""
LIST=0
USE_GCLOUD=0
PROJECT="${AGENT_SESSION_PROJECT:-${CLOUDSDK_CORE_PROJECT:-}}"
ZONE="${AGENT_SESSION_ZONE:-${CLOUDSDK_COMPUTE_ZONE:-}}"

usage() { sed -n '2,18p' "$0"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --session) SESSION="${2:?--session needs a name}"; shift 2 ;;
    --run)     RUN="${2:?--run needs a command}"; shift 2 ;;
    --list)    LIST=1; shift ;;
    --gcloud)  USE_GCLOUD=1; shift ;;
    --forward-auth) FORWARD_AUTH=1; shift ;;
    --auth-port)    AUTH_PORTS="${2:?--auth-port needs a port}"; shift 2 ;;
    --project) PROJECT="${2:?--project needs a value}"; shift 2 ;;
    --zone)    ZONE="${2:?--zone needs a value}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    -*)        echo "unknown flag: $1" >&2; usage >&2; exit 2 ;;
    *)         HOST="$1"; shift ;;
  esac
done

if [ -z "$HOST" ]; then
  echo "error: no machine given. Name it, or set AGENT_SESSION_HOST" >&2
  echo "  $(basename "$0") my-vm --list" >&2
  exit 2
fi

# tmux does the work; ssh is only the transport. `new-session -A` attaches to
# the session when it exists and creates it otherwise, so one command covers
# both the first connection and every later one.
if [ "$LIST" -eq 1 ]; then
  remote='tmux list-sessions 2>/dev/null || echo "no sessions"'
elif [ -n "$RUN" ]; then
  # The command crosses ssh, the remote shell and tmux, each with its own
  # quoting. base64 is the one encoding that survives all three unchanged.
  encoded="$(printf '%s' "$RUN" | base64 | tr -d '\n')"
  session_q="$(printf %q "$SESSION")"
  remote="tmux new-session -A -d -s ${session_q}; \
          tmux new-window -t ${session_q} \"sh -lc 'eval \\\"\\\$(printf %s ${encoded} | base64 -d)\\\"; exec \\\$SHELL -l'\"; \
          tmux attach -t ${session_q}"
else
  remote="tmux new-session -A -s $(printf %q "$SESSION")"
fi

# Already on the target machine: attach directly. Otherwise gcloud would try
# to ssh the VM to itself, make a stray key there, and fail on permissions the
# VM's own service account does not have.
if [ "$(hostname -s 2>/dev/null)" = "${HOST%%.*}" ]; then
  if [ "$LIST" -eq 1 ]; then
    tmux list-sessions 2>/dev/null || echo "no sessions"
    exit 0
  elif [ -n "$RUN" ]; then
    tmux new-session -A -d -s "$SESSION"
    # shellcheck disable=SC2016  # $SHELL expands in the new window, not here
    tmux new-window -t "$SESSION" "$RUN"'; exec $SHELL -l'
    exec tmux attach -t "$SESSION"
  fi
  exec tmux new-session -A -s "$SESSION"
fi

forward_args=()
if [ "$FORWARD_AUTH" -eq 1 ]; then
  for port in $AUTH_PORTS; do
    forward_args+=(-L "${port}:localhost:${port}")
  done
fi

if [ "$USE_GCLOUD" -eq 1 ]; then
  command -v gcloud >/dev/null 2>&1 || { echo "error: gcloud is not installed" >&2; exit 1; }
  [ -n "$PROJECT" ] || { echo "error: --project is required with --gcloud" >&2; exit 2; }
  [ -n "$ZONE" ] || { echo "error: --zone is required with --gcloud" >&2; exit 2; }
  # IAP: the VM needs no external IP.
  exec gcloud compute ssh "$HOST" \
    --project="$PROJECT" --zone="$ZONE" --tunnel-through-iap \
    -- -t ${forward_args[@]+"${forward_args[@]}"} "$remote"
fi

# -t forces a terminal: without it tmux refuses to attach.
exec ssh -t ${forward_args[@]+"${forward_args[@]}"} "$HOST" "$remote"
