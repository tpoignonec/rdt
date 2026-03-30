"""CI/CD commands: build, test, deploy (Dagger-based).

Uses Click sub-groups: ``rdt ci build``, ``rdt ci test``, ``rdt ci deploy``.

The Dagger pipelines use layered stages::

    base  →  ros_base  →  deps  →  build  →  test
                          deps  →  build artifacts  →  deploy (runtime)
"""

from __future__ import annotations

import os
import subprocess

import click

from rdt.core.config import get_dockerfile_path, resolve_config
from rdt.core.console import abort, debug, info, success
from rdt.core.runner import run_dagger_pipeline
from rdt.recipes.ros2.commands import (
    COLCON_TEST_RESULT_CMD,
    colcon_build_cmd,
    colcon_test_cmd,
    source_ros_setup,
)
from rdt.recipes.ros2.models import BuildConfig, DeployConfig, TestingConfig


# ── Dagger helpers ────────────────────────────────────────────────────


def _resolve_base_image(ros_distro: str, base_image: str) -> str:
    """Return the effective base Docker image name."""
    resolved = base_image or f"ros:{ros_distro}-ros-base"
    debug(f"Resolved base image: {resolved}")
    return resolved


# ── Layered container stages ─────────────────────────────────────────

_COMMON_TOOLS = (
    "python3-colcon-common-extensions "
    "python3-rosdep "
    "git"
)


def _stage_base(client, ros_distro: str, base_image: str):  # type: ignore[no-untyped-def]
    """**base** — custom Dockerfile *or* vanilla ROS image."""
    import dagger

    dockerfile_path = get_dockerfile_path()
    if dockerfile_path:
        rel = os.path.relpath(str(dockerfile_path))
        info(f"Applying custom Dockerfile: {rel}")
        ctx = client.host().directory(".", exclude=[".git", "build", "install", "log"])
        return ctx.docker_build(
            dockerfile=rel,
            build_args=[dagger.BuildArg(name="ROS_DISTRO", value=ros_distro)],
        )
    img = _resolve_base_image(ros_distro, base_image)
    info(f"Base image: {img}")
    return client.container().from_(img)


def _stage_ros_base(base):  # type: ignore[no-untyped-def]
    """**ros_base** — base + common build tools."""
    return base.with_exec([
        "bash", "-c",
        "apt-get update "
        "&& apt-get install -y --no-install-recommends "
        f"{_COMMON_TOOLS} "
        "&& rm -rf /var/lib/apt/lists/*",
    ])


def _stage_deps(ros_base, src_dir, ros_distro: str):  # type: ignore[no-untyped-def]
    """**deps** — ros_base + rosdep-resolved runtime dependencies."""
    return (
        ros_base
        .with_directory("/ws/src", src_dir)
        .with_workdir("/ws")
        .with_exec([
            "bash", "-c",
            f"{source_ros_setup('/opt/ros', ros_distro)} "
            "&& (rosdep init 2>/dev/null || true) "
            f"&& rosdep update --rosdistro {ros_distro} "
            "&& rosdep install --from-paths src --ignore-src -r -y",
        ])
    )


def _stage_build(
    deps,  # type: ignore[no-untyped-def]
    ros_distro: str,
    colcon_args: list[str] | None = None,
    *,
    install_base: str | None = None,
    cmake_args: list[str] | None = None,
    cmake_build_type: str | None = None,
):
    """**build** — deps + colcon build."""
    cmd = colcon_build_cmd(
        colcon_args,
        install_base=install_base,
        cmake_args=cmake_args,
        cmake_build_type=cmake_build_type,
    )
    return deps.with_exec([
        "bash", "-c",
        f"{source_ros_setup('/opt/ros', ros_distro)} && {cmd}",
    ])


def _stage_test(
    build,  # type: ignore[no-untyped-def]
    ros_distro: str,
    colcon_args: list[str] | None = None,
    *,
    retest_until_pass: int = 0,
):
    """**test** — build + colcon test + test-result."""
    cmd = colcon_test_cmd(colcon_args, retest_until_pass=retest_until_pass)
    return build.with_exec([
        "bash", "-c",
        f"{source_ros_setup('/opt/ros', ros_distro)} "
        f"&& {cmd} && {COLCON_TEST_RESULT_CMD}",
    ])


# ── Public pipeline functions ─────────────────────────────────────────


def _ci_build(config: BuildConfig) -> None:
    """Build a ROS 2 workspace in CI (Dagger)."""
    distro = config.ros_distro
    info(f"CI build  (distro={distro}, base={_resolve_base_image(distro, config.base_image)})")

    async def _pipeline() -> None:
        import dagger

        async with dagger.Connection() as client:
            src = client.host().directory(".", exclude=[".git", "build", "install", "log"])
            base = _stage_base(client, distro, config.base_image)
            ros_base = _stage_ros_base(base)
            deps = _stage_deps(ros_base, src, distro)
            built = _stage_build(
                deps, distro, config.colcon_args,
                cmake_args=config.cmake_args,
            )
            await built.stdout()

    run_dagger_pipeline(_pipeline, label="CI build")
    success("CI build completed successfully.")


