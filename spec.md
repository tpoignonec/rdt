# rdt — ROS2 Dev Tools: Specification

*Lightweight, Dagger-free CLI toolbox for ROS2 project CI/CD workflows.*

---

## 1. Goals

- **Simple to use:** flat command surface, sensible defaults, minimal config.
- **Works everywhere:** local machine, GitHub CI, GitLab CI (including rootless, no DinD).
- **No magic containers:** commands run directly in whatever environment they are called from — the CI job's Docker image, the developer's machine, or a Dockerfile.
- **Low maintenance:** one small Python package, no plugin system, ROS2-only.

---

## 2. Architecture

```
rdt/
├── pyproject.toml
├── spec.md
└── src/
    └── rdt/
        ├── __init__.py
        ├── cli.py              # Click entry point, command registration
        ├── context.py          # Environment detection + git info
        ├── config.py           # .rdt.yaml loading + Pydantic models
        ├── runner.py           # subprocess wrapper (logging, error handling)
        └── commands/
            ├── deps.py         # rdt deps
            ├── build.py        # rdt build
            ├── test.py         # rdt test
            ├── docker.py       # rdt build-docker, rdt deploy-docker
            ├── doc.py          # rdt build-doc, rdt deploy-doc
            └── init.py         # rdt init
```

**Dependencies:** `click`, `pydantic`, `rich` (console output).
**No Dagger, no Rocker dependency.**

---

## 3. CLI Commands

Entry point: `rdt`

### 3.1 `rdt deps`

Install all workspace dependencies.

```
rdt deps [OPTIONS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--ros-distro` | from config / `jazzy` | ROS 2 distribution |
| `--repos-file` | auto-detected `*.repos` | vcstool repos file |
| `--skip-vcs` | false | Skip `vcs import` step |
| `--skip-apt` | false | Skip `apt` update/upgrade |
| `--skip-rosdep` | false | Skip rosdep install |

**Steps (in order):**
1. `vcs import --recursive < <repos-file>` (if repos file found/provided)
2. `apt-get update && apt-get upgrade -y` (skipped in local mode by default unless `--apt`)
3. `rosdep update`
4. `rosdep install --from-paths . --ignore-src -y --rosdistro <distro>`

---

### 3.2 `rdt build`

Build the ROS 2 workspace with colcon.

```
rdt build [OPTIONS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--ros-distro` | from config / `jazzy` | ROS 2 distribution |
| `--install-dir` | `/opt/ros` | ROS install prefix to source |
| `--install-base` | `install/` | colcon `--install-base` (output dir for artifacts) |
| `--cmake-args` | from config | Extra CMake arguments (repeatable) |
| `--cmake-build-type` | — | Shorthand for `-DCMAKE_BUILD_TYPE=<value>` |
| `--colcon-args` | from config | Extra colcon arguments (repeatable) |
| `--packages-select` | — | Build only these packages |

**Steps:**
1. Source `/opt/ros/<distro>/setup.bash`
2. `colcon build --install-base <install-base> [--cmake-args ...] [--packages-select ...]`

> When building a Docker image, `--install-base` is set to the `INSTALL_PREFIX` build-arg (e.g. `/opt/ros/<project>`). See §6.

---

### 3.3 `rdt test`

Run tests on the ROS 2 workspace with colcon.

```
rdt test [OPTIONS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--ros-distro` | from config / `jazzy` | ROS 2 distribution |
| `--install-dir` | `/opt/ros` | ROS install prefix to source |
| `--retest-until-pass` | `0` | Retry failed tests N times |
| `--packages-select` | — | Test only these packages |

**Steps:**
1. Source `/opt/ros/<distro>/setup.bash` + `install/setup.bash`
2. `colcon test [--packages-select ...]`
3. `colcon test-result --verbose` (exits non-zero on failure)
4. Retry up to `--retest-until-pass` times if failures detected

---

### 3.4 `rdt build-docker`

Build a Docker image for the project using a **multi-stage Dockerfile** (see §6).

```
rdt build-docker [OPTIONS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--dockerfile` | `Dockerfile` | Path to Dockerfile |
| `--tag` | auto (see §5) | Image name:tag |
| `--registry` | from config | Container registry URL |
| `--build-arg` | — | Extra `--build-arg` (repeatable) |
| `--builder` | `docker` | Builder backend: `docker` or `kaniko` |
| `--ros-distro` | from config / `jazzy` | Passed as `ROS_DISTRO` build-arg |
| `--install-prefix` | `/opt/ros/<project-name>` | Passed as `INSTALL_PREFIX` build-arg |

