"""CLI entry point for rdt (Robotics Dev Tools).

Discovers installed recipes via entry-points and registers their
commands under a single Click group.  The ``init`` command is
built-in (not recipe-specific).

Usage::

    rdt --help
    rdt init [--recipe ros2] [--template etherlab]
    rdt local build --ros-distro jazzy
    rdt ci deploy --image-tag 1.0.0
    rdt demo launch --image my-image
"""

from __future__ import annotations

import click

from rdt import __version__
from rdt.core.console import set_verbose


@click.group()
@click.version_option(version=__version__, prog_name="rdt")
@click.option(
    "-v", "--verbose", is_flag=True, default=False,
    help="Enable verbose output.",
)
def cli(verbose: bool) -> None:
    """rdt — Robotics Dev Tools.

    A unified, recipe-driven CLI for build, test, CI/CD, and demo workflows.
    """
    set_verbose(verbose)


# ── Built-in commands ─────────────────────────────────────────────────

from rdt.init import init_cmd  # noqa: E402

cli.add_command(init_cmd)


# ── Recipe-driven commands ────────────────────────────────────────────
# Each recipe registers its own sub-groups (local, ci, demo, …)

from rdt.recipes import discover_recipes  # noqa: E402

for _recipe in discover_recipes().values():
    _recipe.register_commands(cli)


if __name__ == "__main__":
    cli()
