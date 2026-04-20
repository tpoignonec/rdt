"""rdt build — colcon build."""
from __future__ import annotations

import click

from rdt.commands._ros import colcon_build_cmd, source_ros
from rdt.config import load_config
from rdt.console import info, success
from rdt.runner import run_shell


@click.command()
@click.option("--ros-distro", default=None, help="ROS 2 distribution.")
@click.option("--install-dir", default=None, help="ROS install prefix to source.")
@click.option("--install-base", default=None, help="colcon --install-base (artifact output dir).")
@click.option("--cmake-args", multiple=True, metavar="ARG", help="Extra CMake args (repeatable).")
@click.option("--cmake-build-type", default=None, help="CMake build type (e.g. Release).")
@click.option("--colcon-args", multiple=True, metavar="ARG", help="Extra colcon args (repeatable).")
@click.option("--packages-select", multiple=True, metavar="PKG", help="Build only these packages.")
def build_cmd(
    ros_distro: str | None,
    install_dir: str | None,
    install_base: str | None,
    cmake_args: tuple[str, ...],
    cmake_build_type: str | None,
    colcon_args: tuple[str, ...],
    packages_select: tuple[str, ...],
) -> None:
    """Build the ROS2 workspace with colcon."""
    config = load_config()
    distro = ros_distro or config.ros_distro
    inst_dir = install_dir or config.install_dir
    inst_base = install_base or config.build.install_base
    cmake = list(cmake_args) if cmake_args else list(config.build.cmake_args)
    build_type = cmake_build_type or config.build.cmake_build_type
    colcon = list(colcon_args) if colcon_args else list(config.build.colcon_args)
    pkgs = list(packages_select) if packages_select else list(config.build.packages_select)

    cmd = colcon_build_cmd(inst_base, cmake, build_type, colcon, pkgs)
    info(f"Building workspace (distro={distro}, install-base={inst_base})...")
    run_shell(f"{source_ros(inst_dir, distro)} && {cmd}")
    success("Build complete.")
