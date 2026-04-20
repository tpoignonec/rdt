"""Tests for config loading and Pydantic models."""

from __future__ import annotations

import textwrap

import pytest

from rdt.config import RdtConfig, load_config


def test_defaults():
    config = RdtConfig()
    assert config.ros_distro == "jazzy"
    assert config.install_dir == "/opt/ros"
    assert config.build.install_base == "install"
    assert config.test.retest_until_pass == 0
    assert config.docker.builder == "docker"


def test_load_missing_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = load_config()
    assert config == RdtConfig()


def test_load_partial_yaml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".rdt.yaml").write_text(
        textwrap.dedent("""\
        ros_distro: humble
        build:
          cmake_args:
            - -DCMAKE_BUILD_TYPE=Debug
    """)
    )
    config = load_config()
    assert config.ros_distro == "humble"
    assert "-DCMAKE_BUILD_TYPE=Debug" in config.build.cmake_args
    assert config.test.retest_until_pass == 0  # default preserved


def test_load_full_yaml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".rdt.yaml").write_text(
        textwrap.dedent("""\
        ros_distro: rolling
        install_dir: /custom/ros
        build:
          cmake_build_type: Release
          install_base: /opt/ros/myproject
        test:
          retest_until_pass: 3
        docker:
          registry: ghcr.io/myorg
          builder: kaniko
        doc:
          sphinx_dir: docs/sphinx
    """)
    )
    config = load_config()
    assert config.ros_distro == "rolling"
    assert config.install_dir == "/custom/ros"
    assert config.build.cmake_build_type == "Release"
    assert config.build.install_base == "/opt/ros/myproject"
    assert config.test.retest_until_pass == 3
    assert config.docker.registry == "ghcr.io/myorg"
    assert config.docker.builder == "kaniko"
    assert config.doc.sphinx_dir == "docs/sphinx"


def test_invalid_builder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".rdt.yaml").write_text("docker:\n  builder: podman\n")
    with pytest.raises(Exception):
        load_config()


def test_config_discovery_walks_up(tmp_path, monkeypatch):
    """Config in parent dir is found when cwd is a subdirectory."""
    (tmp_path / ".rdt.yaml").write_text("ros_distro: iron\n")
    subdir = tmp_path / "src" / "my_pkg"
    subdir.mkdir(parents=True)
    monkeypatch.chdir(subdir)
    config = load_config()
    assert config.ros_distro == "iron"


def test_config_discovery_stops_at_git_root(tmp_path, monkeypatch):
    """Config above the .git root is not found."""
    (tmp_path / ".rdt.yaml").write_text("ros_distro: iron\n")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    monkeypatch.chdir(repo)
    config = load_config()
    assert config.ros_distro == "jazzy"  # default, not iron
