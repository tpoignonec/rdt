"""rdt build-docker and rdt deploy-docker."""
from __future__ import annotations

import base64
import json
from pathlib import Path

import click

from rdt.config import load_config
from rdt.console import info, success
from rdt.context import get_context
from rdt.runner import run


def _full_image(registry: str, project: str, tag: str) -> str:
    base = f"{registry.rstrip('/')}/{project}" if registry else project
    return f"{base}:{tag}"


@click.command()
@click.option("--dockerfile", default=None, metavar="FILE")
@click.option("--tag", default=None, help="Image tag (overrides auto-detection).")
@click.option("--registry", default=None)
@click.option("--build-arg", multiple=True, metavar="KEY=VALUE", help="Extra build args (repeatable).")
@click.option("--builder", type=click.Choice(["docker", "kaniko"]), default=None)
@click.option("--ros-distro", default=None)
@click.option("--install-prefix", default=None, help="Install prefix inside image (default: /opt/ros/<project>).")
@click.option("--base-image", default=None, help="Override BASE_IMAGE build-arg.")
def build_docker_cmd(
    dockerfile: str | None,
    tag: str | None,
    registry: str | None,
    build_arg: tuple[str, ...],
    builder: str | None,
    ros_distro: str | None,
    install_prefix: str | None,
    base_image: str | None,
) -> None:
    """Build a Docker image using the project Dockerfile."""
    config = load_config()
    ctx = get_context()

    distro = ros_distro or config.ros_distro
    reg = registry or config.docker.registry
    dockerfile_ = dockerfile or config.docker.dockerfile
    builder_ = builder or config.docker.builder
    base = base_image or config.docker.base_image
    prefix = install_prefix or f"/opt/ros/{ctx.project_name}"
    image_tag = tag or ctx.resolve_image_tag()
    image = _full_image(reg, ctx.project_name, image_tag)

    bargs: dict[str, str] = {"ROS_DISTRO": distro, "INSTALL_PREFIX": prefix}
    if base:
        bargs["BASE_IMAGE"] = base
    for kv in build_arg:
        k, _, v = kv.partition("=")
        bargs[k] = v

    info(f"Building image: {image} (builder={builder_})")
    if builder_ == "kaniko":
        _kaniko_build(image, dockerfile_, bargs, ctx)
    else:
        _docker_build(image, dockerfile_, bargs)
    success(f"Image built: {image}")


def _docker_build(image: str, dockerfile: str, bargs: dict[str, str]) -> None:
    cmd = ["docker", "build", "-t", image, "-f", dockerfile]
    for k, v in bargs.items():
        cmd += ["--build-arg", f"{k}={v}"]
    cmd.append(".")
    run(cmd)


def _kaniko_build(image: str, dockerfile: str, bargs: dict[str, str], ctx: object) -> None:
    if hasattr(ctx, "registry_token") and ctx.registry_token:  # type: ignore[union-attr]
        registry = image.split("/")[0]
        auth = base64.b64encode(
            f"{ctx.registry_user}:{ctx.registry_token}".encode()  # type: ignore[union-attr]
        ).decode()
        config_path = Path("/kaniko/.docker/config.json")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps({"auths": {registry: {"auth": auth}}}))

    cmd = [
        "/kaniko/executor",
        "--context", "dir://.",
        "--dockerfile", dockerfile,
        "--destination", image,
    ]
    for k, v in bargs.items():
        cmd += ["--build-arg", f"{k}={v}"]
    run(cmd)


@click.command()
@click.option("--tag", default=None, help="Image tag (overrides auto-detection).")
@click.option("--registry", default=None)
@click.option("--also-tag", multiple=True, metavar="TAG", help="Additional tags to push (repeatable).")
def deploy_docker_cmd(
    tag: str | None,
    registry: str | None,
    also_tag: tuple[str, ...],
) -> None:
    """Push a Docker image to the registry."""
    config = load_config()
    ctx = get_context()

    reg = registry or config.docker.registry
    image_tag = tag or ctx.resolve_image_tag()
    image = _full_image(reg, ctx.project_name, image_tag)

    if ctx.registry_token:
        info("Logging in to registry...")
        login_registry = reg or image.split("/")[0]
        run(
            ["docker", "login", "-u", ctx.registry_user, "--password-stdin", login_registry],
            input=ctx.registry_token,
        )

    info(f"Pushing: {image}")
    run(["docker", "push", image])

    for extra in also_tag:
        extra_image = _full_image(reg, ctx.project_name, extra)
        run(["docker", "tag", image, extra_image])
        run(["docker", "push", extra_image])
        info(f"Also pushed: {extra_image}")

    success(f"Image pushed: {image}")
