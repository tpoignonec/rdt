# rdt — Robotics Dev Tools

A unified, recipe-driven CLI for build, test, CI/CD, and demo workflows.

> **Status:** Early prototype (v0.1.0). The ROS 2 recipe is the reference implementation.

## Features

- **Recipe-driven** — extensible plugin architecture. Currently ships with a `ros2` recipe; add your own for CMake, Python, or any other project type.
- **Unified CLI** — `rdt local build`, `rdt ci deploy`, `rdt demo launch` — one tool for all workflows.
- **Config-as-code** — `.rdt/config.yaml` per project. CLI flags always override.
- **Dagger-based CI** — containerised, reproducible builds with automatic layer caching.
- **Rocker demos** — launch containers with X11/GPU forwarding in one command.
- **Optional dependencies** — only install what you need (`rdt[ci]`, `rdt[demo]`, `rdt[all]`).

## Installation

### From source (development)

```bash
git clone https://github.com/tpoignonec/rtd.git

# Virtual environment
sudo apt install python3-venv
python3 -m venv .venv
source .venv/bin/activate

# Install package
pip install -e ./rtd
```


### From PyPI

```bash
# Core (local build/test only)
pip install rdt

# With CI support (Dagger)
pip install rdt[ci]

# With demo support (Rocker)
pip install rdt[demo]

# Everything
pip install rdt[all]
```

## Quick start

```bash
# Scaffold a new project
rdt init --recipe ros2

# Build locally
rdt local build --ros-distro jazzy

# Run tests locally
rdt local test --retest-until-pass 2

# Build in CI (Dagger)
rdt ci build

# Run tests in CI
rdt ci test

# Build & deploy Docker image
rdt ci deploy --image-tag 1.0.0 --push

# Launch a demo
rdt demo launch --image my-ros2-image --x11 --gpu
```

## CLI overview

```
rdt --help

Commands:
  init          Scaffold a .rdt/ directory with config and Dockerfile
  local         Local development commands
    build       Build ROS 2 workspace locally using colcon
    test        Run tests locally using colcon
  ci            CI/CD commands (Dagger-based)
    build       Build ROS 2 workspace in CI
    test        Run tests in CI
    deploy      Build & deploy Docker image
  demo          Demo launcher commands
    launch      Launch Rocker demo with X11/GPU support
```

## Project configuration

After running `rdt init`, a `.rdt/` directory is created:

```
.rdt/
├── config.yaml     # Project settings
└── Dockerfile      # Custom base image (optional)
```

See the generated `config.yaml` for all available options.

## Architecture

```
rdt/
├── core/               # Framework infrastructure (no domain knowledge)
│   ├── config.py       # Config loading, discovery, resolve_config()
│   ├── console.py      # Rich-based output (info, debug, abort, …)
│   ├── models.py       # Shared Pydantic types (RosDistro, RosBaseConfig)
│   └── runner.py       # run_command(), run_dagger_pipeline(), make_clean_env()
├── recipes/            # Plugin system
│   ├── base.py         # Abstract Recipe base class
│   ├── __init__.py     # Entry-point discovery
│   └── ros2/           # ROS 2 recipe (reference implementation)
│       ├── models.py   # BuildConfig, TestConfig, DeployConfig, DemoConfig
│       ├── commands.py # Colcon command builders
│       ├── local.py    # rdt local build/test
│       ├── ci.py       # rdt ci build/test/deploy (Dagger)
│       ├── demo.py     # rdt demo launch (Rocker)
│       └── templates/  # config.yaml, Dockerfile, Dockerfile-etherlab
├── devcontainer/       # (future) .devcontainer generation
├── scaffold/           # (future) Package templating
├── cli.py              # Root Click group + recipe registration
└── init.py             # Built-in init command
```

## Adding a new recipe

1. Create a class that inherits from `rdt.recipes.base.Recipe`.
2. Implement all abstract methods.
3. Register it as an entry-point in your `pyproject.toml`:

```toml
[tool.poetry.plugins."rdt.recipes"]
my_recipe = "my_package:MyRecipe"
```

4. Install your package — `rdt init --list-recipes` will show it.

## Development

```bash
cd rdt/
poetry install
poetry run pytest
poetry run ruff check src/ tests/
poetry run mypy src/
```

## Comparison with iris-ros2 (v1)

| Aspect | iris-ros2 (v1) | rdt (v2) |
|---|---|---|
| CLI structure | Flat commands (`local_build`) | Sub-groups (`local build`) |
| Config merging | Duplicated in every handler | Single `resolve_config()` helper |
| ROS distro validation | 4× identical `@field_validator` | Single `Annotated[str, AfterValidator]` type |
| Dagger error handling | 3× duplicated try/except | Single `run_dagger_pipeline()` wrapper |
| Extensibility | ROS 2 only, hardcoded | Recipe plugin system via entry-points |
| Optional deps | All required | Split into `[ci]`, `[demo]`, `[all]` |
| Future growth | Difficult | `devcontainer/`, `scaffold/`, new recipes |
