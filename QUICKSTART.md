# Quickstart — after unzipping

## 1. Verify it works

```bash
cd ~/projects/claude-scaffold
uv venv && uv sync          # or: pip install copier pytest pyyaml
uv run pytest               # all template-render tests should pass
```

If anything fails, the test output points at the exact file/line.

## 2. Try a render locally

```bash
# In a temp dir, render the scaffold for an imaginary project
cd /tmp
uvx copier copy --trust ~/projects/claude-scaffold demo-app
cd demo-app
ls -la
cat AGENTS.md
cat .claude/settings.json
```

If that all looks right, the template is good.

## 3. Push to GitHub

```bash
cd ~/projects/claude-scaffold
git init
git add .
git commit -m "feat: initial claude-code harness scaffold"
gh repo create ajinkya-t/claude-scaffold --public --source=. --push
```

Optionally enable the GitHub Template flag so the "Use this template" button appears:

```bash
gh repo edit ajinkya-t/claude-scaffold --template
```

## 4. Use it for a new project

```bash
uvx copier copy --trust gh:ajinkya-t/claude-scaffold my-new-app
cd my-new-app
claude
```

## 5. Use it for an existing project

```bash
cd existing-repo
git checkout -b chore/claude-scaffold
uvx copier copy --trust gh:ajinkya-t/claude-scaffold .
# Manually merge any CLAUDE.md / AGENTS.md / .gitignore conflicts.
# If you run /init in claude, ruthlessly trim the output (ETH Zurich research:
# raw /init output reduces success rates ~3% and inflates tokens ~20%).
git add -A && git commit -m "chore: add claude-code harness"
```

## 6. Update an already-scaffolded project

```bash
cd my-app
uvx copier update --trust
# Resolve any conflicts; commit.
```

## What you have

| Component | Count |
|---|---|
| Slash commands (vanilla: `/plan` `/review` `/commit` `/tdd` `/techdebt` `/security-review` `/worktree`) | 7 |
| Slash commands (+superpowers: `/brainstorm` `/sp-plan` `/sp-debug` `/sp-skill` on Opus; `/sp-tdd` `/sp-implement` `/sp-subagent` `/sp-worktree` `/sp-review-request` `/sp-review-receive` `/sp-finish` `/sp-verify` `/review-with-superpowers` on Sonnet) | +13 |
| Subagents (`code-reviewer`, `test-writer`, `debugger`, `security-auditor`) — model-pinned | 4 |
| Hooks (secret blocking, dangerous-bash blocking, tests-before-PR, perm routing, lockfile warn, spec-review-trigger) | 6 |
| Output styles | 1 (`concise`) |
| Skills (vanilla: `repo-conventions`, `domain-conventions`; +superpowers: `routing`, `design-review`, `spec-security-review`) | 2 base + 3 sp |
| CI workflows (`claude-review`, `claude-techdebt`) | 2 |
| MCP servers (default: github + filesystem; opt-in: postgres, sqlite, playwright, supabase, ref, chrome-devtools) | 2 default + 6 opt-in |
| Pre-commit config (per-language: ruff/prettier/gofmt/cargo + gitleaks) | 1 |

When `enable_superpowers=true`: AGENTS.md stays under 25 lines (procedural guidance moved to `routing` skill + `spec-review-trigger.sh` hook), and Sonnet sessions get the 1M-context beta header automatically when `model_mid` resolves to sonnet.

## Things to customize on day 1

1. **`copier.yml`**: edit defaults if you'll always pick the same options (e.g. always Python + uv).
2. **`template/.claude/skills/repo-conventions/SKILL.md.jinja`**: add your real conventions over time. Rule of thumb from Boris: update when you've corrected Claude on the same convention twice.
3. **`template/.claude/agents/*.md`**: tune the subagent prompts if your domain has specific patterns to look for.
4. **`template/.github/workflows/claude-*.yml`**: edit the prompts to match what your team actually wants flagged.
5. **`template/.claude/settings.json.jinja`**: prune the `permissions.allow` list if any commands shouldn't be auto-allowed in your context.

## Don't commit

These are personal/local and never go in git (the rendered `.gitignore` already handles them):

- `.claude/settings.local.json`
- `CLAUDE.local.md`
- `.claude/.credentials.json`
- `.claude/cache/`
- `.claude/worktrees/`
- `.claude/permission-requests.log` (created by route-perms-to-opus.sh)

