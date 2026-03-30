"""Tests for the rdt CLI entry point."""

from click.testing import CliRunner

from rdt.cli import cli

runner = CliRunner()


class TestCLIHelp:
    """Verify top-level help and version."""

    def test_help(self):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "local" in result.output
        assert "ci" in result.output
        assert "demo" in result.output
        assert "init" in result.output

    def test_version(self):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestLocalHelp:
    """Verify 'rdt local' sub-group."""

    def test_local_help(self):
        result = runner.invoke(cli, ["local", "--help"])
        assert result.exit_code == 0
        assert "build" in result.output
        assert "test" in result.output
        assert "prepare" in result.output
        assert "format" in result.output

    def test_local_build_help(self):
        result = runner.invoke(cli, ["local", "build", "--help"])
        assert result.exit_code == 0
        assert "--ros-distro" in result.output
        assert "--install-dir" in result.output

    def test_local_test_help(self):
        result = runner.invoke(cli, ["local", "test", "--help"])
        assert result.exit_code == 0
        assert "--retest-until-pass" in result.output

    def test_local_prepare_help(self):
        result = runner.invoke(cli, ["local", "prepare", "--help"])
        assert result.exit_code == 0
        assert "--ros-distro" in result.output
        assert "--project-name" in result.output

    def test_local_format_help(self):
        result = runner.invoke(cli, ["local", "format", "--help"])
        assert result.exit_code == 0
        assert "--reformat" in result.output


class TestCIHelp:
    """Verify 'rdt ci' sub-group."""

    def test_ci_help(self):
        result = runner.invoke(cli, ["ci", "--help"])
        assert result.exit_code == 0
        assert "build" in result.output
        assert "test" in result.output
        assert "deploy" in result.output

    def test_ci_build_help(self):
        result = runner.invoke(cli, ["ci", "build", "--help"])
        assert result.exit_code == 0
        assert "--ros-distro" in result.output
        assert "--base-image" in result.output

    def test_ci_deploy_help(self):
        result = runner.invoke(cli, ["ci", "deploy", "--help"])
        assert result.exit_code == 0
        assert "--image-tag" in result.output
        assert "--push" in result.output
        assert "--registry" in result.output


class TestDemoHelp:
    """Verify 'rdt demo' sub-group."""

    def test_demo_help(self):
        result = runner.invoke(cli, ["demo", "--help"])
        assert result.exit_code == 0
        assert "launch" in result.output

    def test_demo_launch_help(self):
        result = runner.invoke(cli, ["demo", "launch", "--help"])
        assert result.exit_code == 0
        assert "--image" in result.output
        assert "--x11" in result.output
        assert "--gpu" in result.output
        assert "--network" in result.output


class TestInitHelp:
    """Verify 'rdt init' command."""

    def test_init_help(self):
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "--recipe" in result.output
        assert "--template" in result.output
        assert "--list-templates" in result.output
        assert "--list-recipes" in result.output
        assert "--list-targets" in result.output
        assert "--with" in result.output
        assert "--without" in result.output

    def test_list_recipes(self):
        result = runner.invoke(cli, ["init", "--list-recipes"])
        assert result.exit_code == 0
        assert "ros2" in result.output

    def test_list_templates(self):
        result = runner.invoke(cli, ["init", "--list-templates"])
        assert result.exit_code == 0
        assert "default" in result.output
        assert "etherlab" in result.output

    def test_list_targets(self):
        result = runner.invoke(cli, ["init", "--list-targets"])
        assert result.exit_code == 0
        assert "vscode" in result.output
        assert "pre-commit" in result.output
        assert "github" in result.output
        assert "gitlab" in result.output


class TestInitTargets:
    """Verify 'rdt init' generates init target files."""

    def test_init_creates_targets(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, ["init", "--force"])
        assert result.exit_code == 0
        # Core files
        assert (tmp_path / ".rdt" / "config.yaml").is_file()
        assert (tmp_path / ".rdt" / "Dockerfile").is_file()
        # Init targets
        assert (tmp_path / ".vscode" / "settings.json").is_file()
        assert (tmp_path / ".vscode" / "extensions.json").is_file()
        assert (tmp_path / ".pre-commit-config.yaml").is_file()
        assert (tmp_path / ".github" / "workflows" / "ci.yml").is_file()
        assert (tmp_path / ".gitlab-ci.yml").is_file()

    def test_init_with_filter(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, ["init", "--with", "vscode"])
        assert result.exit_code == 0
        assert (tmp_path / ".vscode" / "settings.json").is_file()
        assert not (tmp_path / ".pre-commit-config.yaml").exists()
        assert not (tmp_path / ".github").exists()
        assert not (tmp_path / ".gitlab-ci.yml").exists()

    def test_init_without_filter(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, ["init", "--without", "gitlab,github"])
        assert result.exit_code == 0
        assert (tmp_path / ".vscode" / "settings.json").is_file()
        assert (tmp_path / ".pre-commit-config.yaml").is_file()
        assert not (tmp_path / ".github").exists()
        assert not (tmp_path / ".gitlab-ci.yml").exists()

    def test_init_unknown_target_aborts(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, ["init", "--with", "nonexistent"])
        assert result.exit_code != 0
        assert "Unknown" in result.output

    def test_init_skip_existing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # Create a file that init would generate
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "settings.json").write_text("{}")
        result = runner.invoke(cli, ["init", "--with", "vscode"])
        assert result.exit_code == 0
        assert "already exists" in result.output
        # Original content preserved
        assert (vscode_dir / "settings.json").read_text() == "{}"
