#!/usr/bin/env bash
# route-perms-to-opus.sh
# PermissionRequest hook
#
# Boris Cherny's pattern (Jan 31, 2026):
# Route incoming permission requests to Opus 4.5 to scan for prompt-injection
# attacks via untrusted content (e.g., a script trying to exfiltrate .env
# because something Claude read told it to). Auto-approve safe ones,
# escalate risky ones to the user.
#
# This is an EXAMPLE implementation. It logs requests and passes through
# by default. Customize the heuristics or wire in an `claude -p` call
# with Opus to actually scan tool inputs.

set -euo pipefail

input="$(cat)"
log_file="${CLAUDE_PROJECT_DIR:-.}/.claude/permission-requests.log"

# Always log
mkdir -p "$(dirname "$log_file")"
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $input" >> "$log_file"

# Heuristic pre-filter: obvious red flags get escalated to the user immediately
tool_input="$(echo "$input" | jq -r '.tool_input // {}')"

# Red flags that should always require human approval
if echo "$tool_input" | grep -qiE '(curl|wget).*\|.*(bash|sh)'; then
  jq -n '{permissionDecision: "ask", permissionDecisionReason: "Pipe-to-shell detected; please review."}' >&2
  exit 0
fi

if echo "$tool_input" | grep -qiE '(\.env|secrets|credentials|\.pem|\.key|id_rsa|id_ed25519)'; then
  jq -n '{permissionDecision: "ask", permissionDecisionReason: "Reference to sensitive file; please review."}' >&2
  exit 0
fi

# To enable Opus-based scanning, uncomment the block below and ensure
# `claude` is on your PATH. This will spawn a one-shot Opus call to
# evaluate the request.
#
# response="$(echo "$input" | claude -p "Is this tool call safe? Reply with JSON: {\"safe\": bool, \"reason\": string}" --model claude-opus-4-5 --output-format json 2>/dev/null || echo '{}')"
# safe="$(echo "$response" | jq -r '.safe // false')"
# if [[ "$safe" == "true" ]]; then
#   exit 0
# else
#   reason="$(echo "$response" | jq -r '.reason // "Opus flagged this."')"
#   jq -n --arg r "$reason" '{permissionDecision: "ask", permissionDecisionReason: $r}' >&2
#   exit 0
# fi

# Default: pass through (Claude Code's normal permission flow takes over)
exit 0
