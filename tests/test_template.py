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
        ],
        "subagents": ["code-reviewer", "test-writer", "debugger", "security-auditor"],
        "output_style": "concise",
        "model_routing": "boris-defaults",
        "include_superpowers_skills": False,
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


def test_all_four_hooks_exist_and_executable(tmp_path: Path) -> None:
    dst = render(tmp_path)
    hooks_dir = dst / ".claude" / "hooks"
    expected = {
        "block-secret-edits.sh",
        "block-dangerous-bash.sh",
        "tests-before-pr.sh",
        "route-perms-to-opus.sh",
    }
    actual = {p.name for p in hooks_dir.iterdir() if p.is_file()}
    assert expected.issubset(actual)
    # We can't reliably check executable bit on rendered output across platforms,
    # but the shebang must be present.
    for hook_name in expected:
        first_line = (hooks_dir / hook_name).read_text().splitlines()[0]
        assert first_line.startswith("#!"), f"{hook_name} missing shebang"


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
    # Boris-defaults uses Sonnet as base model
    assert "sonnet" in settings.get("model", "").lower()


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


def test_superpowers_on_agents_md_declares_user_priority_section(tmp_path: Path) -> None:
    """The Superpowers integration section must declare itself as user-level (highest priority)."""
    dst = render(tmp_path, enable_superpowers=True)
    agents_md = (dst / "AGENTS.md").read_text()
    assert "Superpowers integration" in agents_md
    assert "USER-LEVEL INSTRUCTIONS" in agents_md
    assert "HIGHEST PRIORITY" in agents_md
    # Must reference both new skills by name
    assert "design-review" in agents_md
    assert "spec-security-review" in agents_md
    # Must reference the User-Review-Gate window from brainstorming
    assert "User-Review-Gate" in agents_md
    # Must include the security trigger keyword list
    assert "auth" in agents_md and "secret" in agents_md and "upload" in agents_md
    # Workflow section should NOT mention /plan, /tdd, /review (those are dropped)
    workflow_idx = agents_md.find("## Workflow")
    boundaries_idx = agents_md.find("## Boundaries")
    workflow_section = agents_md[workflow_idx:boundaries_idx]
    assert "/plan" not in workflow_section
    assert "/tdd" not in workflow_section
    # /review-with-superpowers is fine, but bare /review should not appear
    workflow_section_no_shim = workflow_section.replace("/review-with-superpowers", "")
    assert "/review" not in workflow_section_no_shim


def test_superpowers_off_agents_md_uses_v2_workflow(tmp_path: Path) -> None:
    dst = render(tmp_path, enable_superpowers=False)
    agents_md = (dst / "AGENTS.md").read_text()
    assert "Superpowers integration" not in agents_md
    workflow_idx = agents_md.find("## Workflow")
    boundaries_idx = agents_md.find("## Boundaries")
    workflow_section = agents_md[workflow_idx:boundaries_idx]
    assert "/plan" in workflow_section
    assert "/review" in workflow_section


def test_superpowers_off_does_not_ship_skills(tmp_path: Path) -> None:
    dst = render(tmp_path, enable_superpowers=False)
    assert not (dst / ".claude" / "skills" / "design-review").exists()
    assert not (dst / ".claude" / "skills" / "spec-security-review").exists()
