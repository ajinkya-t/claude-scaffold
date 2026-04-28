"""
Live-runtime verification of model routing.

These tests render the scaffold, then drive `claude -p` headless
against the rendered project and assert that the assistant message
on the wire was actually handled by the expected model family
(opus / sonnet / haiku) for each tier under each `model_routing` x
`enable_1m_context` combo.

Opt-in. Skipped unless `ANTHROPIC_API_KEY` is set or the `claude` CLI
has an active login (Pro/Max), and unless the CLI itself is on PATH.
Deselected by default via `addopts = "-m 'not live'"` in pyproject.toml.
Run with:

    pytest -m live              # uses `claude auth` login if present
    ANTHROPIC_API_KEY=... pytest -m live

Cost: ~17 API calls, <$0.40 per run.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from test_template import render


NOOP_PROMPT = "Reply with exactly the word OK and nothing else."


def _family(model_id: str | None) -> str:
    """Map a resolved model id (e.g. 'claude-sonnet-4-6') to its family."""
    if not model_id:
        return ""
    lower = model_id.lower()
    for fam in ("opus", "sonnet", "haiku"):
        if fam in lower:
            return fam
    return model_id


def _model_answers(routing: str, enable_1m: bool) -> dict[str, str]:
    """Compute model_high/mid/low Copier answers for a routing x 1M combo.

    Mirrors the resolution that copier.yml does at render time.
    """
    suffix = "[1m]" if enable_1m else ""
    if routing == "latest":
        return {
            "model_high": f"opus{suffix}",
            "model_mid": f"sonnet{suffix}",
            "model_low": "haiku",  # haiku has no 1M variant
        }
    if routing == "sonnet-only":
        return {
            "model_high": f"sonnet{suffix}",
            "model_mid": f"sonnet{suffix}",
            "model_low": f"sonnet{suffix}",
        }
    if routing == "opus-heavy":
        return {
            "model_high": f"opus{suffix}",
            "model_mid": f"opus{suffix}",
            "model_low": f"sonnet{suffix}",
        }
    raise ValueError(f"unknown routing: {routing!r}")


# (routing, enable_1m, enable_superpowers, prompt, expected_family, expect_1m_suffix)
#
# Surfaces probed:
# - NOOP_PROMPT      session default (settings.json `model`)
# - /commit          low tier  — commit.md frontmatter
# - /security-review high tier — security-review.md frontmatter
# - /brainstorm      high tier — sp-shim (only ships with enable_superpowers)
# - /sp-implement    mid tier  — sp-shim (only ships with enable_superpowers)
#
# expect_1m_suffix is enforced only when prompt == NOOP_PROMPT (session
# default), via the `system/init` event's `model` field which the CLI emits
# as e.g. "claude-sonnet-4-6[1m]" when the 1M variant is in effect. For
# slash-command turns the field is ignored — the static suite already
# verifies that slash-command frontmatter carries the right `[1m]` strings.
MATRIX: list[tuple[str, bool, bool, str, str, bool]] = [
    # ---------------- enable_superpowers = False (12 cases) ----------------
    # latest + 1M  (high=opus[1m], mid=sonnet[1m], low=haiku — haiku has no 1M)
    ("latest",      True,  False, NOOP_PROMPT,         "sonnet", True),
    ("latest",      True,  False, "/commit",           "haiku",  False),
    ("latest",      True,  False, "/security-review",  "opus",   True),
    # latest, no 1M
    ("latest",      False, False, NOOP_PROMPT,         "sonnet", False),
    ("latest",      False, False, "/commit",           "haiku",  False),
    ("latest",      False, False, "/security-review",  "opus",   False),
    # sonnet-only + 1M  (everything sonnet[1m])
    ("sonnet-only", True,  False, NOOP_PROMPT,         "sonnet", True),
    ("sonnet-only", True,  False, "/commit",           "sonnet", True),
    ("sonnet-only", True,  False, "/security-review",  "sonnet", True),
    # opus-heavy + 1M  (high=opus[1m], mid=opus[1m], low=sonnet[1m])
    ("opus-heavy",  True,  False, NOOP_PROMPT,         "opus",   True),
    ("opus-heavy",  True,  False, "/commit",           "sonnet", True),
    ("opus-heavy",  True,  False, "/security-review",  "opus",   True),

    # ---------------- enable_superpowers = True (5 cases) ----------------
    # Same default routing (latest + 1M), proves the existing surfaces still
    # route correctly when Superpowers is on, AND that the new sp-shims
    # (one high, one mid) honour their `model:` frontmatter.
    ("latest",      True,  True,  NOOP_PROMPT,         "sonnet", True),
    ("latest",      True,  True,  "/commit",           "haiku",  False),
    ("latest",      True,  True,  "/security-review",  "opus",   True),
    ("latest",      True,  True,  "/brainstorm",       "opus",   True),
    ("latest",      True,  True,  "/sp-implement",     "sonnet", True),
]


@pytest.mark.live
@pytest.mark.parametrize(
    "routing,enable_1m,enable_superpowers,prompt,expected_family,expect_1m_suffix",
    MATRIX,
    ids=[
        f"{routing}"
        f"-{'1m' if e1m else 'no1m'}"
        f"-{'sp' if sp else 'nosp'}"
        f"-{prompt.split()[0].lstrip('/') or 'session'}"
        f"-{fam}"
        for routing, e1m, sp, prompt, fam, _ in MATRIX
    ],
)
def test_runtime_model_matches_tier(
    tmp_path: Path,
    claude_p,
    routing: str,
    enable_1m: bool,
    enable_superpowers: bool,
    prompt: str,
    expected_family: str,
    expect_1m_suffix: bool,
) -> None:
    answers = _model_answers(routing, enable_1m)
    rendered = render(
        tmp_path,
        model_routing=routing,
        enable_1m_context=enable_1m,
        enable_superpowers=enable_superpowers,
        **answers,
    )

    result = claude_p(rendered, prompt)

    # 1) tier check — the family of the actual API model that served the turn.
    assert result["assistant_model"], (
        f"no assistant message in stream-json output\n"
        f"returncode={result['returncode']}\n"
        f"stdout (head):\n{result['stdout'][:1500]}\n"
        f"stderr (head):\n{result['stderr'][:1500]}"
    )
    actual_family = _family(result["assistant_model"])
    assert actual_family == expected_family, (
        f"tier-mismatch for routing={routing!r} 1m={enable_1m} prompt={prompt!r}\n"
        f"  expected family: {expected_family}\n"
        f"  actual model:    {result['assistant_model']!r} (family={actual_family!r})"
    )

    # 2) [1m] suffix check — only meaningful for the session-default prompt.
    # Slash commands rebind the model per-turn; the `system/init` event only
    # reports the session config, not the per-turn override. The static suite
    # already verifies that slash-command `model:` frontmatter contains the
    # `[1m]` string under the right Copier answers.
    if prompt == NOOP_PROMPT:
        init = result["init_model"] or ""
        if expect_1m_suffix:
            assert "[1m]" in init, (
                f"expected session init model to carry `[1m]` suffix for "
                f"routing={routing!r} 1m={enable_1m}, got init_model={init!r}"
            )
        else:
            assert "[1m]" not in init, (
                f"expected NO `[1m]` suffix in session init model for "
                f"routing={routing!r} 1m={enable_1m}, got init_model={init!r}"
            )
