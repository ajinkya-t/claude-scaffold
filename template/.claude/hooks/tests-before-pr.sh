#!/usr/bin/env bash
# tests-before-pr.sh
# PreToolUse hook fired on Bash and mcp__github__create_pull_request.
# Bash hooks fire for every command, so we self-filter to the PR-creation case.
# Runs the project test suite; exit 2 if it fails.

set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "tests-before-pr: jq not installed — skipping (install: brew install jq)" >&2
  exit 0
fi

input="$(cat)"
tool_name="$(echo "$input" | jq -r '.tool_name // empty')"
bash_command="$(echo "$input" | jq -r '.tool_input.command // empty')"

# Only run when the user is actually creating a PR.
is_pr_create=0
if [[ "$tool_name" == "mcp__github__create_pull_request" ]]; then
  is_pr_create=1
elif [[ "$tool_name" == "Bash" && "$bash_command" =~ gh[[:space:]]+pr[[:space:]]+create ]]; then
  is_pr_create=1
fi

if [[ $is_pr_create -eq 0 ]]; then
  exit 0
fi

# Detect test command from project files
if [[ -f "pyproject.toml" ]] && grep -q "pytest" pyproject.toml 2>/dev/null; then
  if command -v uv &>/dev/null && [[ -f "uv.lock" ]]; then
    test_cmd="uv run pytest --maxfail=1 -q"
  else
    test_cmd="pytest --maxfail=1 -q"
  fi
elif [[ -f "package.json" ]]; then
  if [[ -f "pnpm-lock.yaml" ]]; then
    test_cmd="pnpm test"
  elif [[ -f "yarn.lock" ]]; then
    test_cmd="yarn test"
  elif [[ -f "bun.lockb" ]]; then
    test_cmd="bun test"
  else
    test_cmd="npm test"
  fi
elif [[ -f "go.mod" ]]; then
  test_cmd="go test ./..."
elif [[ -f "Cargo.toml" ]]; then
  test_cmd="cargo test"
else
  echo "tests-before-pr: no test config detected; skipping." >&2
  exit 0
fi

timeout_secs="${CLAUDE_TESTS_TIMEOUT:-300}"
echo "tests-before-pr: running '$test_cmd' (timeout ${timeout_secs}s)..." >&2

# Use `timeout` if available (GNU coreutils on Linux, brew coreutils on macOS as gtimeout).
if command -v timeout >/dev/null 2>&1; then
  runner="timeout ${timeout_secs}"
elif command -v gtimeout >/dev/null 2>&1; then
  runner="gtimeout ${timeout_secs}"
else
  runner=""
fi

if ! $runner bash -c "$test_cmd" >&2; then
  echo "" >&2
  echo "BLOCKED: tests failed. Fix them before opening the PR." >&2
  echo "Override: set CLAUDE_SKIP_TESTS=1 (use sparingly)." >&2
  if [[ "${CLAUDE_SKIP_TESTS:-0}" == "1" ]]; then
    echo "CLAUDE_SKIP_TESTS=1 set; allowing PR despite test failure." >&2
    exit 0
  fi
  exit 2
fi

echo "tests-before-pr: passed." >&2
exit 0
