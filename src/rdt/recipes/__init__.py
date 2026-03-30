"""Recipe discovery and registration.

Recipes are discovered via ``importlib.metadata`` entry-points
(group ``rdt.recipes``).  Each entry-point should point to a
class that subclasses ``rdt.recipes.base.Recipe``.

Third-party packages can register their own recipes by adding::

    [tool.poetry.plugins."rdt.recipes"]
    my_recipe = "my_package:MyRecipe"

to their ``pyproject.toml``.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rdt.recipes.base import Recipe

if sys.version_info >= (3, 12):
    from importlib.metadata import entry_points
else:
    from importlib.metadata import entry_points


_ENTRY_POINT_GROUP = "rdt.recipes"


def discover_recipes() -> dict[str, Recipe]:
    """Return a ``{name: instance}`` mapping of all installed recipes."""
    recipes: dict[str, Recipe] = {}
    for ep in entry_points(group=_ENTRY_POINT_GROUP):
        cls = ep.load()
        instance = cls()
        recipes[instance.name] = instance
    return recipes


def get_recipe(name: str) -> Recipe:
    """Return a single recipe by *name*, or abort."""
    recipes = discover_recipes()
    if name not in recipes:
        from rdt.core.console import abort

        available = ", ".join(sorted(recipes.keys())) or "(none installed)"
        abort(f"Unknown recipe '{name}'. Available: {available}")
    return recipes[name]
