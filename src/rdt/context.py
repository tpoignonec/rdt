from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Context:
    is_github: bool
    is_gitlab: bool
    branch: str
    commit_sha: str
    project_name: str
    repo_url: str
    registry_user: str
    registry_token: str
    doc_token: str

    @property
    def is_local(self) -> bool:
        return not self.is_github and not self.is_gitlab

    @property
    def platform(self) -> str:
        if self.is_github:
            return "github"
        if self.is_gitlab:
            return "gitlab"
        return "local"

    def resolve_image_tag(self) -> str:
        """Compute a Docker image tag from the current git state."""
        branch = self.branch
        tag = "latest" if branch in ("main", "master") else branch.replace("/", "-") or "dev"
        # Prefer an exact git tag on HEAD over the branch-derived tag
        try:
            out = subprocess.check_output(
                ["git", "describe", "--exact-match", "--tags", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            tag = out
        except subprocess.CalledProcessError:
            pass
        return tag


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return ""


@lru_cache(maxsize=1)
def get_context() -> Context:
    """Detect execution environment. Cached — safe to call repeatedly."""
    is_github = os.environ.get("GITHUB_ACTIONS") == "true"
    is_gitlab = os.environ.get("GITLAB_CI") == "true"

    if is_github:
        branch = os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME", "")
        commit_sha = os.environ.get("GITHUB_SHA", "")
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        project_name = repo.split("/")[-1] if repo else ""
        server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
        repo_url = f"{server}/{repo}" if repo else ""
    elif is_gitlab:
        branch = os.environ.get("CI_COMMIT_REF_NAME", "")
        commit_sha = os.environ.get("CI_COMMIT_SHA", "")
        project_name = os.environ.get("CI_PROJECT_NAME", "")
        repo_url = os.environ.get("CI_PROJECT_URL", "")
    else:
        branch = _git("branch", "--show-current")
        commit_sha = _git("rev-parse", "HEAD")
        remote = _git("config", "--get", "remote.origin.url")
        project_name = (
            remote.rstrip("/").split("/")[-1].removesuffix(".git")
            if remote
            else os.path.basename(os.getcwd())
        )
        repo_url = remote

    return Context(
        is_github=is_github,
        is_gitlab=is_gitlab,
        branch=branch or "unknown",
        commit_sha=commit_sha,
        project_name=project_name or os.path.basename(os.getcwd()),
        repo_url=repo_url,
        registry_user=os.environ.get("REGISTRY_USER", ""),
        registry_token=os.environ.get("REGISTRY_TOKEN", ""),
        doc_token=os.environ.get("SECRET_TOKEN", ""),
    )
