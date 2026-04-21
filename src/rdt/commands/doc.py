"""rdt build-doc and rdt deploy-doc — Sphinx documentation."""

from __future__ import annotations

import runpy
import shutil
import subprocess
from pathlib import Path
from typing import Any

import click

from rdt.config import load_config
from rdt.console import abort, info, success
from rdt.context import get_context
from rdt.runner import run, run_shell

# ── helpers ───────────────────────────────────────────────────────────────────


def _extract_html_context(conf_py: Path) -> dict[str, Any]:
    """Execute conf.py in an isolated namespace and return html_context."""
    ns = runpy.run_path(str(conf_py))
    result: dict[str, Any] = ns.get("html_context", {})
    return result


def _languages_for_branch(html_context: dict[str, Any], branch: str) -> list[str]:
    per_branch: dict[str, Any] = html_context.get("language_per_branch", {})
    if branch in per_branch:
        return list(per_branch[branch])
    return [html_context.get("default_language", "en")]


def _redirect_html(target: str) -> str:
    return (
        "<!DOCTYPE html><html><head>"
        f'<meta http-equiv="refresh" content="0; url={target}">'
        f'<link rel="canonical" href="{target}"/>'
        f'</head><body><p>Redirecting to <a href="{target}">{target}</a></p></body></html>\n'
    )


def _inject_token(url: str, token: str, user: str = "oauth2") -> str:
    parts = url.split("://", 1)
    return f"{parts[0]}://{user}:{token}@{parts[1]}" if len(parts) == 2 else url


# ── build-doc ─────────────────────────────────────────────────────────────────


@click.command()
@click.option("--sphinx-dir", default=None, metavar="DIR", help="Sphinx source root.")
@click.option("--output-dir", default=None, metavar="DIR", help="Build output directory.")
@click.option("--use-venv", is_flag=True, default=False, help="Use virtualenv for building docs.")
def build_doc_cmd(sphinx_dir: str | None, output_dir: str | None, use_venv: bool = False) -> None:
    """Build Sphinx documentation (multi-language support)."""
    config = load_config()
    ctx = get_context()

    src_dir = Path(sphinx_dir or config.doc.sphinx_dir)
    out_dir = Path(output_dir or config.doc.output_dir)
    source = src_dir / "source"
    conf_py = source / "conf.py"

    if not conf_py.exists():
        abort(f"conf.py not found: {conf_py}")

    html_context = _extract_html_context(conf_py)
    branch = ctx.branch
    langs = _languages_for_branch(html_context, branch)
    default_branch = html_context.get("default_branch", "main")
    default_lang = html_context.get("default_language", "en")

    source_venv_cmd = ''

    info(f"Install requirements for building docs...")
    # TODO: apt install system dependencies for sphinx build (latex & co.)

    if use_venv:
        info("Setting up virtualenv for building docs...")
        venv_dir = Path("/tmp/rdt-doc-venv")
        if venv_dir.exists():
            shutil.rmtree(venv_dir)
        run(["python3", "-m", "venv", str(venv_dir)])
        source_venv_cmd = f"source {venv_dir}/bin/activate && "

    info(f"Install sphinx requirements...")
    run([f"{source_venv_cmd}pip", "install", "-r", str(src_dir / "requirements.txt")])

    info(f"Building docs: branch={branch}, languages={langs}")

    if len(langs) > 1:
        info("Running gettext extraction...")
        run_shell(
            f"{source_venv_cmd} cd {src_dir} && "
            "sphinx-build -b gettext source build/gettext && "
            "sphinx-intl update -p build/gettext"
        )

    for lang in langs:
        lang_out = out_dir / branch / lang
        lang_out.mkdir(parents=True, exist_ok=True)
        info(f"  language={lang} -> {lang_out}")
        run([f"{source_venv_cmd}sphinx-build", "-b", "html", "-D", f"language={lang}", str(source), str(lang_out)])

    redirect = f"{default_branch}/{default_lang}/"
    (out_dir / "index.html").write_text(_redirect_html(redirect))
    success(f"Docs built: {out_dir}")


# ── deploy-doc ────────────────────────────────────────────────────────────────


@click.command()
@click.option("--built-doc-path", default=None, metavar="DIR")
@click.option("--publish-root", default="/tmp/rdt-doc-publish", metavar="DIR")
def deploy_doc_cmd(built_doc_path: str | None, publish_root: str | None) -> None:
    """Deploy documentation to GitHub Pages or GitLab Pages."""
    config = load_config()
    ctx = get_context()

    built = Path(built_doc_path or config.doc.output_dir)
    if not built.exists():
        abort(f"Built docs not found at {built}. Run 'rdt build-doc' first.")

    if ctx.is_local:
        dest = Path(publish_root or "/tmp/rdt-doc-publish")
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(str(built), str(dest))
        success(f"Docs copied to {dest} (local, no push).")
    elif ctx.is_github:
        _deploy_github(built, ctx)
    elif ctx.is_gitlab:
        _deploy_gitlab(built)


def _deploy_github(built: Path, ctx: object) -> None:
    from rdt.context import Context

    assert isinstance(ctx, Context)

    publish = Path("/tmp/rdt-gh-pages")
    if publish.exists():
        shutil.rmtree(publish)

    auth_url = _inject_token(ctx.repo_url, ctx.doc_token) if ctx.doc_token else ctx.repo_url

    probe = subprocess.run(
        ["git", "ls-remote", "--heads", auth_url, "gh-pages"],
        capture_output=True,
    )
    if probe.returncode == 0 and probe.stdout:
        run(["git", "clone", "--branch", "gh-pages", "--single-branch", auth_url, str(publish)])
    else:
        info("Creating new gh-pages branch...")
        publish.mkdir(parents=True)
        run(["git", "-C", str(publish), "init"])
        run(["git", "-C", str(publish), "checkout", "--orphan", "gh-pages"])

    for item in publish.iterdir():
        if item.name != ".git":
            shutil.rmtree(item) if item.is_dir() else item.unlink()
    shutil.copytree(str(built), str(publish), dirs_exist_ok=True)

    run(["git", "-C", str(publish), "config", "user.email", "action@github.com"])
    run(["git", "-C", str(publish), "config", "user.name", "GitHub Action"])
    run(["git", "-C", str(publish), "add", "-A"])
    run(["git", "-C", str(publish), "commit", "-m", f"docs: update from {ctx.branch}"])
    run(["git", "-C", str(publish), "push", auth_url, "gh-pages", "--force"])
    success("Docs deployed to gh-pages.")


def _deploy_gitlab(built: Path) -> None:
    public = Path("public")
    public.mkdir(exist_ok=True)
    shutil.copytree(str(built), str(public), dirs_exist_ok=True)
    success("Docs copied to public/ (GitLab Pages).")
