"""Shared ROS2/colcon helpers for command implementations."""
from __future__ import annotations

from pathlib import Path

from rdt.console import warn


def source_ros(install_dir: str, ros_distro: str) -> str:
    """Bash snippet that sources the ROS2 underlay setup file."""
    return f". {install_dir}/{ros_distro}/setup.bash"


def find_repos_file(hint: str | None = None) -> Path | None:
    """Locate a .repos file. Returns None if not found or ambiguous."""
    if hint:
        p = Path(hint)
        return p if p.exists() else None
    matches = sorted(Path.cwd().glob("*.repos"))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        warn("Multiple .repos files found — use --repos-file to specify one.")
    return None


def colcon_build_cmd(
    install_base: str,
    cmake_args: list[str],
    cmake_build_type: str | None,
    colcon_args: list[str],
    packages_select: list[str],
) -> str:
    """Assemble the colcon build command string."""
    effective_cmake = list(cmake_args)
    if cmake_build_type:
        effective_cmake = [a for a in effective_cmake if not a.startswith("-DCMAKE_BUILD_TYPE=")]
        effective_cmake.append(f"-DCMAKE_BUILD_TYPE={cmake_build_type}")

    parts = [f"colcon build --install-base {install_base}"]
    if effective_cmake:
        parts.append("--cmake-args " + " ".join(effective_cmake))
    parts.extend(colcon_args)
    if packages_select:
        parts.append("--packages-select " + " ".join(packages_select))
    return " ".join(parts)


def colcon_test_cmd(
    retest_until_pass: int,
    colcon_args: list[str],
    packages_select: list[str],
) -> str:
    """Assemble the colcon test command string."""
    parts = ["colcon test"]
    if retest_until_pass > 0:
        parts.append(f"--retest-until-pass {retest_until_pass}")
    parts.extend(colcon_args)
    if packages_select:
        parts.append("--packages-select " + " ".join(packages_select))
    return " ".join(parts)
