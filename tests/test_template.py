"""
Tests for the claude-scaffold Copier template.

These render the template with various combinations of answers and
assert that key files exist and parse correctly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from copier import run_copy


TEMPLATE_ROOT = Path(__file__).parent.parent


def render(tmp_path: Path, **overrides: Any) -> Path:
    """Render the template into tmp_path and return the destination."""
    answers = {
        "project_name": "test-app",
        "project_description": "A test project",
        "language": "python",
        "framework": "fastapi",
        "package_manager": "uv",
        "agents_file_strategy": "agents-md-symlink",
        "mcps": ["github", "filesystem"],
        "chrome_extension": False,
        "hooks": [
            "block-secret-edits",
            "block-dangerous-bash",
            "tests-before-pr",
            "route-perms-to-opus",
            "warn-on-lockfile-edit",
        ],
        "subagents": ["code-reviewer", "test-writer", "debugger", "security-auditor"],
        "output_style": "concise",
        "model_routing": "latest",
        "enable_1m_context": True,
        "model_high": "opus[1m]",
        "model_mid": "sonnet[1m]",
        "model_low": "haiku",  # haiku has no 1M variant
        "enable_superpowers": False,
        "enable_bmad": False,
        "ci_review": True,
        "pre_commit": True,
        "git_init": False,
        "license": "MIT",
        "author_name": "Test Author",
        "author_email": "test@example.com",
        **overrides,
    }
    dst = tmp_path / "rendered"
    run_copy(
        src_path=str(TEMPLATE_ROOT),
        dst_path=str(dst),
        data=answers,
        defaults=True,
        unsafe=True,
        quiet=True,
    )
    return dst


# ---------------------------------------------------------------------------
# File-existence tests
# ---------------------------------------------------------------------------


def test_core_files_exist(tmp_path: Path) -> None:
    dst = render(tmp_path)
    assert (dst / "AGENTS.md").exists()
    assert (dst / "CLAUDE.md").exists()
    assert (dst / "README.md").exists()
    assert (dst / ".gitignore").exists()
    assert (dst / ".mcp.json").exists()
    assert (dst / ".claude" / "settings.json").exists()
    assert (dst / ".pre-commit-config.yaml").exists()


def test_all_six_commands_exist(tmp_path: Path) -> None:
    dst = render(tmp_path)
    cmd_dir = dst / ".claude" / "commands"
    expected = {"plan.md", "review.md", "commit.md", "tdd.md", "techdebt.md", "security-review.md"}
    actual = {p.name for p in cmd_dir.iterdir()}
    assert expected.issubset(actual), f"Missing commands: {expected - actual}"


def test_all_four_subagents_exist(tmp_path: Path) -> None:
    dst = render(tmp_path)
    agent_dir = dst / ".claude" / "agents"
    expected = {"code-reviewer.md", "test-writer.md", "debugger.md", "security-auditor.md"}
    actual = {p.name for p in agent_dir.iterdir()}
    assert expected.issubset(actual)


def test_default_hooks_exist_and_have_shebangs(tmp_path: Path) -> None:
    dst = render(tmp_path)
    hooks_dir = dst / ".claude" / "hooks"
    expected = {
        "block-secret-edits.sh",
        "block-dangerous-bash.sh",
        "tests-before-pr.sh",
        "route-perms-to-opus.sh",
        "warn-on-lockfile-edit.sh",
    }
    actual = {p.name for p in hooks_dir.iterdir() if p.is_file()}
    assert expected.issubset(actual)
    # We can't reliably check executable bit on rendered output across platforms,
    # but the shebang must be present.
    for hook_name in expected:
        first_line = (hooks_dir / hook_name).read_text().splitlines()[0]
        assert first_line.startswith("#!"), f"{hook_name} missing shebang"


def test_notify_on_stop_hook_renders_when_selected(tmp_path: Path) -> None:
    dst = render(tmp_path, hooks=[
        "block-secret-edits", "block-dangerous-bash",
        "tests-before-pr", "route-perms-to-opus",
        "warn-on-lockfile-edit", "notify-on-stop",
    ])
    hook_path = dst / ".claude" / "hooks" / "notify-on-stop.sh"
    assert hook_path.exists()
    settings = json.loads((dst / ".claude" / "settings.json").read_text())
    assert "Stop" in settings["hooks"], "Stop event missing from settings.hooks"


def test_repo_conventions_skill_exists(tmp_path: Path) -> None:
    dst = render(tmp_path)
    skill = dst / ".claude" / "skills" / "repo-conventions" / "SKILL.md"
    assert skill.exists()
    content = skill.read_text()
    assert "test-app" in content


def test_ci_workflows_exist_when_enabled(tmp_path: Path) -> None:
    dst = render(tmp_path, ci_review=True)
    assert (dst / ".github" / "workflows" / "claude-review.yml").exists()
    assert (dst / ".github" / "workflows" / "claude-techdebt.yml").exists()


# ---------------------------------------------------------------------------
# File-validity tests
# ---------------------------------------------------------------------------


def test_settings_json_is_valid_json(tmp_path: Path) -> None:
    dst = render(tmp_path)
    settings = json.loads((dst / ".claude" / "settings.json").read_text())
    assert "permissions" in settings
    assert "hooks" in settings
    # 'latest' routing + enable_1m_context=true → session default is sonnet[1m]
    assert settings.get("model", "") == "sonnet[1m]"


def test_mcp_json_is_valid_json(tmp_path: Path) -> None:
    dst = render(tmp_path)
    mcp = json.loads((dst / ".mcp.json").read_text())
    assert "mcpServers" in mcp
    assert "github" in mcp["mcpServers"]
    assert "filesystem" in mcp["mcpServers"]


def test_pre_commit_config_is_valid_yaml(tmp_path: Path) -> None:
    dst = render(tmp_path)
    config = yaml.safe_load((dst / ".pre-commit-config.yaml").read_text())
    assert "repos" in config
    assert len(config["repos"]) > 0


def test_ci_workflows_are_valid_yaml(tmp_path: Path) -> None:
    dst = render(tmp_path, ci_review=True)
    review = yaml.safe_load((dst / ".github" / "workflows" / "claude-review.yml").read_text())
    assert "jobs" in review
    techdebt = yaml.safe_load((dst / ".github" / "workflows" / "claude-techdebt.yml").read_text())
    assert "jobs" in techdebt


# ---------------------------------------------------------------------------
# Conditional rendering tests
# ---------------------------------------------------------------------------


def test_agents_md_symlink_strategy_makes_claude_md_a_2_line_import(tmp_path: Path) -> None:
    dst = render(tmp_path, agents_file_strategy="agents-md-symlink")
    claude_md = (dst / "CLAUDE.md").read_text()
    assert "@AGENTS.md" in claude_md
    # Should be terse — under 10 lines total
    assert len(claude_md.strip().splitlines()) < 10


def test_claude_md_only_strategy_inlines_full_content(tmp_path: Path) -> None:
    dst = render(tmp_path, agents_file_strategy="claude-md")
    claude_md = (dst / "CLAUDE.md").read_text()
    assert "@AGENTS.md" not in claude_md
    assert "## Stack" in claude_md
    assert "## Workflow" in claude_md


def test_typescript_renders_correct_pre_commit(tmp_path: Path) -> None:
    dst = render(tmp_path, language="typescript", framework="next", package_manager="pnpm")
    config = (dst / ".pre-commit-config.yaml").read_text()
    assert "prettier" in config
    assert "ruff" not in config


def test_python_renders_ruff_in_pre_commit(tmp_path: Path) -> None:
    dst = render(tmp_path, language="python", package_manager="uv")
    config = (dst / ".pre-commit-config.yaml").read_text()
    assert "ruff" in config


def test_supabase_only_appears_when_selected(tmp_path: Path) -> None:
    dst = render(tmp_path, mcps=["github", "filesystem", "supabase"])
    mcp = json.loads((dst / ".mcp.json").read_text())
    assert "supabase" in mcp["mcpServers"]
    # Read-only should be in the args
    assert any("--read-only" in str(arg) for arg in mcp["mcpServers"]["supabase"]["args"])


def test_supabase_absent_when_not_selected(tmp_path: Path) -> None:
    dst = render(tmp_path, mcps=["github", "filesystem"])
    mcp = json.loads((dst / ".mcp.json").read_text())
    assert "supabase" not in mcp["mcpServers"]


# ---------------------------------------------------------------------------
# Hook content sanity
# ---------------------------------------------------------------------------


def test_block_secret_edits_blocks_env_files(tmp_path: Path) -> None:
    dst = render(tmp_path)
    hook = (dst / ".claude" / "hooks" / "block-secret-edits.sh").read_text()
    assert "\\.env" in hook
    assert "id_rsa" in hook
    assert "exit 2" in hook


def test_block_dangerous_bash_catches_rm_rf_root(tmp_path: Path) -> None:
    dst = render(tmp_path)
    hook = (dst / ".claude" / "hooks" / "block-dangerous-bash.sh").read_text()
    assert "rm" in hook
    assert "fork bomb" in hook
    assert "force push" in hook


# ---------------------------------------------------------------------------
# Settings deny-list sanity
# ---------------------------------------------------------------------------


def test_tests_before_pr_matcher_uses_tool_names(tmp_path: Path) -> None:
    """C1 regression: matcher must use tool names, not permission specs."""
    dst = render(tmp_path)
    settings = json.loads((dst / ".claude" / "settings.json").read_text())
    pre_tool = settings["hooks"]["PreToolUse"]
    matchers = [entry["matcher"] for entry in pre_tool]
    # Find the tests-before-pr entry
    tests_entries = [
        m for m in matchers
        if "mcp__github__create_pull_request" in m or "tests-before-pr" in str(pre_tool)
    ]
    assert any("Bash|mcp__github__create_pull_request" == m for m in matchers), (
        f"tests-before-pr matcher should be 'Bash|mcp__github__create_pull_request', got {matchers!r}"
    )
    # No matcher should contain permission-spec syntax
    for m in matchers:
        assert "(" not in m and ":*" not in m, (
            f"matcher {m!r} looks like a permission spec, not a tool-name regex"
        )


def test_tests_before_pr_script_self_filters(tmp_path: Path) -> None:
    """C1 regression: the script must short-circuit when not actually creating a PR."""
    dst = render(tmp_path)
    hook = (dst / ".claude" / "hooks" / "tests-before-pr.sh").read_text()
    assert "is_pr_create" in hook
    assert "gh[[:space:]]+pr[[:space:]]+create" in hook
    assert "mcp__github__create_pull_request" in hook


def test_perms_hook_writes_decision_to_stdout(tmp_path: Path) -> None:
    """C2 regression: permission decisions must go to stdout, not stderr."""
    dst = render(tmp_path)
    hook = (dst / ".claude" / "hooks" / "route-perms-to-opus.sh").read_text()
    # The two structured-decision invocations must NOT redirect to stderr
    decision_lines = [
        line for line in hook.splitlines()
        if "permissionDecision" in line and "jq -n" in line
    ]
    assert decision_lines, "expected at least one jq -n permissionDecision line"
    for line in decision_lines:
        assert ">&2" not in line, (
            f"permission decision line redirects to stderr: {line!r}"
        )


def test_agent_tools_field_uses_plain_names(tmp_path: Path) -> None:
    """C4 regression: agent `tools:` frontmatter takes tool names, not permission specs."""
    dst = render(tmp_path)
    agent_dir = dst / ".claude" / "agents"
    for agent_file in agent_dir.glob("*.md"):
        content = agent_file.read_text()
        # Extract frontmatter block
        lines = content.splitlines()
        assert lines[0] == "---", f"{agent_file.name}: missing frontmatter"
        end = lines.index("---", 1)
        for line in lines[1:end]:
            if line.startswith("tools:"):
                value = line.split(":", 1)[1].strip()
                assert "(" not in value and ":*" not in value, (
                    f"{agent_file.name}: tools field {value!r} uses permission-spec syntax"
                )


def test_permission_log_is_gitignored(tmp_path: Path) -> None:
    """C7 regression: route-perms log file must be gitignored."""
    dst = render(tmp_path)
    gitignore = (dst / ".gitignore").read_text()
    assert ".claude/permission-requests.log" in gitignore


def test_hooks_have_jq_guard(tmp_path: Path) -> None:
    """C6 regression: each jq-using hook must short-circuit gracefully if jq is absent."""
    dst = render(tmp_path)
    hooks_dir = dst / ".claude" / "hooks"
    for hook_name in (
        "block-secret-edits.sh",
        "block-dangerous-bash.sh",
        "route-perms-to-opus.sh",
        "tests-before-pr.sh",
        "warn-on-lockfile-edit.sh",
    ):
        content = (hooks_dir / hook_name).read_text()
        assert "command -v jq" in content, f"{hook_name} missing jq guard"


def test_include_superpowers_skills_question_removed(tmp_path: Path) -> None:
    """C5 regression: dead question must not appear in copier.yml."""
    copier_yml = (TEMPLATE_ROOT / "copier.yml").read_text()
    assert "include_superpowers_skills" not in copier_yml


def test_settings_deny_list_blocks_sensitive_reads(tmp_path: Path) -> None:
    dst = render(tmp_path)
    settings = json.loads((dst / ".claude" / "settings.json").read_text())
    deny = settings["permissions"]["deny"]
    assert any(".env" in entry for entry in deny)
    assert any("force" in entry for entry in deny)


# ---------------------------------------------------------------------------
# Superpowers integration
# ---------------------------------------------------------------------------


def test_superpowers_off_default_keeps_all_commands_and_subagents(tmp_path: Path) -> None:
    """Without Superpowers, the full v2 set ships."""
    dst = render(tmp_path, enable_superpowers=False)
    cmd_dir = dst / ".claude" / "commands"
    agent_dir = dst / ".claude" / "agents"
    # All v2 commands present
    for cmd in ("plan.md", "review.md", "tdd.md", "commit.md", "techdebt.md", "security-review.md"):
        assert (cmd_dir / cmd).exists(), f"missing {cmd}"
    # Superpowers shim absent
    assert not (cmd_dir / "review-with-superpowers.md").exists()
    # All four subagents present
    for agent in ("code-reviewer.md", "test-writer.md", "debugger.md", "security-auditor.md"):
        assert (agent_dir / agent).exists(), f"missing {agent}"
    # New skills absent (only ship when Superpowers is on)
    assert not (dst / ".claude" / "skills" / "design-review").exists()
    assert not (dst / ".claude" / "skills" / "spec-security-review").exists()


def test_superpowers_on_drops_redundant_commands(tmp_path: Path) -> None:
    dst = render(tmp_path, enable_superpowers=True)
    cmd_dir = dst / ".claude" / "commands"
    # Redundant commands removed
    for cmd in ("plan.md", "review.md", "tdd.md"):
        assert not (cmd_dir / cmd).exists(), f"{cmd} should be dropped when Superpowers is on"
    # Kept commands still present
    for cmd in ("commit.md", "techdebt.md", "security-review.md"):
        assert (cmd_dir / cmd).exists(), f"{cmd} should still be present"
    # New shim added
    assert (cmd_dir / "review-with-superpowers.md").exists()


def test_superpowers_on_drops_redundant_subagents(tmp_path: Path) -> None:
    dst = render(tmp_path, enable_superpowers=True)
    agent_dir = dst / ".claude" / "agents"
    for agent in ("code-reviewer.md", "test-writer.md", "debugger.md"):
        assert not (agent_dir / agent).exists(), f"{agent} should be dropped when Superpowers is on"
    # security-auditor stays — Superpowers has no equivalent
    assert (agent_dir / "security-auditor.md").exists()


def test_superpowers_on_ships_design_review_skill(tmp_path: Path) -> None:
    dst = render(tmp_path, enable_superpowers=True)
    skill = dst / ".claude" / "skills" / "design-review" / "SKILL.md"
    assert skill.exists()
    content = skill.read_text()
    # Description must NOT summarize workflow (per Superpowers writing-skills rule)
    # so we verify only triggering conditions, not workflow steps, appear in the description block
    assert "design-review" in content
    assert "User-Review-Gate" in content
    assert "frontend-design" in content


def test_superpowers_on_ships_spec_security_review_skill(tmp_path: Path) -> None:
    dst = render(tmp_path, enable_superpowers=True)
    skill = dst / ".claude" / "skills" / "spec-security-review" / "SKILL.md"
    assert skill.exists()
    content = skill.read_text()
    assert "Trigger keywords" in content
    # All six threat categories present
    for heading in (
        "Trust boundaries",
        "Authentication and authorization",
        "Secrets handling",
        "Injection and untrusted input",
        "External-service risks",
        "Privacy and data lifecycle",
    ):
        assert heading in content, f"missing threat-model section: {heading}"


def test_agents_md_is_terse_in_both_modes(tmp_path: Path) -> None:
    """AGENTS.md is injected with every prompt — must stay terse regardless of superpowers state."""
    for sp in (True, False):
        dst = render(tmp_path / f"sp-{sp}", enable_superpowers=sp)
        agents_md = (dst / "AGENTS.md").read_text()
        line_count = len(agents_md.strip().splitlines())
        assert line_count <= 25, (
            f"AGENTS.md grew to {line_count} lines (enable_superpowers={sp}); "
            f"target is ≤25. Procedural content belongs in skills/hooks, not in always-loaded context."
        )


def test_superpowers_on_agents_md_does_not_inline_procedural_prose(tmp_path: Path) -> None:
    """The Superpowers integration prose moved to a hook + routing skill — must NOT be in AGENTS.md."""
    dst = render(tmp_path, enable_superpowers=True)
    agents_md = (dst / "AGENTS.md").read_text()
    # These were the bloat keywords from the old AGENTS.md override block.
    forbidden = [
        "USER-LEVEL INSTRUCTIONS",
        "HIGHEST PRIORITY",
        "User-Review-Gate",
        "spec-security-review",  # name belongs in the skill + hook, not in always-loaded context
        "Conditionally invoke",
    ]
    for needle in forbidden:
        assert needle not in agents_md, (
            f"AGENTS.md still contains bloat keyword {needle!r} — should be in skill/hook"
        )
    # Workflow section must NOT mention /plan, /tdd, or bare /review (those were dropped).
    workflow_idx = agents_md.find("## Workflow")
    next_section_idx = agents_md.find("\n## ", workflow_idx + len("## Workflow"))
    workflow_section = agents_md[workflow_idx:next_section_idx]
    assert "/plan" not in workflow_section.replace("/sp-plan", "")
    workflow_no_compound = (
        workflow_section
        .replace("/review-with-superpowers", "")
        .replace("/security-review", "")
        .replace("/sp-review-request", "")
        .replace("/sp-review-receive", "")
    )
    assert "/review" not in workflow_no_compound


def test_superpowers_on_ships_routing_skill(tmp_path: Path) -> None:
    dst = render(tmp_path, enable_superpowers=True)
    routing_skill = dst / ".claude" / "skills" / "routing" / "SKILL.md"
    assert routing_skill.exists(), "routing skill should ship when superpowers is on"
    content = routing_skill.read_text()
    assert "session default" in content
    # All three aliases appear with the latest routing default
    assert "`opus`" in content and "`sonnet`" in content and "`haiku`" in content
    # Tier-pinned shim shortcuts referenced
    assert "/brainstorm" in content
    assert "/sp-implement" in content


def test_superpowers_on_ships_spec_review_trigger_hook(tmp_path: Path) -> None:
    dst = render(tmp_path, enable_superpowers=True, hooks=[
        "block-secret-edits", "block-dangerous-bash",
        "tests-before-pr", "route-perms-to-opus",
        "warn-on-lockfile-edit", "spec-review-trigger",
    ])
    hook_path = dst / ".claude" / "hooks" / "spec-review-trigger.sh"
    assert hook_path.exists()
    hook = hook_path.read_text()
    assert hook.splitlines()[0].startswith("#!"), "shebang missing"
    assert "docs/superpowers/specs" in hook
    assert "design-review" in hook
    assert "spec-security-review" in hook
    # Must wire into PostToolUse
    settings = json.loads((dst / ".claude" / "settings.json").read_text())
    assert "PostToolUse" in settings["hooks"]
    post_matchers = [e["matcher"] for e in settings["hooks"]["PostToolUse"]]
    assert any("Edit" in m and "Write" in m for m in post_matchers), (
        f"spec-review-trigger should match Edit|Write|MultiEdit, got {post_matchers!r}"
    )


def test_superpowers_on_ships_12_tier_pinned_shims(tmp_path: Path) -> None:
    dst = render(tmp_path, enable_superpowers=True)
    cmd_dir = dst / ".claude" / "commands"
    opus_shims = ["brainstorm.md", "sp-plan.md", "sp-debug.md", "sp-skill.md"]
    sonnet_shims = [
        "sp-worktree.md", "sp-implement.md", "sp-subagent.md", "sp-tdd.md",
        "sp-review-request.md", "sp-review-receive.md", "sp-finish.md", "sp-verify.md",
    ]
    for name in opus_shims:
        path = cmd_dir / name
        assert path.exists(), f"missing Opus shim {name}"
        assert "model: opus" in path.read_text(), f"{name} should pin Opus"
    for name in sonnet_shims:
        path = cmd_dir / name
        assert path.exists(), f"missing Sonnet shim {name}"
        assert "model: sonnet" in path.read_text(), f"{name} should pin Sonnet"


def test_superpowers_off_does_not_ship_shims_or_routing_or_spec_hook(tmp_path: Path) -> None:
    dst = render(tmp_path, enable_superpowers=False)
    cmd_dir = dst / ".claude" / "commands"
    for name in (
        "brainstorm.md", "sp-plan.md", "sp-debug.md", "sp-skill.md",
        "sp-worktree.md", "sp-implement.md", "sp-subagent.md", "sp-tdd.md",
        "sp-review-request.md", "sp-review-receive.md", "sp-finish.md", "sp-verify.md",
    ):
        assert not (cmd_dir / name).exists(), f"{name} should not ship without superpowers"
    assert not (dst / ".claude" / "skills" / "routing").exists()
    assert not (dst / ".claude" / "hooks" / "spec-review-trigger.sh").exists()


def test_superpowers_source_pcvelz_uses_extended_prefix(tmp_path: Path) -> None:
    dst = render(tmp_path, enable_superpowers=True, superpowers_source="pcvelz")
    brainstorm = (dst / ".claude" / "commands" / "brainstorm.md").read_text()
    assert "superpowers-extended-cc:brainstorming" in brainstorm
    assert "superpowers:brainstorming" not in brainstorm.replace("superpowers-extended-cc:", "")


def test_superpowers_on_denies_enter_plan_mode(tmp_path: Path) -> None:
    """pcvelz README requires EnterPlanMode in deny list — its brainstorming/writing-plans
    skills explicitly mandate normal mode, not Claude's native plan mode."""
    dst = render(tmp_path, enable_superpowers=True)
    settings = json.loads((dst / ".claude" / "settings.json").read_text())
    assert "EnterPlanMode" in settings["permissions"]["deny"], (
        "EnterPlanMode must be denied when Superpowers is on (per pcvelz README)"
    )


