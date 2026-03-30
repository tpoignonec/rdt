"""ROS 2-specific Pydantic models.

These inherit from ``RosBaseConfig`` (shared ``ros_distro`` +
``base_image`` with a single ``RosDistro`` annotated validator)
so the validator is never duplicated.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from rdt.core.models import RosBaseConfig


class BuildConfig(RosBaseConfig):
    """Configuration for local and CI build commands."""

    install_dir: str = Field(default="/opt/ros", description="Base install directory.")
    cmake_args: list[str] = Field(
        default_factory=list,
        description="CMake arguments passed via ``--cmake-args``.",
    )
    colcon_args: list[str] = Field(
        default_factory=list,
        description="Extra arguments forwarded to ``colcon build``.",
    )


class TestingConfig(RosBaseConfig):
    """Configuration for local and CI test commands."""

    install_dir: str = Field(default="/opt/ros", description="Base install directory.")
    retest_until_pass: int = Field(
        default=0,
        ge=0,
        description="Number of retries for failing tests (0 = no retry).",
    )
    colcon_args: list[str] = Field(
        default_factory=list,
        description="Extra arguments forwarded to ``colcon test``.",
    )


class DeployConfig(RosBaseConfig):
    """Configuration for the deploy (Docker build + push) command."""

    project_name: str = Field(default="", description="Project name for image naming.")
    image_tag: str = Field(default="latest", description="Docker image tag.")
    push: bool = Field(default=False, description="Push the built image to the registry.")
    registry: str = Field(default="", description="Container registry URL.")


class DemoConfig(RosBaseConfig):
    """Configuration for the Rocker demo launcher."""

    image: str = Field(..., description="Docker image to launch with Rocker.")
    x11: bool = Field(default=False, description="Enable X11 forwarding.")
    gpu: bool = Field(default=False, description="Enable GPU passthrough (nvidia).")
    extra_args: list[str] = Field(
        default_factory=list,
        description="Extra arguments forwarded to Rocker.",
    )
    network: Literal["host", "bridge", "none"] = Field(
        default="host",
        description="Docker network mode.",
    )
