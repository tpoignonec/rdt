"""Rocker demo launcher.

Uses Click sub-group: ``rdt demo launch``.
"""

from __future__ import annotations

import shutil

import click

from rdt.core.config import resolve_config
from rdt.core.console import abort, info, success
from rdt.core.runner import run_command
from rdt.recipes.ros2.models import DemoConfig


def _launch_demo(config: DemoConfig) -> None:
    """Launch a ROS 2 demo container via Rocker."""
    if shutil.which("rocker") is None:
        abort("rocker is not installed.  pip install rdt[demo]")

    info(f"Launching demo (image={config.image})")

    cmd: list[str] = ["rocker"]
    if config.x11:
        cmd.append("--x11")
    if config.gpu:
        cmd.append("--nvidia")
    if config.network != "host":
        cmd.extend(["--network", config.network])
    cmd.extend(config.extra_args)
    cmd.append(config.image)

    run_command(cmd)
    success("Demo session ended.")


# ── Click sub-group ───────────────────────────────────────────────────


@click.group("demo")
def demo_group() -> None:
    """Demo launcher commands (Rocker-based)."""


@demo_group.command("launch")
@click.option("--image", default=None, help="Docker image to launch.")
@click.option("--x11", is_flag=True, default=False, help="Enable X11 forwarding.")
@click.option("--gpu", is_flag=True, default=False, help="Enable GPU passthrough (nvidia).")
@click.option(
    "--network", default=None,
    type=click.Choice(["host", "bridge", "none"]),
    help="Docker network mode.",
)
def demo_launch_cmd(
    image: str | None, x11: bool, gpu: bool, network: str | None,
) -> None:
    """Launch Rocker demo with X11/GPU support."""
    config = resolve_config(
        DemoConfig, "demo",
        image=image,
        x11=x11 if x11 else None,
        gpu=gpu if gpu else None,
        network=network,
    )
    _launch_demo(config)
