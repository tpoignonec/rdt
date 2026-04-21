"""rdt build-docker and rdt deploy-docker."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import click

from rdt.config import load_config
from rdt.console import abort, info, success
from rdt.context import Context, get_context
from rdt.runner import run

_BUNDLED_DOCKERFILE = str(
    Path(__file__).parent.parent / 'templates' / 'Dockerfile'
)


def _full_image(registry: str, project: str, tag: str) -> str:
    base = f'{registry.rstrip("/")}/{project}' if registry else project
    return f'{base}:{tag}'


@click.command()
@click.option(
    '--dockerfile', default=None, metavar='FILE',
    help='Release Dockerfile (default: rdt bundled Dockerfile).',
)
@click.option('--tag', default=None, help='Image tag (overrides auto-detection).')
@click.option('--registry', default=None)
@click.option(
    '--build-arg', multiple=True, metavar='KEY=VALUE',
    help='Extra build args (repeatable).',
)
@click.option('--builder', type=click.Choice(['docker', 'kaniko']), default=None)
@click.option('--ros-distro', default=None)
@click.option(
    '--install-prefix', default=None,
    help='Install prefix inside image (default: /opt/ros/<project>).',
)
@click.option(
    '--base-image-name', default=None, metavar='IMAGE',
    help='Base image name/tag.',
)
@click.option(
    '--base-image-dockerfile', default=None, metavar='FILE',
    help='Dockerfile to build the base image (docker builder only).',
)
def build_docker_cmd(
    dockerfile: str | None,
    tag: str | None,
    registry: str | None,
    build_arg: tuple[str, ...],
    builder: str | None,
    ros_distro: str | None,
    install_prefix: str | None,
    base_image_name: str | None,
    base_image_dockerfile: str | None,
) -> None:
    """Build a Docker image using the rdt bundled Dockerfile.

    The base image can be provided as a name/tag (--base-image-name) or built
    on-the-fly from a Dockerfile (--base-image-dockerfile, docker builder only).
    If neither is given, the Dockerfile ARG default is used: ros:<distro>-ros-base.
    """
    config = load_config()
    ctx = get_context()

    distro = ros_distro or config.ros_distro
    reg = registry or config.docker.registry
    dockerfile_ = dockerfile or _BUNDLED_DOCKERFILE
    builder_ = builder or config.docker.builder
    base_name = base_image_name or config.base_image_name
    base_dockerfile = base_image_dockerfile or config.base_image_dockerfile
    prefix = install_prefix or f'/opt/ros/{ctx.project_name}'
    image_tag = tag or ctx.resolve_image_tag()
    image = _full_image(reg, ctx.project_name, image_tag)

    if base_name and base_dockerfile:
        abort('Specify either --base-image-name or --base-image-dockerfile, not both.')

    bargs: dict[str, str] = {'ROS_DISTRO': distro, 'INSTALL_PREFIX': prefix}

    if base_dockerfile:
        if builder_ == 'kaniko':
            abort('--base-image-dockerfile is not supported with the kaniko builder.')
        base_tag = f'rdt-base-{ctx.project_name}:local'
        info(f'Building base image from {base_dockerfile} -> {base_tag} ...')
        _docker_build(base_tag, base_dockerfile, {'ROS_DISTRO': distro})
        bargs['BASE_IMAGE'] = base_tag
    elif base_name:
        bargs['BASE_IMAGE'] = base_name

    for kv in build_arg:
        k, _, v = kv.partition('=')
        bargs[k] = v

    info(f'Building image: {image} (builder={builder_})')
    if builder_ == 'kaniko':
        _kaniko_build(image, dockerfile_, bargs, ctx)
    else:
        _docker_build(image, dockerfile_, bargs)
    success(f'Image built: {image}')


def _docker_build(image: str, dockerfile: str, bargs: dict[str, str]) -> None:
    cmd = ['docker', 'build', '-t', image, '-f', dockerfile]
    for k, v in bargs.items():
        cmd += ['--build-arg', f'{k}={v}']
    cmd.append('.')
    run(cmd)


def _kaniko_build(image: str, dockerfile: str, bargs: dict[str, str], ctx: Context) -> None:
    if ctx.registry_token:
        registry = image.split('/')[0]
        auth = base64.b64encode(
            f'{ctx.registry_user}:{ctx.registry_token}'.encode()
        ).decode()
        config_path = Path('/kaniko/.docker/config.json')
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps({'auths': {registry: {'auth': auth}}}))

    cmd = [
        '/kaniko/executor',
        '--context', 'dir://.',
        '--dockerfile', dockerfile,
        '--destination', image,
    ]
    for k, v in bargs.items():
        cmd += ['--build-arg', f'{k}={v}']
    run(cmd)


@click.command()
@click.option('--tag', default=None, help='Image tag (overrides auto-detection).')
@click.option('--registry', default=None)
@click.option(
    '--also-tag', multiple=True, metavar='TAG',
    help='Additional tags to push (repeatable).',
)
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
        info('Logging in to registry...')
        login_registry = reg or image.split('/')[0]
        run(
            ['docker', 'login', '-u', ctx.registry_user, '--password-stdin', login_registry],
            input=ctx.registry_token,
        )

    info(f'Pushing: {image}')
    run(['docker', 'push', image])

    for extra in also_tag:
        extra_image = _full_image(reg, ctx.project_name, extra)
        run(['docker', 'tag', image, extra_image])
        run(['docker', 'push', extra_image])
        info(f'Also pushed: {extra_image}')

    success(f'Image pushed: {image}')
