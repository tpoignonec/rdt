"""Command runner — subprocess execution and Dagger pipeline wrappers.

Centralises:
  - ``run_command()`` for host-side subprocess calls.
  - ``run_dagger_pipeline()`` for Dagger async pipelines with
    uniform error handling.
  - ``make_clean_env()`` to strip virtualenv entries from PATH
    so that the system ROS 2 Python is used.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any, Awaitable, Callable

from rdt.core.console import abort, debug, warning


def make_clean_env() -> dict[str, str]:
    """Return a copy of ``os.environ`` with the active venv stripped out.

    When ``rdt`` is installed in a virtualenv the venv Python takes
    precedence on ``PATH``.  CMake / ament then use that interpreter,
    which does **not** have ``catkin_pkg`` and friends.  Removing the
    venv entries lets the ROS 2 system Python be picked up instead.
    """
    env = os.environ.copy()
    venv = env.pop("VIRTUAL_ENV", None)
    env.pop("PYTHONHOME", None)
    if venv:
        path_dirs = env.get("PATH", "").split(os.pathsep)
        clean_path = os.pathsep.join(d for d in path_dirs if not d.startswith(venv))
        env["PATH"] = clean_path
        warning(
            f"Detected active virtualenv ({venv}). "
            "Stripping it from the environment so that the "
            "system ROS 2 Python is used."
        )
        debug(f"Clean PATH: {clean_path}")
    else:
        debug("No active virtualenv detected")
    return env


def run_command(
    cmd: list[str],
    *,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
    capture: bool = False,
    dry_run: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a shell command with optional capture and error handling.

    Parameters
    ----------
    cmd:
        Command and arguments.
    cwd:
        Working directory.
    env:
        Environment variables (default: inherit).
    check:
        Raise on non-zero exit code.
    capture:
        Capture stdout/stderr instead of streaming.
    dry_run:
        Print the command but don't execute it.
    """
    from rich.console import Console

    console = Console()
    console.print(f"[dim]$ {' '.join(cmd)}[/dim]")

    if dry_run:
        return subprocess.CompletedProcess(cmd, 0, "", "")

    try:
        return subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            check=check,
            text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
        )
    except subprocess.CalledProcessError as exc:
        abort(f"Command failed (exit {exc.returncode}): {' '.join(cmd)}")


def run_dagger_pipeline(
    pipeline_fn: Callable[..., Awaitable[Any]],
    *,
    label: str = "pipeline",
) -> None:
    """Run an async Dagger pipeline with uniform error handling.

    Parameters
    ----------
    pipeline_fn:
        An ``async def`` that receives no arguments and runs the
        Dagger pipeline.
    label:
        Human-readable name used in error messages.
    """
    try:
        import dagger  # noqa: F401
    except ImportError:
        abort("dagger-io is not installed.  pip install rdt[ci]")

    import anyio
    import dagger

    try:
        anyio.run(pipeline_fn)
    except dagger.QueryError as exc:
        abort(f"{label} failed:\n{exc}")
    except subprocess.TimeoutExpired:
        # Dagger CLI session cleanup can timeout — harmless if the
        # pipeline itself completed.  Log rather than silently swallow.
        warning(f"{label}: Dagger session cleanup timed out (usually harmless)")
    except Exception as exc:
        abort(f"{label} failed ({type(exc).__name__}): {exc}")
