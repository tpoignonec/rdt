# rdt — ROS2 Dev Tools

Lightweight CLI toolbox for ROS2 project build, test, and CI/CD workflows.
No Dagger, no containers required — runs anywhere (local, GitHub CI, GitLab CI).

See [spec.md](spec.md) for the full specification.

## Install

### From Pypi

TODO

### From source

Create and activate a virtual environment:

```bash
sudo apt update
sudo apt install python3-venv

python3 -m venv .venv
source .venv/bin/activate
```

Install `rdt` inside the activated virtual environment:

```bash
pip install rdt
```

## Quick start

```bash
rdt info          # show detected context and config
rdt init          # scaffold project files
rdt deps          # install dependencies (vcs, apt, rosdep)
rdt build         # colcon build
rdt test          # colcon test
rdt docker-build  # build Docker image
rdt docker-deploy # push image to registry
rdt doc-build     # build Sphinx docs
rdt doc-deploy    # deploy to GitHub/GitLab Pages
```
