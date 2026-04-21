"""rdt info — show detected context and resolved configuration."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from rdt import __version__
from rdt.config import find_config_path, load_config
from rdt.context import get_context

_console = Console()


@click.command()
def info_cmd() -> None:
    """Show detected platform context and resolved configuration."""
    ctx = get_context()
    config = load_config()
    config_path = find_config_path()

    # ── Context table ─────────────────────────────────────────────────
    t = Table(title="Context", show_header=False, box=None, padding=(0, 2))
    t.add_column("key", style="cyan")
    t.add_column("value")

    t.add_row("rdt", __version__)
    t.add_row("platform", ctx.platform)
    t.add_row("project", ctx.project_name)
    t.add_row("branch", ctx.branch)
    t.add_row("commit", ctx.commit_sha[:12] if ctx.commit_sha else "(none)")
    t.add_row("repo_url", ctx.repo_url or "(none)")
    t.add_row("image_tag", ctx.resolve_image_tag())
    t.add_row("registry_user", ctx.registry_user or "(not set)")
    t.add_row(
        "REGISTRY_TOKEN", "[green]set[/green]" if ctx.registry_token else "[dim]not set[/dim]"
    )
    t.add_row("SECRET_TOKEN", "[green]set[/green]" if ctx.doc_token else "[dim]not set[/dim]")
    _console.print(t)
    _console.print()

    # ── Config table ──────────────────────────────────────────────────
    src = str(config_path) if config_path else "[dim]no .rdt.yaml found — using defaults[/dim]"
    t2 = Table(title=f"Config  ({src})", show_header=False, box=None, padding=(0, 2))
    t2.add_column("key", style="cyan")
    t2.add_column("value")

    t2.add_row("ros_distro", config.ros_distro)
    t2.add_row("install_dir", config.install_dir)
    t2.add_row("build.install_base", config.build.install_base)
    t2.add_row("build.cmake_args", " ".join(config.build.cmake_args) or "(none)")
    t2.add_row("build.cmake_build_type", config.build.cmake_build_type or "(none)")
    t2.add_row("test.retest_until_pass", str(config.test.retest_until_pass))
    t2.add_row("docker.registry", config.docker.registry or "(not set)")
    t2.add_row("docker.builder", config.docker.builder)
    base_image = config.base_image_name or f"ros:{config.ros_distro}-ros-base"
    t2.add_row("base_image_name", base_image)
    t2.add_row("doc.sphinx_dir", config.doc.sphinx_dir)
    t2.add_row("doc.output_dir", config.doc.output_dir)
    t2.add_row("doc.multi_version", str(config.doc.multi_version))
    t2.add_row("doc.apt_packages", " ".join(config.doc.apt_packages) or "(none)")
    _console.print(t2)

    # ── Resolved image name ───────────────────────────────────────────
    _console.print()
    registry = config.docker.registry
    tag = ctx.resolve_image_tag()
    base = f"{registry.rstrip('/')}/{ctx.project_name}" if registry else ctx.project_name
    _console.print(f"[cyan]resolved image[/cyan]  {base}:{tag}")
    prefix = f"/opt/ros/{ctx.project_name}"
    _console.print(f"[cyan]install prefix[/cyan]  {prefix}")
