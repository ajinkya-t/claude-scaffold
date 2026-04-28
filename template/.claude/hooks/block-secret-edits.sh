#!/usr/bin/env bash
# block-secret-edits.sh
# PreToolUse hook on Edit|Write|MultiEdit
# Exit 2 = block the tool call and surface stderr to Claude.
#
# Per Anthropic hooks spec at code.claude.com/docs/en/hooks

set -euo pipefail

# Read the tool call JSON from stdin
input="$(cat)"

# Extract the file path being written
file_path="$(echo "$input" | jq -r '.tool_input.file_path // .tool_input.path // empty')"

if [[ -z "$file_path" ]]; then
  exit 0
fi

# Patterns to block (case-insensitive)
patterns=(
  '\.env$'
  '\.env\.'
  '/secrets/'
  'credentials\.json$'
  'id_rsa'
  'id_ed25519'
  '\.pem$'
  '\.key$'
  '\.p12$'
  '\.pfx$'
  '\.keystore$'
)

shopt -s nocasematch
for pattern in "${patterns[@]}"; do
  if [[ "$file_path" =~ $pattern ]]; then
    echo "BLOCKED: $file_path matches sensitive-file pattern '$pattern'." >&2
    echo "If this is intentional, edit the file outside Claude Code or update .claude/hooks/block-secret-edits.sh." >&2
    exit 2
  fi
done

exit 0
