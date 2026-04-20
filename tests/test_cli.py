"""Tests for CLI structure and command registration."""

from __future__ import annotations

from click.testing import CliRunner

from rdt.cli import cli


def test_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "deps" in result.output
    assert "build" in result.output
    assert "test" in result.output
    assert "build-docker" in result.output
    assert "deploy-docker" in result.output
    assert "build-doc" in result.output
    assert "deploy-doc" in result.output
    assert "init" in result.output


def test_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_deps_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["deps", "--help"])
    assert result.exit_code == 0
    assert "--ros-distro" in result.output
    assert "--skip-vcs" in result.output
    assert "--skip-apt" in result.output
    assert "--skip-rosdep" in result.output


def test_build_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["build", "--help"])
    assert result.exit_code == 0
    assert "--install-base" in result.output
    assert "--cmake-build-type" in result.output


def test_test_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["test", "--help"])
    assert result.exit_code == 0
    assert "--retest-until-pass" in result.output


def test_build_docker_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["build-docker", "--help"])
    assert result.exit_code == 0
    assert "--builder" in result.output
    assert "--install-prefix" in result.output


def test_init_list(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["init", "--list"])
    assert result.exit_code == 0
    for target in ("vscode", "github", "gitlab", "devcontainer", "pre-commit", "repos"):
        assert target in result.output


def test_init_creates_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["init", "--project-name", "mybot", "--without", "devcontainer"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".rdt.yaml").exists()
    assert (tmp_path / "Dockerfile").exists()
    assert (tmp_path / ".vscode" / "settings.json").exists()
    assert (tmp_path / ".github" / "workflows" / "ci.yml").exists()
    assert (tmp_path / ".gitlab-ci.yml").exists()
    assert (tmp_path / "mybot.repos").exists()


def test_init_substitutes_project_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["init", "--project-name", "mybot", "--with", "repos", "--with", "github"])
    # Filename: PROJECT_NAME substituted in repos file name
    assert (tmp_path / "mybot.repos").exists()
    # Content: no leftover PROJECT_NAME tokens
    assert "PROJECT_NAME" not in (tmp_path / "mybot.repos").read_text()
    # Content: PROJECT_NAME substituted in github workflow
    ci_content = (tmp_path / ".github" / "workflows" / "ci.yml").read_text()
    assert "PROJECT_NAME" not in ci_content


def test_init_force_overwrites(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["init", "--project-name", "mybot", "--without", "devcontainer"])
    (tmp_path / ".rdt.yaml").write_text("ros_distro: humble\n")
    runner.invoke(cli, ["init", "--project-name", "mybot", "--force"])
    config_text = (tmp_path / ".rdt.yaml").read_text()
    assert "humble" not in config_text