## When something goes wrong

- **Copier YAML errors**: usually a `:` inside an unquoted help string. Wrap the value in `"..."`.
- **`{{ project_name }}` showing literally in rendered file**: the file needs the `.jinja` suffix.
- **Hook not running**: check `chmod +x` on the `.sh` file. Check `$CLAUDE_PROJECT_DIR` is set in the environment.
- **MCP server not loading**: check the env var (`GITHUB_TOKEN`, `SUPABASE_ACCESS_TOKEN`, etc.) is exported.

## Using with the Superpowers plugin

If you set `enable_superpowers=true` during `copier copy`, choose a `superpowers_source`:

- **`pcvelz` (default, recommended)** — `pcvelz/superpowers` fork with native Claude Code task management (TaskCreate w/ structured `json:metadata`, dependency enforcement, pre-commit task gate, cross-session resume). Skill prefix: `superpowers-extended-cc:`.
- **`obra`** — upstream `obra/superpowers`, cross-platform (CC/Codex/OpenCode/Gemini). Skill prefix: `superpowers:`.

Install the chosen source:

```bash
# pcvelz (default)
/plugin marketplace add pcvelz/superpowers
/plugin install superpowers-extended-cc@superpowers-extended-cc-marketplace

# obra
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

What the scaffold ships when superpowers is enabled:

- Drops `/plan`, `/tdd`, `/review` and the `code-reviewer`/`test-writer`/`debugger` subagents (Superpowers replaces them).
- Adds `/review-with-superpowers` and 12 tier-pinned slash shims (4 Opus + 8 Sonnet) that wrap the per-skill invocations with the right `model:` frontmatter — the only mechanism to get a specific model on a Superpowers skill.
- Adds three skills: `routing` (model tier reference), `design-review`, `spec-security-review`.
- Adds the `spec-review-trigger.sh` PostToolUse hook — fires the moment a design doc is saved at `docs/superpowers/specs/*-design.md`, injecting a system reminder to invoke `design-review` (and `spec-security-review` when security keywords are detected). Replaces ~17 lines of always-loaded AGENTS.md prose.
- Appends Claude Code's `[1m]` alias suffix on Opus/Sonnet tiers (e.g. `sonnet[1m]`, `opus[1m]`) — the canonical way to enable the 1M context window per `code.claude.com/docs/en/model-config`. Haiku has no 1M variant; the suffix is omitted on the low tier when it resolves to haiku. Disable per project with `enable_1m_context=false` in copier answers, or globally at runtime with `CLAUDE_CODE_DISABLE_1M_CONTEXT=1`.

The integration solves the issue where Superpowers' brainstorming skill `<HARD-GATE>` blocks implementation skills like `frontend-design`: the project skills run inside the User-Review-Gate window (after design approval, before `writing-plans`), which is *outside* the gate's blocking scope, and `frontend-design` is invoked indirectly via `design-review` only when UI is in scope.

### pcvelz-specific: required and optional config

When `superpowers_source=pcvelz`, the scaffold automatically adds `"EnterPlanMode"` to `.claude/settings.json` `permissions.deny` — the fork's brainstorming + writing-plans skills require normal mode and the README explicitly calls this out as recommended config.

Two opt-in hooks ship inside the pcvelz plugin (not auto-wired by this scaffold — they reference the plugin's install dir). Add to `.claude/settings.local.json` if you want them:

- **`pre-commit-check-tasks.sh`** — `PreToolUse` on `Bash`. Blocks `git commit` while a native task is `in_progress`. Pending tasks pass through, so per-task commit flows still work.
- **`stop-deflection-guard.sh`** — `Stop` event. Blocks "fresh session later" / "context is full" deflections when real context usage is below 50%.

Both live at `~/.claude/plugins/marketplaces/superpowers-extended-cc-marketplace/hooks/examples/`. See the script headers for configuration env vars.

## References

- Anthropic Claude Code best practices: `code.claude.com/docs/en/best-practices`
- Hooks reference: `code.claude.com/docs/en/hooks`
- Boris Cherny's tips: `howborisusesclaudecode.com`
- Copier docs: `copier.readthedocs.io`
- The blueprint this scaffold implements is in `docs/blueprint.md` if you copy the v2 doc into the repo (recommended).
