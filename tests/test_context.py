"""Tests for environment detection (Context)."""
from __future__ import annotations

import pytest

from rdt.context import Context, get_context


@pytest.fixture(autouse=True)
def _clear_context_cache():
    get_context.cache_clear()
    yield
    get_context.cache_clear()


def test_local_detection(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("GITLAB_CI", raising=False)
    ctx = get_context()
    assert ctx.is_local
    assert not ctx.is_github
    assert not ctx.is_gitlab
    assert ctx.platform == "local"


def test_github_detection(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    monkeypatch.setenv("GITHUB_SHA", "abc123")
    monkeypatch.setenv("GITHUB_REPOSITORY", "myorg/myrepo")
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.delenv("GITLAB_CI", raising=False)
    ctx = get_context()
    assert ctx.is_github
    assert not ctx.is_local
    assert ctx.branch == "main"
    assert ctx.commit_sha == "abc123"
    assert ctx.project_name == "myrepo"
    assert ctx.repo_url == "https://github.com/myorg/myrepo"
    assert ctx.platform == "github"


def test_gitlab_detection(monkeypatch):
    monkeypatch.setenv("GITLAB_CI", "true")
    monkeypatch.setenv("CI_COMMIT_REF_NAME", "feature/my-branch")
    monkeypatch.setenv("CI_COMMIT_SHA", "def456")
    monkeypatch.setenv("CI_PROJECT_NAME", "my_robot")
    monkeypatch.setenv("CI_PROJECT_URL", "https://gitlab.com/mygroup/my_robot")
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    ctx = get_context()
    assert ctx.is_gitlab
    assert not ctx.is_local
    assert ctx.branch == "feature/my-branch"
    assert ctx.project_name == "my_robot"
    assert ctx.platform == "gitlab"


def test_image_tag_main():
    ctx = Context(
        is_github=True, is_gitlab=False,
        branch="main", commit_sha="", project_name="mypkg",
        repo_url="", registry_user="", registry_token="", doc_token="",
    )
    assert ctx.resolve_image_tag() == "latest"


def test_image_tag_master():
    ctx = Context(
        is_github=True, is_gitlab=False,
        branch="master", commit_sha="", project_name="mypkg",
        repo_url="", registry_user="", registry_token="", doc_token="",
    )
    assert ctx.resolve_image_tag() == "latest"


def test_image_tag_feature_branch():
    ctx = Context(
        is_github=False, is_gitlab=True,
        branch="feature/my-feature", commit_sha="", project_name="mypkg",
        repo_url="", registry_user="", registry_token="", doc_token="",
    )
    assert ctx.resolve_image_tag() == "feature-my-feature"


def test_registry_credentials(monkeypatch):
    monkeypatch.setenv("GITLAB_CI", "true")
    monkeypatch.setenv("CI_COMMIT_REF_NAME", "main")
    monkeypatch.setenv("CI_COMMIT_SHA", "")
    monkeypatch.setenv("CI_PROJECT_NAME", "proj")
    monkeypatch.setenv("CI_PROJECT_URL", "")
    monkeypatch.setenv("REGISTRY_USER", "myuser")
    monkeypatch.setenv("REGISTRY_TOKEN", "mytoken")
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    ctx = get_context()
    assert ctx.registry_user == "myuser"
    assert ctx.registry_token == "mytoken"
