"""Shared apt helpers for command implementations."""

from __future__ import annotations

import os
import shutil

import click

from rdt.runner import run


def _resolve_sudo(use_sudo: bool | None) -> bool:
    """Return whether to prefix commands with sudo.

    ``None`` means auto-detect: no sudo when running as root, sudo when the
    binary is available, error otherwise.
    """
    if use_sudo is not None:
        return use_sudo
    if os.geteuid() == 0:
        return False
    if shutil.which("sudo"):
        return True
    raise click.ClickException("apt-get requires root privileges; run as root or install sudo.")


def _apt_cmd(use_sudo: bool | None) -> list[str]:
    return ["sudo", "apt-get"] if _resolve_sudo(use_sudo) else ["apt-get"]


def apt_update(*, use_sudo: bool | None = None) -> None:
    """Run apt-get update."""
    run([*_apt_cmd(use_sudo), "update"])


def apt_upgrade(*, use_sudo: bool | None = None) -> None:
    """Run apt-get upgrade -y."""
    run([*_apt_cmd(use_sudo), "upgrade", "-y"])


def apt_install(packages: list[str], *, use_sudo: bool | None = None, update: bool = False) -> None:
    """Install apt packages. Optionally run apt-get update first."""
    if not packages:
        return
    if update:
        apt_update(use_sudo=use_sudo)
    run([*_apt_cmd(use_sudo), "install", "-y", *packages])