**What `rdt build-docker` does:**
1. Resolves the image name and tag (see §5).
2. Injects `ROS_DISTRO` and `INSTALL_PREFIX` as `--build-arg` values.
3. Calls `docker build` (or Kaniko executor — see §7) and tags the result.

The **build logic lives entirely in the project's Dockerfile** — `rdt build-docker` is just a thin wrapper that supplies context-derived values as build arguments and handles tagging. The Dockerfile template (provided by `rdt init`) is described in §6.

**Builder selection:**
- `docker`: uses `docker build` — works locally and on GitHub Actions.
- `kaniko`: uses `executor` binary — works in rootless GitLab CI (no DinD). See §7.

---

### 3.5 `rdt deploy-docker`

Push a previously built Docker image to a registry.

```
rdt deploy-docker [OPTIONS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--tag` | auto (see §5) | Image name:tag to push |
| `--registry` | from config | Container registry URL |
| `--also-tag` | — | Additional tags to push (repeatable) |

**Authentication:** reads `REGISTRY_USER` and `REGISTRY_TOKEN` from environment. Runs `docker login` automatically if both are set.

---

### 3.6 `rdt build-doc`

Build Sphinx documentation (with multi-language support).

```
rdt build-doc [OPTIONS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--sphinx-dir` | `doc/sphinx` | Path to sphinx source root |
| `--output-dir` | `doc/sphinx/build/html` | Build output directory |

**Steps:**
1. Parse `html_context` from `<sphinx-dir>/source/conf.py` (using `sphinx_conf_extractor`).
2. Determine languages for current branch from `language_per_branch` mapping.
3. If multilingual: run `make gettext` then `sphinx-intl update`.
4. For each language: `sphinx-build -b html -D language=<lang> source/ <output>/<branch>/<lang>/`
5. Generate root `index.html` redirect to `<default-branch>/<default-lang>/`.

---

### 3.7 `rdt deploy-doc`

Deploy built documentation to GitHub Pages or GitLab Pages.

```
rdt deploy-doc [OPTIONS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--built-doc-path` | `doc/sphinx/build/html` | Directory of built docs |
| `--publish-root` | `/tmp/rdt-doc-publish` | Staging directory |

**Behavior per platform (auto-detected):**
- **GitHub:** clones `gh-pages` branch (orphan if new), copies docs, force-pushes. Auth via `SECRET_TOKEN` env var.
- **GitLab:** copies built docs to `public/` directory (GitLab Pages standard). Auth via `SECRET_TOKEN`.
- **Local:** copies to `test/ci_cd/local_build_docs/` (no git push, for inspection).

---

### 3.8 `rdt init`

Scaffold project files into the current directory.

```
rdt init [OPTIONS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--project-name` | current directory name | Project name |
| `--ros-distro` | `jazzy` | ROS 2 distribution |
| `--with` | all | Targets to include (repeatable) |
| `--without` | none | Targets to exclude (repeatable) |
| `--list` | — | List available targets and exit |

**Available targets:** `vscode`, `github`, `gitlab`, `devcontainer`, `pre-commit`, `repos`

---

## 4. Configuration

### 4.1 File: `.rdt.yaml`

Placed at the project root. All fields are optional — defaults and auto-detection cover most cases.

```yaml
# .rdt.yaml

ros_distro: jazzy          # ROS 2 distribution
install_dir: /opt/ros      # ROS install prefix

build:
  cmake_args:
    - -DCMAKE_BUILD_TYPE=RelWithDebInfo
    - -DCMAKE_EXPORT_COMPILE_COMMANDS=1
  colcon_args: []
  packages_select: []

test:
  retest_until_pass: 0
  colcon_args: []
  packages_select: []

docker:
  registry: ghcr.io/myorg   # e.g. ghcr.io/org, registry.gitlab.com/group/project
  dockerfile: Dockerfile
  builder: docker            # docker | kaniko

doc:
  sphinx_dir: doc/sphinx
  output_dir: doc/sphinx/build/html
```

### 4.2 Priority (highest to lowest)

