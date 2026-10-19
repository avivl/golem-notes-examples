# Tint the Ghostty background and title while in an interactive remote session
# (ssh, herdr --remote, hr-home), so a remote shell never looks like a local one.
# Reset uses OSC 111, which returns to the configured theme background.
#
# Source it from ~/.zshrc. Override colors by defining these before this file
# is sourced:
#   typeset -gA REMOTE_TINT_COLORS=(home '#1e1033' work '#102a18')
#   REMOTE_TINT_DEFAULT='#2a2010'

(( ${+REMOTE_TINT_COLORS} )) || typeset -gA REMOTE_TINT_COLORS=(home '#1e1033')
: ${REMOTE_TINT_DEFAULT:=#1e1033}

# Host as typed -> short label: no user@, no domain suffix, no trailing -ts.
_remote_tint_label() {
  local host=${1##*@}
  host=${host%%.*}
  print -r -- "${host%-ts}"
}

# _remote_tint_run <host> <cmd...>
# Tints only for an interactive shell in Ghostty with a tty on stdout.
# Escape sequences go to /dev/tty so piped output stays clean.
_remote_tint_run() {
  local label color
  label=$(_remote_tint_label "$1")
  shift

  if [[ ! -o interactive || ! -t 1 ]] \
    || [[ $TERM != xterm-ghostty && -z $GHOSTTY_RESOURCES_DIR ]]; then
    "$@"
    return $?
  fi

  color=${REMOTE_TINT_COLORS[$label]:-$REMOTE_TINT_DEFAULT}
  local rc=0
  {
    printf '\e]11;%s\a\e]2;REMOTE: %s\a' "$color" "$label" >/dev/tty
    "$@"
    rc=$?
  } always {
    printf '\e]111\a' >/dev/tty
  }
  return $rc
}

ssh() {
  local host="" arg opt rest
  local i=1 no_tint=0
  local value_opts="BbcDEeFIiJLlmOopQRSWw"
  local passive_opts="NWOGQVTf"  # no interactive login shell
  local j

  while (( i <= $# )); do
    arg=${@[i]}
    i=$(( i + 1 ))
    if [[ $arg == -- ]]; then
      host=${@[i]-}
      i=$(( i + 1 ))
      break
    elif [[ $arg == -?* ]]; then
      rest=${arg#-}
      for (( j = 1; j <= ${#rest}; j++ )); do
        opt=${rest[j]}
        [[ $passive_opts == *$opt* ]] && no_tint=1
        if [[ $value_opts == *$opt* ]]; then
          # "-p 22" takes the next word; "-p22" carries its value.
          (( j == ${#rest} )) && i=$(( i + 1 ))
          break
        fi
      done
    else
      host=$arg
      break
    fi
  done

  # Anything after the host is a remote command: run untinted.
  if [[ -z $host ]] || (( no_tint || i <= $# )); then
    command ssh "$@"
    return $?
  fi

  _remote_tint_run "$host" command ssh "$@"
}

herdr() {
  if [[ $1 == --remote && -n $2 ]]; then
    _remote_tint_run "$2" command herdr "$@"
  else
    command herdr "$@"
  fi
}

# Attach to the home laptop's Herdr (detach: Ctrl+B then Q).
# home-ts is an ssh config Host entry; change it to yours.
hr-home() {
  herdr --remote ${HR_HOME_HOST:-home-ts} "$@"
}
