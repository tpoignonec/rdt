"""Tests for the runner environment helpers."""

from __future__ import annotations

from rdt.runner import _clean_env


def test_clean_env_strips_virtualenv() -> None:
    env = {
        "VIRTUAL_ENV": "/home/user/.venv",
        "PATH": "/home/user/.venv/bin:/usr/local/bin:/usr/bin",
        "PYTHONHOME": "/home/user/.venv",
    }

    cleaned = _clean_env(env.copy())

    assert "VIRTUAL_ENV" not in cleaned
    assert "PYTHONHOME" not in cleaned
    assert cleaned["PATH"] == "/usr/local/bin:/usr/bin"


def test_clean_env_preserves_path_without_virtualenv() -> None:
    env = {
        "PATH": "/usr/local/bin:/usr/bin",
        "PYTHONHOME": "/some/pythonhome",
    }

    cleaned = _clean_env(env.copy())

    assert cleaned["PATH"] == "/usr/local/bin:/usr/bin"
    assert "PYTHONHOME" not in cleaned