def test_superpowers_off_does_not_deny_enter_plan_mode(tmp_path: Path) -> None:
    """Without Superpowers, native plan mode is fine."""
    dst = render(tmp_path, enable_superpowers=False)
    settings = json.loads((dst / ".claude" / "settings.json").read_text())
    assert "EnterPlanMode" not in settings["permissions"]["deny"]


def test_superpowers_source_obra_uses_bare_prefix(tmp_path: Path) -> None:
    dst = render(tmp_path, enable_superpowers=True, superpowers_source="obra")
    brainstorm = (dst / ".claude" / "commands" / "brainstorm.md").read_text()
    assert "superpowers:brainstorming" in brainstorm
    assert "superpowers-extended-cc" not in brainstorm


def test_superpowers_off_agents_md_uses_v2_workflow(tmp_path: Path) -> None:
    dst = render(tmp_path, enable_superpowers=False)
    agents_md = (dst / "AGENTS.md").read_text()
    assert "Superpowers integration" not in agents_md
    workflow_idx = agents_md.find("## Workflow")
    next_section_idx = agents_md.find("\n## ", workflow_idx + len("## Workflow"))
    workflow_section = agents_md[workflow_idx:next_section_idx]
    assert "/plan" in workflow_section
    assert "/review" in workflow_section