1. CLI flags
2. `.rdt.yaml` project section (e.g. `build:`, `test:`)
3. `.rdt.yaml` top-level fields (`ros_distro`, `install_dir`)
4. Built-in defaults

---

## 5. Context Detection

Module: `rdt.context`

Detected automatically at startup. Exposes a `Context` object:

| Property | Source |
|----------|--------|
| `is_local` | not GitHub, not GitLab |
| `is_github` | `GITHUB_ACTIONS == "true"` |
| `is_gitlab` | `GITLAB_CI == "true"` |
| `branch` | `GITHUB_REF_NAME` / `CI_COMMIT_REF_NAME` / `git branch --show-current` |
| `commit_sha` | `GITHUB_SHA` / `CI_COMMIT_SHA` / `git rev-parse HEAD` |
| `project_name` | `GITHUB_REPOSITORY` / `CI_PROJECT_NAME` / directory name |
| `repo_url` | `GITHUB_SERVER_URL/GITHUB_REPOSITORY` / `CI_PROJECT_URL` / git remote |
| `registry_user` | `REGISTRY_USER` env var |
| `registry_token` | `REGISTRY_TOKEN` env var |
| `doc_token` | `SECRET_TOKEN` env var |

### 5.1 Automatic Docker Image Tagging

| Condition | Tag |
|-----------|-----|
| Branch is `main` or `master` | `latest` |
| Git tag present (`v*`) | tag name (e.g. `v1.2.3`) |
| Any other branch | branch name (slashes → dashes) |
| Fallback | `git-<short-sha>` |

Full image name: `<registry>/<project-name>:<tag>`

---

## 6. Multi-Stage Dockerfile Strategy

`rdt build-docker` delegates all build logic to the project's **Dockerfile** — it only drives tagging and passes context values as build arguments. The Dockerfile follows a two-stage pattern that produces a lean runtime image containing **only the compiled install artifacts**, not sources or build tools.

### 6.1 Stage overview

```
 ┌─────────────────────────────────────────────────┐
 │  builder stage  (ros:<distro>-ros-base)          │
 │  - apt tools + rdt installed                     │
 │  - rdt deps   → apt upgrade + rosdep (all deps)  │
 │  - rdt build  → colcon build --install-base      │
 │                  /opt/ros/<project>  (Release)   │
 └────────────────────────┬────────────────────────┘
                          │ COPY --from=builder
                          │   /opt/ros/<project>
                          ▼
 ┌─────────────────────────────────────────────────┐
 │  runtime stage  (ros:<distro>-ros-base)          │
 │  - rdt deps (--skip-vcs)  → runtime rosdep deps  │
 │  - install artifacts at /opt/ros/<project>       │
 │  - entrypoint sources setup.bash                 │
 └─────────────────────────────────────────────────┘
```

**Key design decisions (mirroring the old rdt Dagger pipeline):**
- Colcon is called with a **custom `--install-base`** (`/opt/ros/<project>`) so all artifacts land in one clean, relocatable directory — not in the default `install/`.
- The build type is forced to **Release** in the Docker image build (overriding any debug flags from `.rdt.yaml`).
- The runtime stage copies **only that directory** from the builder — no sources, no build cache, no colcon metadata.
- Both stages start from the same base image so shared system libraries are compatible.

### 6.2 Template Dockerfile (provided by `rdt init`)

```dockerfile
ARG ROS_DISTRO=jazzy
ARG BASE_IMAGE=ros:${ROS_DISTRO}-ros-base

# ── Builder ──────────────────────────────────────────────────────────────
FROM ${BASE_IMAGE} AS builder

ARG ROS_DISTRO=jazzy
ARG INSTALL_PREFIX=/opt/ros/myproject

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3-pip \
    && pip install rdt \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ws
COPY . src/

# Install all workspace dependencies (apt + rosdep)
RUN rdt deps --ros-distro ${ROS_DISTRO}

# Build in Release mode into the relocatable install prefix
RUN rdt build \
        --ros-distro ${ROS_DISTRO} \
        --install-base ${INSTALL_PREFIX} \
        --cmake-build-type Release

# ── Runtime ──────────────────────────────────────────────────────────────
FROM ${BASE_IMAGE} AS runtime

ARG ROS_DISTRO=jazzy
ARG INSTALL_PREFIX=/opt/ros/myproject

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3-pip \
    && pip install rdt \
    && rm -rf /var/lib/apt/lists/*

# Bring sources in temporarily to resolve rosdep runtime dependencies
COPY --from=builder /ws/src /tmp/ws/src
WORKDIR /tmp/ws
RUN rdt deps --ros-distro ${ROS_DISTRO} --skip-vcs \
    && rm -rf /tmp/ws \
    && rm -rf /var/lib/apt/lists/*

# Install only the compiled artifacts — no sources, no build cache
COPY --from=builder ${INSTALL_PREFIX} ${INSTALL_PREFIX}

WORKDIR /
ENTRYPOINT ["/bin/bash", "-c", ". ${INSTALL_PREFIX}/setup.bash && exec \"$@\"", "--"]
CMD ["bash"]
```

