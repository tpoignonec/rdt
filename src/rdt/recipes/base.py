"""Abstract base class for recipes.

A *recipe* encapsulates all the domain knowledge for a specific
project type (ROS 2, CMake, Python, …).  It knows:

  - Which Click commands to register.
  - What the default config template looks like.
  - Which Dockerfile / devcontainer templates to offer.
  - Which **init targets** (project-level file sets) to generate.

New project types are added by subclassing ``Recipe`` and registering
the subclass as an ``rdt.recipes`` entry-point in ``pyproject.toml``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import click


class Recipe(ABC):
    """Base class that every recipe must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short, unique recipe identifier (e.g. ``'ros2'``)."""

    @property
    @abstractmethod
    def description(self) -> str:
        """One-line human-readable description."""

    # ── CLI integration ───────────────────────────────────────────────

    @abstractmethod
    def register_commands(self, cli: click.Group) -> None:
        """Add recipe-specific commands / sub-groups to *cli*.

        Typically adds commands under ``local``, ``ci``, ``demo``, etc.
        """

    # ── Config / templates ────────────────────────────────────────────

    @abstractmethod
    def get_default_config(self) -> dict[str, Any]:
        """Return the default ``config.yaml`` content as a dict."""

    @abstractmethod
    def get_config_yaml_template(self) -> str:
        """Return the default ``config.yaml`` as a YAML string."""

    @abstractmethod
    def list_templates(self) -> list[str]:
        """Return names of available Dockerfile templates."""

    @abstractmethod
    def get_template(self, name: str | None = None) -> str:
        """Return the content of a Dockerfile template by *name*.

        ``None`` or ``'default'`` should return the base template.
        """

    @abstractmethod
    def get_templates_dir(self) -> Path:
        """Return the ``Path`` to the recipe's templates directory."""

    # ── Init targets (convention-based) ───────────────────────────────
    #
    # An *init target* is a named set of project-level files that
    # ``rdt init`` can generate.  Each target is a subdirectory under
    # ``<templates>/init/<target>/`` whose layout mirrors the workspace
    # root.  Example:
    #
    #   templates/init/vscode/.vscode/settings.json
    #   templates/init/github/.github/workflows/ci.yml
    #
    # Recipes that follow this convention get discovery for free.

    def list_init_targets(self) -> list[str]:
        """Return the names of available init targets.

        Default implementation auto-discovers subdirectories of
        ``<templates_dir>/init/``.
        """
        init_dir = self.get_templates_dir() / "init"
        if not init_dir.is_dir():
            return []
        return sorted(
            d.name for d in init_dir.iterdir()
            if d.is_dir() and not d.name.startswith(("_", "."))
        )

    def get_init_target_files(self, target: str) -> dict[str, str]:
        """Return ``{relative_path: content}`` for all files in *target*.

        The relative paths mirror the workspace root, so
        ``templates/init/vscode/.vscode/settings.json`` becomes
        ``.vscode/settings.json``.
        """
        target_dir = self.get_templates_dir() / "init" / target
        if not target_dir.is_dir():
            available = ", ".join(self.list_init_targets())
            raise ValueError(
                f"Unknown init target '{target}'. Available: {available}"
            )
        files: dict[str, str] = {}
        for path in sorted(target_dir.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                rel = str(path.relative_to(target_dir))
                files[rel] = path.read_text(encoding="utf-8")
        return files
