"""Shared Pydantic types and base models.

Defines re-usable ``Annotated`` types (e.g. ``RosDistro``) and base
model classes so that per-command configs don't duplicate validators.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, Field

# ── Supported ROS 2 distributions ────────────────────────────────────

SUPPORTED_ROS_DISTROS: tuple[str, ...] = ('humble', 'iron', 'jazzy', 'rolling')


def _validate_ros_distro(value: str) -> str:
    value = value.strip().lower()
    if value not in SUPPORTED_ROS_DISTROS:
        raise ValueError(
            f'Unsupported ROS distro "{value}". '
            f'Choose from: {", ".join(SUPPORTED_ROS_DISTROS)}'
        )
    return value


RosDistro = Annotated[str, AfterValidator(_validate_ros_distro)]
"""A validated ROS 2 distribution name (e.g. ``'jazzy'``)."""


# ── Shared base models ───────────────────────────────────────────────


class RosBaseConfig(BaseModel):
    """Fields shared by every ROS 2 build/test/deploy config."""

    ros_distro: RosDistro = Field(
        default='jazzy',
        description='Target ROS 2 distribution.',
    )
    base_image: str = Field(
        default='',
        description='Base Docker image for building and deployment.',
    )


class ProjectConfig(BaseModel):
    """Top-level model mirroring ``.rdt/config.yaml``.

    Holds global defaults and per-section overrides.  Sections are
    stored as raw dicts so that the per-command Pydantic models can
    validate them independently.
    """

    project_name: str = Field(default='', description='Project / meta-package name.')
    recipe: str = Field(default='ros2', description='Active recipe name.')
    ros_distro: RosDistro = Field(default='jazzy', description='Target ROS 2 distribution.')
    base_image: str = Field(default='', description='Base Docker image for building and deployment.')
    install_dir: str = Field(default='/opt/ros/icube', description='ROS installation directory.')

    # Per-section overrides (validated lazily by each command).
    build: dict[str, Any] = Field(default_factory=dict)
    test: dict[str, Any] = Field(default_factory=dict)
    deploy: dict[str, Any] = Field(default_factory=dict)
    demo: dict[str, Any] = Field(default_factory=dict)