def _ci_test(config: TestingConfig) -> None:
    """Run tests in CI (Dagger): base → ros_base → deps → build → test."""
    distro = config.ros_distro
    info(f"CI test  (distro={distro}, retries={config.retest_until_pass})")

    async def _pipeline() -> None:
        import dagger

        async with dagger.Connection() as client:
            src = client.host().directory(".", exclude=[".git", "build", "install", "log"])
            base = _stage_base(client, distro, config.base_image)
            ros_base = _stage_ros_base(base)
            deps = _stage_deps(ros_base, src, distro)
            built = _stage_build(
                deps, distro, config.colcon_args,
                cmake_args=config.cmake_args,
            )
            tested = _stage_test(
                built, distro, config.colcon_args,
                retest_until_pass=config.retest_until_pass,
            )
            await tested.stdout()

    run_dagger_pipeline(_pipeline, label="CI test")
    success("CI tests completed successfully.")


def _deploy(config: DeployConfig) -> None:
    """Build & deploy: base → ros_base → deps → build → runtime image."""
    distro = config.ros_distro
    tag = config.image_tag
    registry = config.registry.rstrip("/")
    project = config.project_name or "unnamed"
    ws_install = f"/opt/ros/{project}"
    image_name = f"{registry}:{tag}" if registry else f"{project}:{tag}"

    info(f"Deploy  (image={image_name}, push={config.push}, install={ws_install})")

    async def _pipeline() -> None:
        import dagger

        async with dagger.Connection() as client:
            src = client.host().directory(".", exclude=[".git", "build", "install", "log"])

            base = _stage_base(client, distro, config.base_image)
            ros_base = _stage_ros_base(base)
            deps = _stage_deps(ros_base, src, distro)

            builder = _stage_build(
                deps, distro,
                install_base=ws_install,
                cmake_build_type="Release",
            )

            runtime = (
                deps
                .with_directory(ws_install, builder.directory(ws_install))
                .with_env_variable("RDT_INSTALL_DIR", ws_install)
                .with_workdir("/")
                .with_entrypoint([
                    "/bin/bash", "-c",
                    f". {ws_install}/setup.bash && exec \"$@\"",
                    "--",
                ])
                .with_default_args(args=["bash"])
            )

            if config.push:
                ref = await runtime.publish(image_name)
                success(f"Image pushed: {ref}")
            else:
                import tempfile

                tarball = os.path.join(tempfile.mkdtemp(prefix="rdt-"), "image.tar")
                await runtime.export(tarball)

                load_result = subprocess.run(
                    ["docker", "load", "-i", tarball],
                    capture_output=True, text=True,
                )
                if load_result.returncode != 0:
                    abort(f"docker load failed: {load_result.stderr.strip()}")

                loaded = load_result.stdout.strip()
                if "image ID:" in loaded:
                    sha = loaded.split("image ID:")[1].strip()
                    subprocess.run(["docker", "tag", sha, image_name], check=True)

                os.unlink(tarball)
                os.rmdir(os.path.dirname(tarball))
                success(f"Image loaded: {image_name}")

    run_dagger_pipeline(_pipeline, label="Deploy")
    success("Deploy completed successfully.")


# ── Click sub-group ───────────────────────────────────────────────────


@click.group("ci")
def ci_group() -> None:
    """CI/CD commands (Dagger-based containerised pipelines)."""


@ci_group.command("build")
@click.option("--ros-distro", default=None, help="Target ROS 2 distribution.")
@click.option("--base-image", default=None, help="Base Docker image for CI.")
def ci_build_cmd(ros_distro: str | None, base_image: str | None) -> None:
    """Build ROS 2 workspace in CI (Dagger)."""
    config = resolve_config(
        BuildConfig, "build",
        ros_distro=ros_distro, base_image=base_image,
    )
    _ci_build(config)


@ci_group.command("test")
@click.option("--ros-distro", default=None, help="Target ROS 2 distribution.")
@click.option("--retest-until-pass", default=None, type=int, help="Retries for failing tests.")
@click.option("--base-image", default=None, help="Base Docker image for CI.")
def ci_test_cmd(
    ros_distro: str | None, retest_until_pass: int | None, base_image: str | None,
) -> None:
    """Run tests in CI (Dagger)."""
    config = resolve_config(
        TestingConfig, "test",
        ros_distro=ros_distro, retest_until_pass=retest_until_pass, base_image=base_image,
    )
    _ci_test(config)


@ci_group.command("deploy")
@click.option("--image-tag", default=None, help="Docker image tag.")
@click.option("--push", is_flag=True, default=False, help="Push image to registry.")
@click.option("--registry", default=None, help="Container registry URL.")
@click.option("--base-image", default=None, help="Base Docker image.")
def ci_deploy_cmd(
    image_tag: str | None, push: bool, registry: str | None, base_image: str | None,
) -> None:
    """Build & deploy Docker image (Dagger multi-stage)."""
    config = resolve_config(
        DeployConfig, "deploy",
        image_tag=image_tag,
        push=push if push else None,  # only override if explicitly passed
        registry=registry,
        base_image=base_image,
    )
    _deploy(config)
