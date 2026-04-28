"""
Shared pytest configuration for claude-scaffold tests.

Registers the `live` marker, gates `live`-marked tests on a usable
`claude` CLI plus working Anthropic auth (env-var or active login),
and exposes a `claude_p` fixture that drives headless Claude Code
against a rendered scaffold.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "live: hits the real Anthropic API; opt-in (run with `pytest -m live`)",
    )


def _claude_is_logged_in() -> bool:
    """True if `claude auth status` reports a usable subscription/login."""
    try:
        proc = subprocess.run(
            ["claude", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    if proc.returncode != 0:
        return False
    try:
        return bool(json.loads(proc.stdout).get("loggedIn"))
    except (json.JSONDecodeError, AttributeError):
        return False


@pytest.fixture(autouse=True)
def _gate_live_tests(request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("live") is None:
        return
    if shutil.which("claude") is None:
        pytest.skip("`claude` CLI not on PATH")
    # Accept either an API key OR an active `claude auth` login (Pro/Max
    # subscription, OAuth, etc.) — `claude -p` works with either.
    if not os.environ.get("ANTHROPIC_API_KEY") and not _claude_is_logged_in():
        pytest.skip("no Anthropic auth: set ANTHROPIC_API_KEY or run `claude auth login`")


@pytest.fixture
def claude_p():
    """Run `claude -p` against a rendered scaffold and return parsed events.

    Returns a callable `(rendered_dir, prompt, *, timeout=120)` that yields
    a dict with:

      - events: list of stream-json events (dicts)
      - init_model: `model` field from the `system/init` event — the
        CLI-resolved alias including any `[1m]` suffix
        (e.g. "claude-sonnet-4-6[1m]")
      - assistant_model: `message.model` from the first assistant event —
        the actual model id that served the request (no `[1m]` suffix;
        that's a CLI alias, not an API model id)
      - stdout / stderr / returncode: raw subprocess outputs
    """

    def _run(
        rendered_dir: Path,
        prompt: str,
        *,
        timeout: int = 120,
    ) -> dict[str, Any]:
        # `--tools ""` disables all tools (no side effects on the rendered
        # scaffold). It's variadic, so it MUST be followed by another --flag,
        # never by the bare prompt — otherwise it eats the prompt as a tool
        # name and the CLI errors with "Input must be provided".
        cmd = [
            "claude",
            "-p",
            "--tools", "",
            "--output-format", "stream-json",
            "--include-partial-messages",
            "--verbose",
            "--no-session-persistence",
            "--max-budget-usd", "0.05",
            "--permission-mode", "bypassPermissions",
            prompt,
        ]

        proc = subprocess.run(
            cmd,
            cwd=str(rendered_dir),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        events: list[dict[str, Any]] = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        init_model: str | None = None
        for ev in events:
            if ev.get("type") == "system" and ev.get("subtype") == "init":
                init_model = ev.get("model")
                break

        assistant_model: str | None = None
        for ev in events:
            msg = ev.get("message") or {}
            if msg.get("role") == "assistant" and msg.get("model"):
                assistant_model = msg["model"]
                break

        return {
            "events": events,
            "init_model": init_model,
            "assistant_model": assistant_model,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
        }

    return _run
