"""Tests for rdt.core.config — config resolution logic."""

import yaml

from rdt.core.config import (
    CONFIG_DIR,
    CONFIG_FILE,
    find_config_dir,
    load_project_config,
    resolve_config,
)
from rdt.recipes.ros2.models import BuildConfig, TestingConfig, DeployConfig


class TestFindConfigDir:
    def test_finds_config_in_cwd(self, tmp_path):
        config_dir = tmp_path / CONFIG_DIR
        config_dir.mkdir()
        result = find_config_dir(tmp_path)
        assert result == config_dir

    def test_finds_config_in_parent(self, tmp_path):
        config_dir = tmp_path / CONFIG_DIR
        config_dir.mkdir()
        child = tmp_path / "src" / "pkg"
        child.mkdir(parents=True)
        result = find_config_dir(child)
        assert result == config_dir

    def test_returns_none_when_missing(self, tmp_path):
        result = find_config_dir(tmp_path)
        assert result is None


class TestLoadProjectConfig:
    def test_returns_none_without_dir(self, tmp_path):
        result = load_project_config(tmp_path)
        assert result is None

    def test_loads_yaml(self, tmp_path):
        config_dir = tmp_path / CONFIG_DIR
        config_dir.mkdir()
        config = {"project_name": "my_project", "ros_distro": "humble"}
        (config_dir / CONFIG_FILE).write_text(yaml.dump(config))
        result = load_project_config(tmp_path)
        assert result is not None
        assert result.project_name == "my_project"
        assert result.ros_distro == "humble"


class TestResolveConfig:
    """Test the 4-layer resolution: recipe → globals → section → CLI."""

    # ── Layer 1: recipe defaults (no project config) ──────────────

    def test_recipe_defaults_without_config(self, tmp_path, monkeypatch):
        """No .rdt/ at all → recipe defaults.yaml values are used."""
        monkeypatch.chdir(tmp_path)
        config = resolve_config(BuildConfig, "build")
        assert config.ros_distro == "jazzy"
        assert config.install_dir == "/opt/ros"

    def test_recipe_section_defaults(self, tmp_path, monkeypatch):
        """Section-level defaults come from the recipe when project omits them."""
        monkeypatch.chdir(tmp_path)
        config = resolve_config(TestingConfig, "test")
        assert config.retest_until_pass == 0
        assert config.colcon_args == []

    # ── Layer 2 & 3: project globals + section override recipe ────

    def test_project_globals_override_recipe(self, tmp_path, monkeypatch):
        """Project-level globals override recipe defaults."""
        config_dir = tmp_path / CONFIG_DIR
        config_dir.mkdir()
        (config_dir / CONFIG_FILE).write_text(
            yaml.dump({"ros_distro": "humble"})
        )
        monkeypatch.chdir(tmp_path)

        config = resolve_config(BuildConfig, "build")
        assert config.ros_distro == "humble"
        # install_dir not overridden → recipe default
        assert config.install_dir == "/opt/ros"

    def test_section_overrides_merge(self, tmp_path, monkeypatch):
        """Section-specific values override both recipe and global defaults."""
        config_dir = tmp_path / CONFIG_DIR
        config_dir.mkdir()
        proj_config = {
            "ros_distro": "humble",
            "build": {"colcon_args": ["--symlink-install"]},
        }
        (config_dir / CONFIG_FILE).write_text(yaml.dump(proj_config))
        monkeypatch.chdir(tmp_path)

        config = resolve_config(BuildConfig, "build")
        assert config.ros_distro == "humble"
        assert config.colcon_args == ["--symlink-install"]

    def test_partial_project_config_fills_from_recipe(self, tmp_path, monkeypatch):
        """Project config with only project_name → everything else from recipe."""
        config_dir = tmp_path / CONFIG_DIR
        config_dir.mkdir()
        (config_dir / CONFIG_FILE).write_text(
            yaml.dump({"project_name": "my_robot"})
        )
        monkeypatch.chdir(tmp_path)

        config = resolve_config(DeployConfig, "deploy")
        assert config.project_name == "my_robot"
        assert config.ros_distro == "jazzy"       # recipe default
        assert config.image_tag == "latest"        # recipe section default

    # ── Layer 4: CLI flags override everything ────────────────────

    def test_cli_overrides_win(self, tmp_path, monkeypatch):
        config_dir = tmp_path / CONFIG_DIR
        config_dir.mkdir()
        proj_config = {"ros_distro": "humble"}
        (config_dir / CONFIG_FILE).write_text(yaml.dump(proj_config))
        monkeypatch.chdir(tmp_path)

        config = resolve_config(BuildConfig, "build", ros_distro="rolling")
        assert config.ros_distro == "rolling"

    def test_cli_overrides_recipe_defaults(self, tmp_path, monkeypatch):
        """CLI flags override recipe defaults even with no project config."""
        monkeypatch.chdir(tmp_path)
        config = resolve_config(BuildConfig, "build", ros_distro="iron")
        assert config.ros_distro == "iron"

    def test_none_cli_values_ignored(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = resolve_config(BuildConfig, "build", ros_distro=None)
        assert config.ros_distro == "jazzy"  # recipe default, not None
