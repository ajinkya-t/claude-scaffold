---
description: Pre-commit code review of staged + unstaged changes via parallel subagents.
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Task
---

# /review

1. Run `git status` and `git diff HEAD` to see what's changed.

2. Delegate to subagents **in parallel** (single message, multiple Task calls):
   - `code-reviewer` — correctness, naming, dead code, missing tests, style
   - `security-auditor` — secrets, injection, auth gaps, unsafe deserialization

3. Compile findings into three buckets:
   - 🔴 **Blockers** (must fix): correctness bugs, security issues, broken tests, secrets in diff
   - 🟡 **Should fix**: style violations, missing tests, unclear naming, dead branches
   - 🟢 **Nice to have**: refactor opportunities, missing docs

4. Each finding format: `path/to/file:LINE — what's wrong — concrete fix`.

5. End with: `Ready to commit? [Y/n]`. **Do not run `git commit` until I say yes.**
