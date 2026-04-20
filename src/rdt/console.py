from __future__ import annotations

from rich.console import Console
from rich.theme import Theme

_theme = Theme({
    "info": "cyan",
    "success": "bold green",
    "warning": "yellow",
    "error": "bold red",
    "debug": "dim",
})

_console = Console(theme=_theme)
_err_console = Console(stderr=True, theme=_theme)
_verbose = False


def set_verbose(v: bool) -> None:
    global _verbose
    _verbose = v


def is_verbose() -> bool:
    return _verbose


def info(msg: str) -> None:
    _console.print(f"[info]{msg}[/info]")


def success(msg: str) -> None:
    _console.print(f"[success]{msg}[/success]")


def warn(msg: str) -> None:
    _console.print(f"[warning]Warning: {msg}[/warning]")


def error(msg: str) -> None:
    _err_console.print(f"[error]Error: {msg}[/error]")


def debug(msg: str) -> None:
    if _verbose:
        _console.print(f"[debug]  {msg}[/debug]")


def abort(msg: str) -> None:
    error(msg)
    raise SystemExit(1)
