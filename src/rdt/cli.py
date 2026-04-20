from __future__ import annotations

import click

from rdt import __version__
from rdt.console import set_verbose


@click.group()
@click.version_option(__version__, prog_name="rdt")
@click.option("-v", "--verbose", is_flag=True, help="Enable debug output.")
def cli(verbose: bool) -> None:
    """ROS2 Dev Tools — build, test, and deploy ROS2 projects."""
    set_verbose(verbose)


def _register() -> None:
    from rdt.commands.build import build_cmd
    from rdt.commands.deps import deps_cmd
    from rdt.commands.doc import build_doc_cmd, deploy_doc_cmd
    from rdt.commands.docker import build_docker_cmd, deploy_docker_cmd
    from rdt.commands.info import info_cmd
    from rdt.commands.init import init_cmd
    from rdt.commands.test import test_cmd

    cli.add_command(info_cmd, "info")
    cli.add_command(deps_cmd, "deps")
    cli.add_command(build_cmd, "build")
    cli.add_command(test_cmd, "test")
    cli.add_command(build_docker_cmd, "build-docker")
    cli.add_command(deploy_docker_cmd, "deploy-docker")
    cli.add_command(build_doc_cmd, "build-doc")
    cli.add_command(deploy_doc_cmd, "deploy-doc")
    cli.add_command(init_cmd, "init")


_register()
