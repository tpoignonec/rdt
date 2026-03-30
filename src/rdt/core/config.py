"""Configuration loading, discovery, and resolution.

Responsibilities:
  - Walk up the filesystem to find ``.rdt/config.yaml``.
  - Load + validate it into a ``ProjectConfig``.
  - Provide ``resolve_config()`` — the single helper that merges
    project defaults, section overrides, and CLI flags into a
    typed Pydantic model.  Every Click command should call this
    instead of manually assembling dicts.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel

from rdt.core.console import debug, info
from rdt.core.models import ProjectConfig

# ── Constants ─────────────────────────────────────────────────────────

CONFIG_DIR = ".rdt"
CONFIG_FILE = "config.yaml"
DOCKERFILE = "Dockerfile"

T = TypeVar("T", bound=BaseModel)

# ── Project fields that propagate into per-command configs ────────────

_INHERITABLE_FIELDS = ("ros_distro", "base_image", "install_dir", "project_name")


# ── Filesystem discovery ──────────────────────────────────────────────


def find_config_dir(start: str | Path | None = None) -> Path | None:
    """Walk up from *start* (default: cwd) looking for ``.rdt/``.

    Returns the ``.rdt`` directory ``Path``, or ``None``.
    """
    current = Path(start or os.getcwd()).resolve()
    debug(f"Searching for {CONFIG_DIR}/ starting from {current}")
    for parent in [current, *current.parents]:
        candidate = parent / CONFIG_DIR
        if candidate.is_dir():
            debug(f"Found config dir: {candidate}")
            return candidate
    debug(f"No {CONFIG_DIR}/ directory found")
    return None


def load_project_config(start: str | Path | None = None) -> ProjectConfig | None:
    """Load and validate ``.rdt/config.yaml`` if it exists.

    Returns ``None`` when no config directory is found.
    """
    config_dir = find_config_dir(start)
    if config_dir is None:
        debug("No config directory found — using defaults")
        return None
    config_file = config_dir / CONFIG_FILE
    if not config_file.is_file():
        debug(f"{config_file} not found — returning empty ProjectConfig")
        return ProjectConfig()
    with open(config_file) as fh:
        raw = yaml.safe_load(fh) or {}
    debug(f"Loaded config from {config_file}")
    return ProjectConfig(**raw)


def get_dockerfile_path(start: str | Path | None = None) -> Path | None:
    """Return the path to ``.rdt/Dockerfile`` if it exists."""
    config_dir = find_config_dir(start)
    if config_dir is None:
        return None
    dockerfile = config_dir / DOCKERFILE
    if dockerfile.is_file():
        debug(f"Custom Dockerfile found: {dockerfile}")
        return dockerfile
    debug(f"No Dockerfile at {dockerfile}")
    return None


# ── Config resolution (the ONE place that merges everything) ──────────


def resolve_config(
    model: type[T],
    section: str,
    **cli_overrides: Any,
) -> T:
    """Build a typed config by layering recipe → project → CLI flags.

    Resolution order (later wins):

    1. **Recipe defaults** — baked into the recipe's ``defaults.yaml``.
    2. **Project globals** — top-level fields in ``.rdt/config.yaml``.
    3. **Project section** — section-specific overrides (e.g. ``build:``).
    4. **CLI flags** — explicit command-line arguments.

    Parameters
    ----------
    model:
        The Pydantic model class (e.g. ``BuildConfig``).
    section:
        The section name in ``config.yaml`` (e.g. ``"build"``).
    **cli_overrides:
        Values explicitly passed on the command line.  ``None`` values
        are ignored (i.e. the user didn't pass the flag).

    Returns
    -------
    T
        A fully validated instance of *model*.
    """
    proj = load_project_config()

    # ── 1. Recipe defaults ────────────────────────────────────────
    recipe_name = proj.recipe if proj else "ros2"
    from rdt.recipes import get_recipe  # lazy import to avoid circular deps

    recipe = get_recipe(recipe_name)
    recipe_defaults = recipe.get_default_config()

    defaults: dict[str, Any] = {}
    # Global fields from recipe defaults
    for field in _INHERITABLE_FIELDS:
        if field in recipe_defaults:
            defaults[field] = recipe_defaults[field]
    # Section fields from recipe defaults
    recipe_section = recipe_defaults.get(section, {})
    if isinstance(recipe_section, dict):
        defaults.update(recipe_section)

    debug(f"Recipe '{recipe_name}' defaults for [{section}]: {defaults}")

    # ── 2 & 3. Project config (globals + section) ─────────────────
    if proj:
        info("Loaded project config from .rdt/config.yaml")
        for field in _INHERITABLE_FIELDS:
            val = getattr(proj, field, None)
            if val is not None and val != "":
                defaults[field] = val
        section_data = getattr(proj, section, {})
        if isinstance(section_data, dict) and section_data:
            defaults.update(section_data)

    # ── 4. CLI flags win (drop None = "not supplied") ─────────────
    defaults.update({k: v for k, v in cli_overrides.items() if v is not None})

    return model(**defaults)
