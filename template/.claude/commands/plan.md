---
description: Plan a non-trivial change before implementation. Forces Explore -> Plan flow.
argument-hint: <task description>
allowed-tools: Bash(git status:*), Bash(git log:*), Read, Glob, Grep
---

# /plan

Task: $ARGUMENTS

Before writing any code, do this in order:

1. **Explore.** Read the relevant files. Trace existing patterns. Check `git log --oneline -20` for recent context. Don't grep-and-skim; actually read.

2. **Identify constraints.** Existing conventions in the codebase. Edge cases. Failure modes. What would a careful reviewer flag?

3. **Write the plan as a numbered list.** Each step is one logical change with:
   - Files touched
   - Specific approach (not just "add validation" but "validate X with Y because Z")
   - How you'll verify it worked (tests, type check, manual check)

4. **Flag open questions.** If something is ambiguous, list it. Don't guess.

5. **Stop.** Output the plan. Do not implement. Wait for me to approve, edit (Ctrl+G to open in editor), or push back.

If the task is genuinely a one-line diff, say so and skip the plan.
