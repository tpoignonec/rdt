"""rdt deps — install workspace dependencies (vcs, apt, rosdep)."""
from __future__ import annotations

import click

from rdt.commands._ros import find_repos_file, source_ros
from rdt.config import load_config
from rdt.console import info, success
from rdt.runner import run, run_shell


@click.command()
@click.option("--ros-distro", default=None, help="ROS 2 distribution.")
@click.option("--repos-file", default=None, metavar="FILE", help="vcstool .repos file.")
@click.option("--skip-vcs", is_flag=True, help="Skip vcs import.")
@click.option("--skip-apt", is_flag=True, help="Skip apt update/upgrade.")
@click.option("--skip-rosdep", is_flag=True, help="Skip rosdep install.")
def deps_cmd(
    ros_distro: str | None,
    repos_file: str | None,
    skip_vcs: bool,
    skip_apt: bool,
    skip_rosdep: bool,
) -> None:
    """Install workspace dependencies (vcs, apt, rosdep)."""
    config = load_config()
    distro = ros_distro or config.ros_distro

    if not skip_vcs:
        repos = find_repos_file(repos_file)
        if repos:
            info(f"Importing repositories from {repos.name}...")
            run(["vcs", "import", "--recursive", "--input", str(repos)])
        else:
            info("No .repos file found, skipping vcs import.")

    if not skip_apt:
        info("Running apt update / upgrade...")
        run_shell("apt-get update && apt-get upgrade -y")

    if not skip_rosdep:
        info(f"Installing rosdep dependencies (distro={distro})...")
        run_shell(
            f"{source_ros(config.install_dir, distro)}"
            " && (rosdep init 2>/dev/null || true)"
            f" && rosdep update --rosdistro {distro}"
            f" && rosdep install --from-paths . --ignore-src -y --rosdistro {distro}"
        )

    success("Dependencies ready.")
