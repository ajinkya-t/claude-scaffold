#!/usr/bin/env bash
# tests-before-pr.sh
# PreToolUse hook on PR creation tools
# Runs the project test suite; exit 2 if it fails.

set -euo pipefail

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

echo "tests-before-pr: running '$test_cmd'..." >&2

if ! eval "$test_cmd" >&2; then
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
