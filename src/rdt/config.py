from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class BuildConfig(BaseModel):
    cmake_args: list[str] = Field(default_factory=list)
    cmake_build_type: str | None = None
    colcon_args: list[str] = Field(default_factory=list)
    packages_select: list[str] = Field(default_factory=list)
    install_base: str = "install"


class TestConfig(BaseModel):
    retest_until_pass: int = 0
    colcon_args: list[str] = Field(default_factory=list)
    packages_select: list[str] = Field(default_factory=list)


class DockerConfig(BaseModel):
    registry: str = ""
    dockerfile: str = "Dockerfile"
    builder: Literal["docker", "kaniko"] = "docker"
    base_image: str = ""


class DocConfig(BaseModel):
    sphinx_dir: str = "doc/sphinx"
    output_dir: str = "doc/sphinx/build/html"


class RdtConfig(BaseModel):
    ros_distro: str = "jazzy"
    install_dir: str = "/opt/ros"
    build: BuildConfig = Field(default_factory=BuildConfig)
    test: TestConfig = Field(default_factory=TestConfig)
    docker: DockerConfig = Field(default_factory=DockerConfig)
    doc: DocConfig = Field(default_factory=DocConfig)


_CONFIG_NAME = ".rdt.yaml"


def find_config_path() -> Path | None:
    """Search upward from cwd for .rdt.yaml, stopping at repo root."""
    for directory in [Path.cwd(), *Path.cwd().parents]:
        candidate = directory / _CONFIG_NAME
        if candidate.exists():
            return candidate
        if (directory / ".git").exists():
            break
    return None


def load_config() -> RdtConfig:
    """Load .rdt.yaml if present; otherwise return all-defaults config."""
    path = find_config_path()
    if path is None:
        return RdtConfig()
    with path.open() as fh:
        data = yaml.safe_load(fh) or {}
    return RdtConfig.model_validate(data)
