"""Shared shell-command builders for colcon build / test.

Both the local commands and the CI pipelines import these helpers
so that the colcon invocations are defined in exactly one place.
"""

from __future__ import annotations


def source_ros_setup(install_dir: str, ros_distro: str) -> str:
    """Shell snippet: source the ROS 2 setup file."""
    return f". {install_dir}/{ros_distro}/setup.bash"


def colcon_build_cmd(
    colcon_args: list[str] | None = None,
    *,
    install_base: str | None = None,
    cmake_args: list[str] | None = None,
    cmake_build_type: str | None = None,
) -> str:
    """Build the ``colcon build …`` shell command string.

    Parameters
    ----------
    cmake_args:
        List of ``-D…`` flags forwarded via ``--cmake-args``.
    cmake_build_type:
        If given, overrides any ``-DCMAKE_BUILD_TYPE=`` already in
        *cmake_args* (useful for deploy which always wants Release).
    """
    parts = ["colcon", "build"]
    if install_base:
        parts += ["--install-base", install_base]
    # Combine cmake args; cmake_build_type wins if both present
    effective_cmake = list(cmake_args or [])
    if cmake_build_type:
        effective_cmake = [
            a for a in effective_cmake
            if not a.startswith("-DCMAKE_BUILD_TYPE=")
        ]
        effective_cmake.append(f"-DCMAKE_BUILD_TYPE={cmake_build_type}")
    if effective_cmake:
        parts += ["--cmake-args"] + effective_cmake
    if colcon_args:
        parts.extend(colcon_args)
    return " ".join(parts)


def colcon_test_cmd(
    colcon_args: list[str] | None = None,
    *,
    retest_until_pass: int = 0,
) -> str:
    """Build the ``colcon test …`` shell command string."""
    parts = ["colcon", "test"]
    if retest_until_pass > 0:
        parts += ["--retest-until-pass", str(retest_until_pass)]
    if colcon_args:
        parts.extend(colcon_args)
    return " ".join(parts)


COLCON_TEST_RESULT_CMD = "colcon test-result --verbose"
