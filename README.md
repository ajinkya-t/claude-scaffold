# claude-scaffold

A pragmatic Claude Code harness for production-grade work. Distilled from Anthropic's official guidance, Boris Cherny's threads, and 2026 practitioner consensus.

## What you get

- Terse `CLAUDE.md` / `AGENTS.md` (~35 lines, vendor-neutral)
- 4 deterministic hooks (secret blocking, dangerous-bash blocking, tests-before-PR, permission routing to Opus)
- 4 narrowly-scoped subagents (code-reviewer, test-writer, debugger, security-auditor)
- 6 slash commands (`/plan`, `/review`, `/commit`, `/tdd`, `/techdebt`, `/security-review`)
- Per-task model routing (Opus / Sonnet / Haiku)
- `.github/workflows/` with `claude -p` headless mode for CI review and duplicate sweeps
- Pre-commit config (ruff / prettier / gitleaks) — formatting lives here, not in PostToolUse
- Optional: BMAD spec-driven layer, Chrome extension pointer, Superpowers skill cherry-picks

## Usage

### New project

```bash
uvx copier copy --trust gh:ajinkya-t/claude-scaffold my-app
cd my-app
claude
```

### Existing project

```bash
cd existing-repo
git checkout -b chore/claude-scaffold
uvx copier copy --trust gh:ajinkya-t/claude-scaffold .
# Resolve any CLAUDE.md / AGENTS.md / .gitignore conflicts manually
# Then ruthlessly trim /init output if you ran it
git add -A && git commit -m "chore: add claude-code harness"
```

### Update an already-scaffolded project

```bash
cd my-app
uvx copier update --trust
# Resolve conflicts; commit
```

## Prerequisites

- `uv` installed (https://docs.astral.sh/uv/)
- Claude Code installed (https://claude.com/code)
- Optional: `gh` CLI for GitHub integration, `pre-commit` for the bundled hooks

## Tests

The scaffold ships with a static `pytest` suite that renders the template under several Copier answer combos and asserts the rendered files are correct. Run `pytest` from the repo root.

There is also an opt-in **live runtime** suite that drives `claude -p` headless against a freshly rendered scaffold and verifies model routing actually resolves to the expected tier on the wire (Opus / Sonnet / Haiku, with or without `[1m]`). Covers both `enable_superpowers` modes and the tier-pinned `/sp-*` shims. Skipped by default. To run:

```bash
pytest -m live              # uses `claude auth` login (Pro/Max) if present
ANTHROPIC_API_KEY=... pytest -m live
```

Costs <$0.40 per run (~17 API calls) and requires the `claude` CLI on `PATH`.

## What this is not

- **Not a 100-agent mega-collection.** Use `wshobson/agents`, `VoltAgent/awesome-claude-code-subagents`, `hesreallyhim/awesome-claude-code` as catalogs. This scaffold is intentionally minimal.
- **Not a replacement for thinking.** The best CLAUDE.md is the one you've pruned three times. Start here, then cut what doesn't help.
- **Not vendor-locked.** Default writes `AGENTS.md` and a 2-line `CLAUDE.md` that imports it. Codex, Cursor, Aider, Copilot, Windsurf all read the same file.

## License

MIT

## References

- Anthropic Claude Code best practices: https://code.claude.com/docs/en/best-practices
- Hooks reference: https://code.claude.com/docs/en/hooks
- Boris Cherny's tips: https://howborisusesclaudecode.com