def test_superpowers_off_does_not_ship_skills(tmp_path: Path) -> None:
    dst = render(tmp_path, enable_superpowers=False)
    assert not (dst / ".claude" / "skills" / "design-review").exists()
    assert not (dst / ".claude" / "skills" / "spec-security-review").exists()


# ---------------------------------------------------------------------------
# Model routing — single source of truth flows everywhere
# ---------------------------------------------------------------------------


def test_latest_routing_uses_three_aliases_with_1m(tmp_path: Path) -> None:
    """Default 'latest' routing + 1M: opus[1m] (high), sonnet[1m] (mid, session default), haiku (low — no 1M)."""
    dst = render(tmp_path)  # uses default latest + 1m=true
    settings = json.loads((dst / ".claude" / "settings.json").read_text())
    assert settings["model"] == "sonnet[1m]"

    # /commit and /techdebt -> low (haiku, no 1M)
    assert "model: haiku" in (dst / ".claude" / "commands" / "commit.md").read_text()
    assert "[1m]" not in (dst / ".claude" / "commands" / "commit.md").read_text()
    assert "model: haiku" in (dst / ".claude" / "commands" / "techdebt.md").read_text()

    # /review -> mid (sonnet[1m])
    assert "model: sonnet[1m]" in (dst / ".claude" / "commands" / "review.md").read_text()

    # /security-review -> high (opus[1m])
    assert "model: opus[1m]" in (dst / ".claude" / "commands" / "security-review.md").read_text()

    # security-auditor agent -> high (opus[1m])
    assert "model: opus[1m]" in (dst / ".claude" / "agents" / "security-auditor.md").read_text()


