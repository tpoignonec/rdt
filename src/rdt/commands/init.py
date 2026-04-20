"""rdt init — scaffold project configuration and CI template files."""

from __future__ import annotations

from pathlib import Path

import click

from rdt.console import info, success, warn

_TEMPLATES = Path(__file__).parent.parent / "templates"


def _available_targets() -> list[str]:
    init_dir = _TEMPLATES / "init"
    return [d.name for d in sorted(init_dir.iterdir()) if d.is_dir()] if init_dir.exists() else []


def _target_files(target: str, project_name: str, ros_distro: str) -> dict[str, str]:
    """Return {dest_relative_path: content} for a given init target."""
    target_dir = _TEMPLATES / "init" / target
    files: dict[str, str] = {}
    for path in sorted(target_dir.rglob("*")):
        if path.is_file():
            dest = str(path.relative_to(target_dir)).replace("PROJECT_NAME", project_name)
            content = (
                path.read_text()
                .replace("PROJECT_NAME", project_name)
                .replace("ROS_DISTRO", ros_distro)
            )
            files[dest] = content
    return files


def _write(path: Path, content: str, force: bool) -> None:
    rel = path.relative_to(Path.cwd())
    if path.exists() and not force:
        warn(f"Skipping {rel} (already exists — use --force to overwrite).")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    info(f"  {rel}")


@click.command()
@click.option(
    "--project-name", default=None, help="Project name (default: current directory name)."
)
@click.option("--ros-distro", default="jazzy", show_default=True, help="ROS 2 distribution.")
@click.option(
    "--with",
    "include",
    multiple=True,
    metavar="TARGET",
    help="Include only these targets (repeatable).",
)
@click.option(
    "--without",
    "exclude",
    multiple=True,
    metavar="TARGET",
    help="Exclude these targets (repeatable).",
)
@click.option("--list", "list_targets", is_flag=True, help="List available targets and exit.")
@click.option("--force", is_flag=True, help="Overwrite existing files.")
def init_cmd(
    project_name: str | None,
    ros_distro: str,
    include: tuple[str, ...],
    exclude: tuple[str, ...],
    list_targets: bool,
    force: bool,
) -> None:
    """Scaffold project configuration and CI template files."""
    if list_targets:
        for t in _available_targets():
            click.echo(f"  {t}")
        return

    name = project_name or Path.cwd().name
    targets = _available_targets()
    if include:
        targets = [t for t in targets if t in include]
    if exclude:
        targets = [t for t in targets if t not in exclude]

    cwd = Path.cwd()
    info(f"Initializing project: {name}")

    _write(
        cwd / ".rdt.yaml",
        (_TEMPLATES / "config.yaml")
        .read_text()
        .replace("PROJECT_NAME", name)
        .replace("ROS_DISTRO", ros_distro),
        force,
    )
    _write(
        cwd / "Dockerfile",
        (_TEMPLATES / "Dockerfile")
        .read_text()
        .replace("PROJECT_NAME", name)
        .replace("ROS_DISTRO", ros_distro),
        force,
    )

    for target in targets:
        for rel, content in _target_files(target, name, ros_distro).items():
            _write(cwd / rel, content, force)

    success("Done. Edit .rdt.yaml and Dockerfile as needed.")
