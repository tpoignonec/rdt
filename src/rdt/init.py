"""``rdt init`` — initialise a project directory.

This is a built-in command (not recipe-specific) that:
  1. Creates ``.rdt/config.yaml`` from the active recipe's template.
  2. Creates ``.rdt/Dockerfile`` from the recipe's template library.
  3. Generates **init targets** — recipe-provided file sets such as
     ``.vscode/``, ``.pre-commit-config.yaml``, CI configs, etc.
"""

from __future__ import annotations

import os
from pathlib import Path

import click

from rdt.core.config import CONFIG_DIR, CONFIG_FILE, DOCKERFILE
from rdt.core.console import abort, debug, info, success, warning
from rdt.recipes import discover_recipes, get_recipe


@click.command("init")
@click.option(
    "--recipe", "-r", default="ros2",
    help="Recipe to use (e.g. ros2, cmake).",
)
@click.option(
    "--force", is_flag=True, default=False,
    help="Overwrite existing files.",
)
@click.option(
    "--template", "-t", default=None,
    help='Dockerfile template (e.g. "etherlab").  Use --list-templates to see options.',
)
@click.option(
    "--with", "include_targets", default=None,
    help="Comma-separated init targets to include (default: all).",
)
@click.option(
    "--without", "exclude_targets", default=None,
    help="Comma-separated init targets to exclude.",
)
@click.option(
    "--list-templates", is_flag=True, default=False,
    help="List available Dockerfile templates for the chosen recipe and exit.",
)
@click.option(
    "--list-recipes", is_flag=True, default=False,
    help="List all installed recipes and exit.",
)
@click.option(
    "--list-targets", is_flag=True, default=False,
    help="List available init targets for the chosen recipe and exit.",
)
def init_cmd(
    recipe: str,
    force: bool,
    template: str | None,
    include_targets: str | None,
    exclude_targets: str | None,
    list_templates: bool,
    list_recipes: bool,
    list_targets: bool,
) -> None:
    """Initialise a project with .rdt/ config and optional extras.

    By default, ``rdt init`` creates the ``.rdt/`` directory **and**
    all available init targets (e.g. .vscode, pre-commit, CI configs).

    Use ``--with`` to pick specific targets, or ``--without`` to skip some::

        rdt init                          # everything
        rdt init --with vscode,pre-commit # only these two
        rdt init --without gitlab         # everything except gitlab
    """
    # ── List recipes ──────────────────────────────────────
    if list_recipes:
        recipes = discover_recipes()
        info("Installed recipes:")
        for name, r in sorted(recipes.items()):
            click.echo(f"  - {name}: {r.description}")
        return

    r = get_recipe(recipe)

    # ── List templates ────────────────────────────────────
    if list_templates:
        names = r.list_templates()
        info(f"Available Dockerfile templates for recipe '{recipe}':")
        for name in names:
            click.echo(f"  - {name}")
        return

    # ── List init targets ─────────────────────────────────
    if list_targets:
        targets = r.list_init_targets()
        info(f"Available init targets for recipe '{recipe}':")
        for name in targets:
            click.echo(f"  - {name}")
        return

    # ── Core .rdt/ scaffold ───────────────────────────────
    ws_root = Path(os.getcwd())
    target = ws_root / CONFIG_DIR
    debug(f"Target directory: {target}")
    target.mkdir(exist_ok=True)

    config_path = target / CONFIG_FILE
    dockerfile_path = target / DOCKERFILE
    created: list[str] = []

    # config.yaml
    if config_path.exists() and not force:
        warning("config.yaml already exists — skipping (use --force to overwrite)")
    else:
        config_content = r.get_config_yaml_template()
        detected_name = ws_root.name
        # Patch only the project_name: line, preserving comments/formatting
        lines = config_content.splitlines()
        new_lines = []
        for line in lines:
            if line.strip().startswith('project_name:'):
                # Only replace if empty or whitespace after colon
                if line.strip() == 'project_name:' or line.strip() == 'project_name: ""' or line.strip() == 'project_name: \'\'':
                    new_lines.append(f'project_name: "{detected_name}"')
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        config_path.write_text('\n'.join(new_lines) + '\n')
        created.append(f"{CONFIG_DIR}/config.yaml")
        info(f"Created {CONFIG_DIR}/config.yaml")

    # Dockerfile
    if dockerfile_path.exists() and not force:
        warning("Dockerfile already exists — skipping (use --force to overwrite)")
    else:
        try:
            content = r.get_template(template)
        except ValueError as exc:
            abort(str(exc))
        dockerfile_path.write_text(content)
        label = f"Dockerfile (template: {template})" if template else "Dockerfile"
        created.append(f"{CONFIG_DIR}/Dockerfile")
        info(f"Created {CONFIG_DIR}/{label}")

    # ── Init targets ──────────────────────────────────────
    all_targets = r.list_init_targets()
    if include_targets:
        selected = [t.strip() for t in include_targets.split(",")]
        unknown = set(selected) - set(all_targets)
        if unknown:
            abort(
                f"Unknown init target(s): {', '.join(sorted(unknown))}. "
                f"Available: {', '.join(all_targets)}"
            )
    else:
        selected = list(all_targets)

    if exclude_targets:
        excluded = {t.strip() for t in exclude_targets.split(",")}
        selected = [t for t in selected if t not in excluded]

    # Try to get project_name from config.yaml if set, else fallback to directory name
    config_path = ws_root / CONFIG_DIR / CONFIG_FILE
    project_name = None
    if config_path.exists():
        import yaml
        with open(config_path, 'r') as f:
            try:
                config_data = yaml.safe_load(f)
                if isinstance(config_data, dict):
                    pn = config_data.get('project_name')
                    if pn and isinstance(pn, str) and pn.strip():
                        project_name = pn.strip()
            except Exception:
                pass
    if not project_name:
        project_name = ws_root.name

    for tgt in selected:
        files = r.get_init_target_files(tgt)
        for rel_path, content in files.items():
            # Replace PROJECT_NAME in filename with actual project name
            rel_path_actual = rel_path.replace('PROJECT_NAME', project_name)
            dest = ws_root / rel_path_actual
            if dest.exists() and not force:
                warning(f"{rel_path_actual} already exists — skipping")
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content)
            created.append(rel_path_actual)
            info(f"Created {rel_path_actual}")

    if created:
        success(f"Project initialised (recipe: {recipe})")
    else:
        info("Nothing to do — all files already exist.")
