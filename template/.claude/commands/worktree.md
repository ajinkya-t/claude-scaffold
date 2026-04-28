---
description: Create a git worktree for isolated parallel work, on a fresh branch.
argument-hint: <feature-name>
allowed-tools: Bash(git worktree:*), Bash(git branch:*), Bash(git status:*), Bash(pwd), Bash(basename:*)
---

# /worktree

Feature: $ARGUMENTS

Create an isolated worktree so this Claude session (or a parallel one) can work on `$ARGUMENTS` without disturbing the main checkout.

1. Confirm the working tree is clean: `git status --porcelain`. If it has uncommitted changes, stop and tell me to stash or commit first.

2. Determine the worktree path and branch name:
   - Repo dir: result of `basename "$(pwd)"`
   - Worktree path: `../<repo-dir>-$ARGUMENTS`
   - Branch name: `feat/$ARGUMENTS`

3. Create the worktree on a new branch off the current HEAD:
   ```
   git worktree add <worktree-path> -b feat/$ARGUMENTS
   ```

4. Output two things and stop:
   - The path that was created
   - The exact `cd` command I should run, plus a reminder to start a fresh Claude session there

Do **not** `cd` yourself — Claude can't change the user's shell. Just print the command.

If `$ARGUMENTS` is empty, ask me for the feature name.
