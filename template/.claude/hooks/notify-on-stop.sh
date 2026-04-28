#!/usr/bin/env bash
# notify-on-stop.sh
# Stop event hook
# Surfaces a desktop notification (or terminal bell fallback) when Claude
# finishes responding. Useful when running Claude in a tab you've moved away from.
#
# Suppress with CLAUDE_NOTIFY_QUIET=1.

set -euo pipefail

if [[ "${CLAUDE_NOTIFY_QUIET:-0}" == "1" ]]; then
  exit 0
fi

title="${CLAUDE_PROJECT_NAME:-Claude Code}"
body="Done — your turn."

case "$(uname -s)" in
  Darwin)
    if command -v osascript >/dev/null 2>&1; then
      osascript -e "display notification \"$body\" with title \"$title\"" 2>/dev/null || printf '\a'
    else
      printf '\a'
    fi
    ;;
  Linux)
    if command -v notify-send >/dev/null 2>&1; then
      notify-send "$title" "$body" 2>/dev/null || printf '\a'
    else
      printf '\a'
    fi
    ;;
  *)
    printf '\a'
    ;;
esac

exit 0