def test_1m_disabled_drops_the_suffix(tmp_path: Path) -> None:
    """enable_1m_context=false: tiers fall back to plain aliases."""
    dst = render(tmp_path,
                 enable_1m_context=False,
                 model_high="opus",
                 model_mid="sonnet",
                 model_low="haiku")
    settings = json.loads((dst / ".claude" / "settings.json").read_text())
    assert settings["model"] == "sonnet"
    # No [1m] suffix anywhere when disabled
    for path in (dst / ".claude" / "commands").glob("*.md"):
        assert "[1m]" not in path.read_text(), f"{path.name} still has [1m] suffix when disabled"
    for path in (dst / ".claude" / "agents").glob("*.md"):
        assert "[1m]" not in path.read_text(), f"{path.name} still has [1m] suffix when disabled"


def test_sonnet_only_routes_all_to_sonnet_1m(tmp_path: Path) -> None:
    """sonnet-only + 1M: every tier collapses to sonnet[1m]."""
    dst = render(tmp_path, model_routing="sonnet-only",
                 model_high="sonnet[1m]",
                 model_mid="sonnet[1m]",
                 model_low="sonnet[1m]")
    settings = json.loads((dst / ".claude" / "settings.json").read_text())
    assert settings["model"] == "sonnet[1m]"
    assert "model: sonnet[1m]" in (dst / ".claude" / "commands" / "commit.md").read_text()
    assert "model: sonnet[1m]" in (dst / ".claude" / "agents" / "security-auditor.md").read_text()
    sec_auditor = (dst / ".claude" / "agents" / "security-auditor.md").read_text()
    assert "opus" not in sec_auditor
    assert "haiku" not in (dst / ".claude" / "commands" / "commit.md").read_text()


