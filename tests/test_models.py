"""Tests for rdt.core.models — Pydantic model validation."""

import pytest
from pydantic import ValidationError

from rdt.core.models import ProjectConfig, RosBaseConfig
from rdt.recipes.ros2.models import BuildConfig, DemoConfig, DeployConfig, TestingConfig


class TestRosDistroValidator:
    """The RosDistro annotated type is used by all models."""

    def test_valid_distros(self):
        for distro in ("humble", "iron", "jazzy", "rolling"):
            cfg = RosBaseConfig(ros_distro=distro)
            assert cfg.ros_distro == distro

    def test_invalid_distro(self):
        with pytest.raises(ValidationError, match="Unsupported ROS distro"):
            RosBaseConfig(ros_distro="foxy")

    def test_distro_normalised(self):
        cfg = RosBaseConfig(ros_distro="  Jazzy  ")
        assert cfg.ros_distro == "jazzy"


class TestBuildConfig:
    def test_defaults(self):
        cfg = BuildConfig()
        assert cfg.ros_distro == "jazzy"
        assert cfg.install_dir == "/opt/ros"
        assert cfg.cmake_args == []
        assert cfg.colcon_args == []

    def test_cmake_args(self):
        cfg = BuildConfig(cmake_args=["-DCMAKE_BUILD_TYPE=Release"])
        assert cfg.cmake_args == ["-DCMAKE_BUILD_TYPE=Release"]

    def test_inherits_base_image(self):
        cfg = BuildConfig(base_image="my-image:latest")
        assert cfg.base_image == "my-image:latest"


class TestTestingConfig:
    def test_defaults(self):
        cfg = TestingConfig()
        assert cfg.retest_until_pass == 0

    def test_negative_retries_rejected(self):
        with pytest.raises(ValidationError):
            TestingConfig(retest_until_pass=-1)


class TestDeployConfig:
    def test_defaults(self):
        cfg = DeployConfig()
        assert cfg.image_tag == "latest"
        assert cfg.push is False

    def test_custom(self):
        cfg = DeployConfig(image_tag="1.2.3", push=True, registry="ghcr.io/user/repo")
        assert cfg.image_tag == "1.2.3"
        assert cfg.push is True


class TestDemoConfig:
    def test_image_required(self):
        with pytest.raises(ValidationError):
            DemoConfig()  # type: ignore[call-arg]

    def test_minimal(self):
        cfg = DemoConfig(image="ros:jazzy")
        assert cfg.image == "ros:jazzy"
        assert cfg.x11 is False
        assert cfg.network == "host"

    def test_invalid_network(self):
        with pytest.raises(ValidationError):
            DemoConfig(image="ros:jazzy", network="custom")  # type: ignore[arg-type]


class TestProjectConfig:
    def test_defaults(self):
        cfg = ProjectConfig()
        assert cfg.recipe == "ros2"
        assert cfg.ros_distro == "jazzy"

    def test_sections_are_dicts(self):
        cfg = ProjectConfig(build={"colcon_args": ["--symlink-install"]})
        assert cfg.build["colcon_args"] == ["--symlink-install"]
