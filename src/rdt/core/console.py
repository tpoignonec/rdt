"""Console helpers — rich-based output with a structured logging feel.

All user-facing output goes through these helpers so that:
  - Verbosity is controlled in one place.
  - Output is consistent across commands.
  - Tests can patch a single module.
"""

from __future__ import annotations

import logging
import sys
from typing import NoReturn

from rich.console import Console


_console = Console()
_err_console = Console(stderr=True, style='bold red')

# ── Verbosity ─────────────────────────────────────────────────────────

_debug_logging: bool = False
_verbose: bool = False


def set_verbose(enabled: bool = True) -> None:
    """Enable or disable verbose (debug-level) output globally."""
    global _verbose  # noqa: PLW0603
    _verbose = enabled
    if _debug_logging:
        logging.basicConfig(
            level=logging.DEBUG, format='%(name)s: %(message)s')
    else:
        logging.basicConfig(
            level=logging.INFO, format='%(name)s: %(message)s')


def is_verbose() -> bool:
    """Return whether verbose output is enabled."""
    return _verbose


# ── Output primitives ─────────────────────────────────────────────────


def debug(message: str) -> None:
    """Print a debug message (only when ``--verbose`` is active)."""
    if _verbose:
        _console.print(f'[dim]🔍 {message}[/dim]')
    # logger.debug(message)


def info(message: str) -> None:
    """Print an informational message."""
    _console.print(f'[bold cyan]ℹ[/bold cyan]  {message}')
    # logger.info(message)  # Only log to file, not console


def success(message: str) -> None:
    """Print a success message."""
    _console.print(f'[bold green]✔[/bold green]  {message}')
    # logger.info(message)


def warning(message: str) -> None:
    """Print a warning message."""
    _console.print(f'[bold yellow]⚠[/bold yellow]  {message}')
    # logger.warning(message)


def abort(message: str) -> NoReturn:
    """Print an error message and exit with code 1."""
    _err_console.print(f'[bold red]Error:[/bold red] {message}')
    # logger.error(message)
    sys.exit(1)
