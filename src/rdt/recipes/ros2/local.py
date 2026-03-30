"""Local build and test commands (native colcon on the host).

Uses Click sub-groups: ``rdt local build``, ``rdt local test``.
"""

from __future__ import annotations

import os
import shutil

import click

from rdt.core.config import resolve_config
from rdt.core.console import abort, debug, info, success
from rdt.core.runner import make_clean_env, run_command
from rdt.recipes.ros2.commands import (
    COLCON_TEST_RESULT_CMD,
    colcon_build_cmd,
    colcon_test_cmd,
    source_ros_setup,
)
from rdt.recipes.ros2.models import BuildConfig, TestingConfig


def _ensure_colcon(env: dict[str, str]) -> None:
    """Abort if colcon is not reachable in the given environment."""
    if shutil.which("colcon", path=env.get("PATH")) is None:
        abort(
            "colcon is not installed or not on PATH. "
            "Make sure you have sourced your ROS 2 environment."
        )


def _source_setup_prefix(install_dir: str, ros_distro: str) -> str:
    """Return the shell snippet that sources the ROS 2 setup file."""
    setup = os.path.join(install_dir, ros_distro, "setup.bash")
    if not os.path.isfile(setup):
        abort(f"ROS 2 setup file not found: {setup}")
    return source_ros_setup(install_dir, ros_distro)


# ── Business logic ────────────────────────────────────────────────────


def _build_locally(config: BuildConfig) -> None:
    """Build a ROS 2 workspace on the host using colcon."""
    clean_env = make_clean_env()
    _ensure_colcon(clean_env)

    info(
        f"Building ROS 2 workspace "
        f"(distro={config.ros_distro}, install_dir={config.install_dir})"
    )

    src = _source_setup_prefix(config.install_dir, config.ros_distro)
    build = colcon_build_cmd(config.colcon_args, cmake_args=config.cmake_args)

    debug(f"Source command: {src}")
    debug(f"Build command:  {build}")

    run_command(["bash", "-c", f"{src} && {build}"], env=clean_env)
    success("Local build completed successfully.")


def _test_locally(config: TestingConfig) -> None:
    """Run tests on the host using colcon with optional retry logic."""
    clean_env = make_clean_env()
    _ensure_colcon(clean_env)

    info(
        f"Running tests (distro={config.ros_distro}, "
        f"retries={config.retest_until_pass})"
    )

    src = _source_setup_prefix(config.install_dir, config.ros_distro)
    test = colcon_test_cmd(
        config.colcon_args,
        retest_until_pass=config.retest_until_pass,
    )

    run_command(
        ["bash", "-c", f"{src} && {test} && {COLCON_TEST_RESULT_CMD}"],
        env=clean_env,
    )
    success("Local tests completed successfully.")


def _prepare_locally(ros_distro: str, install_dir: str, project_name: str) -> None:
    """Prepare workspace: source ROS 2, download deps, install with rosdep.

    Supports both ROS2 workspace layout (src/) and flat project layout.
    """
    clean_env = make_clean_env()

    # Detect layout: ROS2 workspace (has src/) or project (flat)
    is_workspace = os.path.isdir("src")
    deps_dir = "src/external" if is_workspace else "external"
    rosdep_paths = "src" if is_workspace else "."

    info(
        f"Preparing {'workspace' if is_workspace else 'project'} "
        f"(distro={ros_distro}, install_dir={install_dir})"
    )

    src = _source_setup_prefix(install_dir, ros_distro)

    # Download dependencies from *.repos file
    repos_file = f"{project_name}.repos"
    if os.path.isfile(repos_file):
        info(f"Downloading dependencies from {repos_file}...")
        # Ensure deps_dir exists
        os.makedirs(deps_dir, exist_ok=True)
        run_command(
            [
                "bash", "-c",
                f"{src} && vcs import {deps_dir} < {repos_file}",
            ],
            env=clean_env,
        )
    else:
        debug(f"No {repos_file} found — skipping dependency download")

    # Run rosdep install
    info("Installing dependencies with rosdep...")
    run_command(
        [
            "bash", "-c",
            f"{src} && rosdep update --rosdistro {ros_distro} "
            f"&& rosdep install --from-paths {rosdep_paths} --ignore-src -r -y",
        ],
        env=clean_env,
    )

    success("Workspace preparation completed successfully.")


def _format_locally() -> None:
    """Run pre-commit hooks on all files."""
    info("Running pre-commit hooks...")
    run_command(["pre-commit", "run", "--all-files"])
    success("Code formatting completed successfully.")


# ── Click sub-group ───────────────────────────────────────────────────


@click.group("local")
def local_group() -> None:
    """Local development commands (build & test on the host)."""


@local_group.command("build")
@click.option(
    "--ros-distro", default=None,
    help="Target ROS 2 distribution.  [default: from config or jazzy]",
)
@click.option(
    "--install-dir", default=None,
    help="Base install directory.  [default: from config or /opt/ros]",
)
def local_build_cmd(ros_distro: str | None, install_dir: str | None) -> None:
    """Build ROS 2 workspace locally using colcon."""
    config = resolve_config(
        BuildConfig, "build",
        ros_distro=ros_distro,
        install_dir=install_dir,
    )
    _build_locally(config)


@local_group.command("test")
@click.option(
    "--ros-distro", default=None,
    help="Target ROS 2 distribution.  [default: from config or jazzy]",
)
@click.option(
    "--retest-until-pass", default=None, type=int,
    help="Number of retries for failing tests.  [default: from config or 0]",
)
def local_test_cmd(ros_distro: str | None, retest_until_pass: int | None) -> None:
    """Run tests locally using colcon."""
    config = resolve_config(
        TestingConfig, "test",
        ros_distro=ros_distro,
        retest_until_pass=retest_until_pass,
    )
    _test_locally(config)


@local_group.command("prepare")
@click.option(
    "--ros-distro", default=None,
    help="Target ROS 2 distribution.  [default: from config or jazzy]",
)
@click.option(
    "--install-dir", default=None,
    help="Base install directory.  [default: from config or /opt/ros]",
)
@click.option(
    "--project-name", default=None,
    help="Project name for *.repos file.  [default: from config or unnamed]",
)
def local_prepare_cmd(
    ros_distro: str | None,
    install_dir: str | None,
    project_name: str | None,
) -> None:
    """Prepare workspace: source ROS 2, download deps, install with rosdep."""
    from rdt.core.models import ProjectConfig

    proj = resolve_config(
        ProjectConfig, "project",
        ros_distro=ros_distro,
        install_dir=install_dir,
    )
    pname = project_name or proj.project_name or "unnamed"
    _prepare_locally(proj.ros_distro, proj.install_dir, pname)


@local_group.command("format")
def local_format_cmd() -> None:
    """Run pre-commit hooks on all files."""
    _format_locally()