def test_opus_heavy_routes_high_and_mid_to_opus_1m(tmp_path: Path) -> None:
    """opus-heavy + 1M: high+mid → opus[1m], low → sonnet[1m]."""
    dst = render(tmp_path, model_routing="opus-heavy",
                 model_high="opus[1m]",
                 model_mid="opus[1m]",
                 model_low="sonnet[1m]")
    settings = json.loads((dst / ".claude" / "settings.json").read_text())
    assert settings["model"] == "opus[1m]"
    assert "model: sonnet[1m]" in (dst / ".claude" / "commands" / "commit.md").read_text()
    assert "model: opus[1m]" in (dst / ".claude" / "commands" / "security-review.md").read_text()
    assert "model: opus[1m]" in (dst / ".claude" / "commands" / "review.md").read_text()


def test_routing_flows_to_ci_workflows(tmp_path: Path) -> None:
    """CI workflows derive their --model arg from the same tier vars (with [1m] preserved)."""
    dst = render(tmp_path)  # latest + 1m on
    review_yml = (dst / ".github" / "workflows" / "claude-review.yml").read_text()
    techdebt_yml = (dst / ".github" / "workflows" / "claude-techdebt.yml").read_text()
    # claude-review uses mid, claude-techdebt uses low
    assert "--model sonnet[1m]" in review_yml
    assert "--model haiku" in techdebt_yml
    assert "haiku[1m]" not in techdebt_yml  # haiku has no 1M variant


