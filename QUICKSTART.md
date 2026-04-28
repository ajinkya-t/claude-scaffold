# Quickstart — after unzipping

## 1. Verify it works

```bash
cd ~/projects/claude-scaffold
uv venv && uv sync          # or: python3 -m pip install copier pytest pyyaml
uv run pytest               # should be 19/19 passing
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
| Slash commands (`/plan`, `/review`, `/commit`, `/tdd`, `/techdebt`, `/security-review`) | 6 |
| Subagents (`code-reviewer`, `test-writer`, `debugger`, `security-auditor`) | 4 |
| Hooks (secret blocking, dangerous-bash blocking, tests-before-PR, perm routing) | 4 |
| Output styles | 1 (`concise`) |
| Skills | 1 (`repo-conventions`) |
| CI workflows (`claude-review`, `claude-techdebt`) | 2 |
| MCP servers (default: github + filesystem; opt-in: postgres, sqlite, playwright, supabase, ref, chrome-devtools) | 2 default + 6 opt-in |
| Pre-commit config (per-language: ruff/prettier/gofmt/cargo + gitleaks) | 1 |

Total: 35 files in the template repo, 27 in the rendered project.

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

If you set `enable_superpowers=true` during `copier copy`, the scaffold:

- Drops `/plan`, `/review`, `/tdd` commands (replaced by Superpowers' auto-triggered skills)
- Drops `code-reviewer`, `test-writer`, `debugger` subagents (replaced by Superpowers equivalents)
- Adds `/review-with-superpowers` (delegates to `superpowers:code-reviewer` + your `security-auditor`)
- Adds two project-level skills: `design-review` and `spec-security-review`
- Adds a USER-LEVEL INSTRUCTIONS section to AGENTS.md telling Superpowers to invoke both skills during the brainstorming User-Review-Gate

The integration solves the known issue where Superpowers' brainstorming skill explicitly blocks `frontend-design` and other implementation skills via a `<HARD-GATE>`. The two project skills run inside the User-Review-Gate window (after design approval, before `writing-plans`), which is *outside* the gate's blocking scope, and `frontend-design` is invoked indirectly via `design-review` only when UI is in scope.

To install Superpowers:
```bash
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

Or via the official Anthropic marketplace:
```bash
/plugin install superpowers@claude-plugins-official
```

Don't install both. Don't install the full `obra/superpowers-marketplace` bundle if you want to avoid Context7 — use the official Anthropic marketplace install instead.

## References

- Anthropic Claude Code best practices: `code.claude.com/docs/en/best-practices`
- Hooks reference: `code.claude.com/docs/en/hooks`
- Boris Cherny's tips: `howborisusesclaudecode.com`
- Copier docs: `copier.readthedocs.io`
- The blueprint this scaffold implements is in `docs/blueprint.md` if you copy the v2 doc into the repo (recommended).