### 6.3 How `rdt build-docker` drives the build

```
rdt build-docker
  │
  ├── resolves image name:  <registry>/<project>:<tag>   (§5.1)
  ├── resolves ROS_DISTRO:  from config / CLI flag
  ├── resolves INSTALL_PREFIX: /opt/ros/<project-name>   (overridable)
  │
  └── calls (docker backend):
        docker build \
          --build-arg ROS_DISTRO=<distro> \
          --build-arg INSTALL_PREFIX=<prefix> \
          --build-arg BASE_IMAGE=<base> \
          -t <image>:<tag> \
          -f <dockerfile> \
          .
```

`rdt deploy-docker` is a separate step that calls `docker push <image>:<tag>` after login.

### 6.4 Overriding the base image

Set `docker.base_image` in `.rdt.yaml` to use a custom base (e.g. one with proprietary drivers pre-installed):

```yaml
docker:
  base_image: registry.myorg.com/ros-etherlab:jazzy
```

This value is passed as the `BASE_IMAGE` build-arg to both stages.

---

## 7. Rootless Docker Builds with Kaniko (GitLab CI)

GitLab CI in rootless mode (no DinD) cannot run `docker build`. Use **Kaniko**:

- `--builder kaniko` calls the `executor` binary (available in `gcr.io/kaniko-project/executor` image).
- The GitLab CI job must use that image or have `executor` on PATH.
- Kaniko pushes the image directly to the registry during build — **no separate `rdt deploy-docker` step needed** when using Kaniko.

**What `rdt build-docker --builder kaniko` calls:**

```
/kaniko/executor \
  --context dir://. \
  --dockerfile <dockerfile> \
  --build-arg ROS_DISTRO=<distro> \
  --build-arg INSTALL_PREFIX=<prefix> \
  --build-arg BASE_IMAGE=<base> \
  --destination <registry>/<project>:<tag>
```

Registry credentials are read from `REGISTRY_USER` / `REGISTRY_TOKEN` env vars and written to `/kaniko/.docker/config.json` before invoking the executor.

---

## 8. Typical Usage Patterns

### Local development

```bash
pip install rdt
rdt deps
rdt build
rdt test
```

### GitHub Actions

```yaml
jobs:
  ci:
    runs-on: ubuntu-latest
    container: ros:jazzy-ros-base
    steps:
      - uses: actions/checkout@v4
      - run: pip install rdt
      - run: rdt deps
      - run: rdt build
      - run: rdt test
      - run: rdt build-docker
      - run: rdt deploy-docker
        env:
          REGISTRY_USER: ${{ github.actor }}
          REGISTRY_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### GitLab CI

```yaml
build-test:
  image: ros:jazzy-ros-base
  script:
    - pip install rdt
    - rdt deps
    - rdt build
    - rdt test

build-docker:
  image:
    name: gcr.io/kaniko-project/executor:debug
    entrypoint: [""]
  script:
    - pip install rdt
    - rdt build-docker --builder kaniko
  variables:
    REGISTRY_USER: $CI_REGISTRY_USER
    REGISTRY_TOKEN: $CI_REGISTRY_PASSWORD

deploy-doc:
  image: python:3.12
  script:
    - pip install rdt
    - rdt build-doc
    - rdt deploy-doc
  only:
    - main
```

---

## 9. Installation

```bash
pip install rdt
```

Or from source:

```bash
pip install -e rdt/
```

The package will be published to PyPI. Pin a version in CI for stability:

```bash
pip install rdt==0.2.1
```

---

## 9. Out of Scope

- Rocker / demo launching (can be added later as `rdt demo`)
- Multi-recipe plugin system
- Dagger integration
- Non-ROS2 projects