def test_routing_flows_to_perms_hook(tmp_path: Path) -> None:
    """The Opus scanning reference in the perms hook uses model_high."""
    dst = render(tmp_path)
    hook = (dst / ".claude" / "hooks" / "route-perms-to-opus.sh").read_text()
    # The (commented-out) scanning block references model_high
    assert "--model opus[1m]" in hook
    # And no orphaned Jinja syntax left over
    assert "{{ " not in hook and "{% " not in hook


def test_haiku_never_gets_1m_suffix(tmp_path: Path) -> None:
    """Hard guard: Haiku has no 1M variant, so [1m] must never be appended to it."""
    for routing in ("latest", "sonnet-only", "opus-heavy"):
        # latest is the only routing where low resolves to haiku; the others use sonnet for low.
        dst = render(tmp_path / f"r-{routing}", model_routing=routing,
                     model_high="opus[1m]" if routing != "sonnet-only" else "sonnet[1m]",
                     model_mid="opus[1m]" if routing == "opus-heavy" else "sonnet[1m]",
                     model_low="haiku" if routing == "latest" else "sonnet[1m]")
        for path in dst.rglob("*.md"):
            content = path.read_text(errors="ignore")
            assert "haiku[1m]" not in content, f"haiku[1m] in {path}: not a real alias"
        for path in dst.rglob("*.yml"):
            content = path.read_text(errors="ignore")
            assert "haiku[1m]" not in content, f"haiku[1m] in {path}: not a real alias"


