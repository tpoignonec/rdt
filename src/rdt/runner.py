from __future__ import annotations

import os
import shlex
import subprocess
from collections.abc import Sequence

from rdt.console import debug


class CommandError(Exception):
    def __init__(self, cmd: str, returncode: int) -> None:
        self.returncode = returncode
        super().__init__(f"Command failed (exit {returncode}): {cmd}")


def _clean_env(env: dict[str, str]) -> dict[str, str]:
    """Remove active virtualenv entries so ROS system Python is used."""
    venv = env.pop("VIRTUAL_ENV", None)
    env.pop("PYTHONHOME", None)
    if venv:
        path_dirs = env.get("PATH", "").split(os.pathsep)
        env["PATH"] = os.pathsep.join(d for d in path_dirs if not d.startswith(venv))
        debug(f"Stripped active virtualenv from PATH: {env['PATH']}")
    return env


def run(
    cmd: Sequence[str],
    *,
    cwd: str | None = None,
    extra_env: dict[str, str] | None = None,
    input: str | None = None,
    check: bool = True,
) -> int:
    """Run a command, streaming output to the terminal. Returns returncode."""
    env = _clean_env(os.environ.copy())
    if extra_env:
        env.update(extra_env)
    debug(f"$ {shlex.join(cmd)}")
    result = subprocess.run(
        list(cmd),
        cwd=cwd,
        env=env,
        input=input,
        text=input is not None,
    )
    if check and result.returncode != 0:
        raise CommandError(shlex.join(cmd), result.returncode)
    return result.returncode


def run_shell(
    script: str,
    *,
    cwd: str | None = None,
    extra_env: dict[str, str] | None = None,
    check: bool = True,
) -> int:
    """Run a bash script, streaming output to the terminal. Returns returncode."""
    env = _clean_env(os.environ.copy())
    if extra_env:
        env.update(extra_env)
    debug(f"$ {script}")
    result = subprocess.run(["bash", "-c", script], cwd=cwd, env=env)
    if check and result.returncode != 0:
        raise CommandError(script, result.returncode)
    return result.returncode
