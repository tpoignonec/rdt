"""rdt test — colcon test."""

from __future__ import annotations

import click

from rdt.commands._ros import colcon_test_cmd, source_ros_distro
from rdt.config import load_config
from rdt.console import info, success
from rdt.runner import run_shell


@click.command()
@click.option("--ros-distro", default=None, help="ROS 2 distribution.")
@click.option("--install-dir", default=None, help="ROS install prefix to source.")
@click.option(
    "--retest-until-pass",
    default=None,
    type=int,
    help="Pass --retest-until-pass N to colcon (retry N times on failure).",
)
@click.option("--colcon-args", multiple=True, metavar="ARG", help="Extra colcon args (repeatable).")
@click.option("--packages-select", multiple=True, metavar="PKG", help="Test only these packages.")
def test_cmd(
    ros_distro: str | None,
    install_dir: str | None,
    retest_until_pass: int | None,
    colcon_args: tuple[str, ...],
    packages_select: tuple[str, ...],
) -> None:
    """Run tests with colcon."""
    config = load_config()
    distro = ros_distro or config.ros_distro
    # inst_dir = install_dir or config.install_dir
    retries = retest_until_pass if retest_until_pass is not None else config.test.retest_until_pass
    colcon = list(colcon_args) if colcon_args else list(config.test.colcon_args)
    pkgs = list(packages_select) if packages_select else list(config.test.packages_select)

    # Source the system ROS distro and then overlay workspace install if available.
    source = f"{source_ros_distro(distro)} && {{ . install/setup.bash 2>/dev/null || true; }}"
    test_str = colcon_test_cmd(retries, colcon, pkgs)
    info(f"Running tests (distro={distro})...")
    run_shell(f"{source} && {test_str} && colcon test-result --verbose")
    success("All tests passed.")
