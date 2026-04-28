#!/usr/bin/env bash
# block-dangerous-bash.sh
# PreToolUse hook on Bash
# Exit 2 = block + show stderr to Claude.

set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "block-dangerous-bash: jq not installed — skipping (install: brew install jq)" >&2
  exit 0
fi

input="$(cat)"
command="$(echo "$input" | jq -r '.tool_input.command // empty')"

if [[ -z "$command" ]]; then
  exit 0
fi

# Pattern -> human-readable reason
# shellcheck disable=SC2016  # $HOME inside single quotes is intentional (regex literal)
declare -A patterns=(
  ['rm[[:space:]]+-rf?[[:space:]]+/(\s|$)']='rm -rf on root'
  ['rm[[:space:]]+-rf?[[:space:]]+/(etc|usr|var|bin|sbin|lib|opt|root|home)(/|\s|$)']='rm -rf on system path'
  ['rm[[:space:]]+-rf?[[:space:]]+~(\s|$)']='rm -rf on home'
  ['rm[[:space:]]+-rf?[[:space:]]+\$HOME']='rm -rf on $HOME'
  ['git[[:space:]]+clean[[:space:]]+(-[a-z]*[fdx][a-z]*[[:space:]]+)*-[a-z]*[fdx]{2,}']='git clean -fdx (wipes uncommitted)'
  [':\(\)\{[[:space:]]*:\|:&[[:space:]]*\};:']='fork bomb'
  ['DROP[[:space:]]+TABLE']='SQL DROP TABLE'
  ['TRUNCATE[[:space:]]+TABLE']='SQL TRUNCATE TABLE'
  ['git[[:space:]]+push[[:space:]]+(-f|--force)[[:space:]].*\b(main|master)\b']='force push to protected branch'
  ['git[[:space:]]+reset[[:space:]]+--hard[[:space:]]+origin/(main|master)']='hard reset on protected branch'
  ['curl[[:space:]]+.*\|[[:space:]]*(sudo[[:space:]]+)?(bash|sh|zsh)']='curl pipe to shell'
  ['wget[[:space:]]+.*\|[[:space:]]*(sudo[[:space:]]+)?(bash|sh|zsh)']='wget pipe to shell'
  ['chmod[[:space:]]+-R[[:space:]]+777']='chmod -R 777 (overly permissive)'
  ['/dev/sda']='direct disk access'
  ['mkfs\.']='filesystem format'
  ['dd[[:space:]]+.*of=/dev/']='dd to a device'
)

shopt -s nocasematch
for pattern in "${!patterns[@]}"; do
  if [[ "$command" =~ $pattern ]]; then
    echo "BLOCKED: command matches dangerous pattern: ${patterns[$pattern]}" >&2
    echo "Command was: $command" >&2
    echo "If you genuinely need this, run it outside Claude Code." >&2
    exit 2
  fi
done

exit 0
