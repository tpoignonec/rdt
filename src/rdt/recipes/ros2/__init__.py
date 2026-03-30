"""ROS 2 recipe — build, test, deploy, and demo for ROS 2 workspaces."""

from __future__ import annotations

from importlib import resources as _resources
from pathlib import Path
from typing import Any

import click

from rdt.recipes.base import Recipe

_TEMPLATES_PKG = "rdt.recipes.ros2.templates"


class ROS2Recipe(Recipe):
    """Recipe for ROS 2 colcon-based workspaces."""

    @property
    def name(self) -> str:
        return "ros2"

    @property
    def description(self) -> str:
        return "Build, test, deploy, and demo ROS 2 colcon workspaces."

    # ── CLI integration ───────────────────────────────────────────

    def register_commands(self, cli: click.Group) -> None:
        """Register ``local``, ``ci``, and ``demo`` sub-groups."""
        from rdt.recipes.ros2.ci import ci_group
        from rdt.recipes.ros2.demo import demo_group
        from rdt.recipes.ros2.local import local_group

        cli.add_command(local_group)
        cli.add_command(ci_group)
        cli.add_command(demo_group)

    # ── Config / templates ────────────────────────────────────────

    def get_default_config(self) -> dict[str, Any]:
        import yaml

        content = (
            _resources.files(_TEMPLATES_PKG)
            .joinpath("defaults.yaml")
            .read_text(encoding="utf-8")
        )
        return yaml.safe_load(content) or {}

    def get_config_yaml_template(self) -> str:
        return (
            _resources.files(_TEMPLATES_PKG)
            .joinpath("config.yaml")
            .read_text(encoding="utf-8")
        )

    def list_templates(self) -> list[str]:
        templates_dir = _resources.files(_TEMPLATES_PKG)
        names: list[str] = []
        for item in templates_dir.iterdir():
            n = item.name
            if n == "Dockerfile":
                names.append("default")
            elif n.startswith("Dockerfile-"):
                names.append(n.removeprefix("Dockerfile-"))
        return sorted(names)

    def get_template(self, name: str | None = None) -> str:
        if name and name != "default":
            filename = f"Dockerfile-{name}"
        else:
            filename = "Dockerfile"
        ref = _resources.files(_TEMPLATES_PKG).joinpath(filename)
        try:
            return ref.read_text(encoding="utf-8")
        except FileNotFoundError:
            available = ", ".join(self.list_templates())
            raise ValueError(
                f"Unknown Dockerfile template '{name}'. Available: {available}"
            ) from None

    def get_templates_dir(self) -> Path:
        return Path(str(_resources.files(_TEMPLATES_PKG)))
