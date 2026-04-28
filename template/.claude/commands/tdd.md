---
description: Test-Driven Development. Forces RED -> GREEN -> REFACTOR with explicit stops.
argument-hint: <feature or behavior to implement>
---

# /tdd

Behavior: $ARGUMENTS

We will do this in three explicit phases. **STOP between phases and wait for me to say "go".**

## Phase 1: RED

1. Write a failing test that captures the intended behavior. Just one test, the smallest meaningful one.
2. Run the test. Confirm it fails for the right reason (not import error, not syntax — actual assertion failure).
3. Show me the test file and the failing output.
4. **STOP.** Wait for "go".

## Phase 2: GREEN

1. Write the **minimum** code to make the test pass. No extra features. No "while I'm here" cleanup.
2. Run the test. Confirm it passes.
3. Run the full suite. Confirm nothing else broke.
4. Show me the diff and the test output.
5. **STOP.** Wait for "go".

## Phase 3: REFACTOR

1. Review the new code for: duplication, unclear naming, missing edge cases, structural issues.
2. Refactor with the test still passing after every change.
3. If you discover the test was insufficient, write more tests *first* (back to RED).
4. Show me the final diff.
5. End with: "TDD cycle complete. Run `/review` next?"

Per Simon Willison's rule: every change ships with a test that fails when you revert the implementation.
