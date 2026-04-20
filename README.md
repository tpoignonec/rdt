# rdt — ROS2 Dev Tools

Lightweight CLI toolbox for ROS2 project build, test, and CI/CD workflows.
No Dagger, no containers required — runs anywhere (local, GitHub CI, GitLab CI).

See [spec.md](spec.md) for the full specification.

## Install

```bash
pip install rdt
```

## Quick start

```bash
rdt info          # show detected context and config
rdt deps          # install dependencies (vcs, apt, rosdep)
rdt build         # colcon build
rdt test          # colcon test
rdt build-docker  # build Docker image
rdt deploy-docker # push image to registry
rdt build-doc     # build Sphinx docs
rdt deploy-doc    # deploy to GitHub/GitLab Pages
rdt init          # scaffold project files
```
