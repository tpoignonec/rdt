"""Tests for ROS2/colcon command builders."""

from __future__ import annotations

from rdt.commands._ros import (
    colcon_build_cmd,
    colcon_test_cmd,
    source_ros_distro,
    source_ros_ws,
)


def test_source_ros_ws() -> None:
    assert source_ros_ws("/opt/ros/my_ws") == ". /opt/ros/my_ws/setup.bash"


def test_source_ros_distro() -> None:
    assert source_ros_distro("jazzy") == ". /opt/ros/jazzy/setup.bash"


def test_colcon_build_minimal() -> None:
    cmd = colcon_build_cmd("install", [], None, [], [])
    assert cmd == "colcon build --install-base install"


def test_colcon_build_with_cmake_args() -> None:
    cmd = colcon_build_cmd("install", ["-DFOO=1", "-DBAR=2"], None, [], [])
    assert "--cmake-args -DFOO=1 -DBAR=2" in cmd


def test_colcon_build_cmake_build_type_override() -> None:
    cmd = colcon_build_cmd(
        "/opt/ros/myproject",
        ["-DCMAKE_BUILD_TYPE=Debug", "-DFOO=1"],
        "Release",
        [],
        [],
    )
    assert "-DCMAKE_BUILD_TYPE=Release" in cmd
    assert "-DCMAKE_BUILD_TYPE=Debug" not in cmd
    assert "-DFOO=1" in cmd


def test_colcon_build_packages_select() -> None:
    cmd = colcon_build_cmd("install", [], None, [], ["pkg_a", "pkg_b"])
    assert "--packages-select pkg_a pkg_b" in cmd


def test_colcon_build_custom_install_base() -> None:
    cmd = colcon_build_cmd("/opt/ros/myrobot", [], None, [], [])
    assert "--install-base /opt/ros/myrobot" in cmd


def test_colcon_test_minimal() -> None:
    cmd = colcon_test_cmd(0, [], [])
    assert cmd == "colcon test"


def test_colcon_test_with_retries() -> None:
    cmd = colcon_test_cmd(3, [], [])
    assert "--retest-until-pass 3" in cmd


def test_colcon_test_no_retry_flag_when_zero() -> None:
    cmd = colcon_test_cmd(0, [], [])
    assert "--retest-until-pass" not in cmd


def test_colcon_test_packages_select() -> None:
    cmd = colcon_test_cmd(0, [], ["my_pkg"])
    assert "--packages-select my_pkg" in cmd