def test_routing_table_lives_in_routing_skill_not_agents_md(tmp_path: Path) -> None:
    """Routing reference moved out of always-loaded AGENTS.md into an on-demand skill."""
    dst = render(tmp_path, model_routing="latest",
                 model_high="opus",
                 model_mid="sonnet",
                 model_low="haiku",
                 enable_superpowers=True)
    agents_md = (dst / "AGENTS.md").read_text()
    # Routing reference table no longer in AGENTS.md
    assert "## Model routing" not in agents_md
    routing_skill = dst / ".claude" / "skills" / "routing" / "SKILL.md"
    assert routing_skill.exists()
    content = routing_skill.read_text()
    # Tier table is in the skill
    assert "session default" in content
    assert "`opus`" in content
    assert "`sonnet`" in content
    assert "`haiku`" in content
    assert "high" in content and "mid" in content and "low" in content


def test_no_hardcoded_model_ids_anywhere(tmp_path: Path) -> None:
    """Regression guard: scaffold must use aliases, not pinned model IDs."""
    dst = render(tmp_path)
    import re
    pattern = re.compile(r"claude-(opus|sonnet|haiku)-\d")
    for path in dst.rglob("*"):
        if path.is_file() and path.suffix in (".md", ".yml", ".yaml", ".json", ".sh"):
            content = path.read_text(errors="ignore")
            match = pattern.search(content)
            if match:
                # Allow a single mention as documentation example in AGENTS.md routing section
                if path.name == "AGENTS.md" and "pin a specific ID" in content:
                    continue
                raise AssertionError(
                    f"Hardcoded model ID {match.group(0)!r} found in "
                    f"{path.relative_to(dst)} — use an alias instead."
                )


def test_no_orphan_jinja_in_any_rendered_file(tmp_path: Path) -> None:
    """Catch-all: no rendered file should contain unrendered {{ ... }} or {% ... %}."""
    dst = render(tmp_path)
    for path in dst.rglob("*"):
        if path.is_file() and path.suffix in (".md", ".yml", ".yaml", ".json", ".sh"):
            content = path.read_text(errors="ignore")
            # Allow GitHub Actions ${{ ... }} which is escaped via Copier as ${{ '{{' }}
            # After rendering it appears as ${{ ... }} which we should not flag
            # So we check for bare {{ or {% (without the $ prefix)
            for line_num, line in enumerate(content.splitlines(), 1):
                # strip GitHub Actions interpolation
                line_clean = line.replace("${{", "").replace("$  {{", "")
                if "{{ " in line_clean or "{%" in line_clean:
                    raise AssertionError(
                        f"Orphan Jinja in {path.relative_to(dst)}:{line_num}: {line!r}"
                    )
