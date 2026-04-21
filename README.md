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

## Documentation (`doc-build` / `doc-deploy`)

### Build modes

**Simple (default)** — output goes directly into the output directory:

```
<output_dir>/          # single language
<output_dir>/<lang>/   # multiple languages, with index.html redirect
```

**Multi-version (`--multi-version`)** — output is nested by branch and language,
with a root `index.html` redirect to the default branch/language:

```
<output_dir>/<branch>/<lang>/
<output_dir>/index.html   ← redirects to <default_branch>/<default_lang>/
```

Enable multi-version mode from `.rdt.yaml`:

```yaml
doc:
  multi_version: true
```

### Variables injected into Sphinx

Every `sphinx-build` invocation receives the following `-D` overrides:

| Variable      | Source                                          |
|---------------|-------------------------------------------------|
| `git_branch`  | CI env (`GITHUB_REF_NAME` / `CI_COMMIT_REF_NAME`) or `git branch --show-current` |
| `git_commit`  | CI env (`GITHUB_SHA` / `CI_COMMIT_SHA`) or `git rev-parse HEAD` |
| `release`     | `--release` flag, or nearest `git describe --tags --abbrev=0`, or branch name |
| `language`    | per-language loop value                         |

In `conf.py`, declare matching top-level defaults so Sphinx accepts the overrides:

```python
git_branch = 'unknown'
git_commit = 'unknown'
release = 'dev'
version = release
```

Use a `builder-inited` hook to propagate the values into `rst_prolog` or
`html_context` (after `-D` overrides have been applied):

```python
def _on_builder_inited(app) -> None:
    branch = app.config.git_branch
    commit = app.config.git_commit
    app.config.html_context['current_distro'] = branch
    app.config.rst_prolog = f"""\
.. |current_distro| replace:: {branch}

.. |commit_hash| replace:: {commit}
"""

def setup(app) -> None:
    app.connect('builder-inited', _on_builder_inited)
```

### Multi-language support

rdt executes `conf.py` in an isolated namespace to read `html_context` and determine which
languages to build for each branch. Declare the mapping in `conf.py`:

```python
html_context = {
    'default_branch': 'main',
    'default_language': 'en',
    'language_per_branch': {
        'main':    ['en'],
        'develop': ['en', 'fr'],
    },
}
```

Branches not listed in `language_per_branch` fall back to `default_language`.
When more than one language is configured, rdt runs `sphinx-build -b gettext`
and `sphinx-intl update` before building each language.

### CLI reference

```
rdt doc-build [OPTIONS]

  --sphinx-dir DIR    Sphinx source root (default: doc/sphinx)
  --output-dir DIR    Build output directory (default: doc/sphinx/build/html)
  --multi-version     Build into <output-dir>/<branch>/<lang>/ layout
  --release VERSION   Release string; defaults to nearest git tag
  --use-venv          Build inside an isolated virtualenv (.venv/)

rdt doc-deploy [OPTIONS]

  --built-doc-path DIR   Path to built docs (default: doc.output_dir)
  --publish-root DIR     Local destination when running outside CI
```

### `.rdt.yaml` options

```yaml
doc:
  sphinx_dir: doc/sphinx          # root containing source/ and requirements.txt
  output_dir: doc/sphinx/build/html
  multi_version: false            # true → <output>/<branch>/<lang>/ layout
```

### Deploy targets

| Environment  | Behaviour |
|--------------|-----------|
| GitHub CI    | Clones / creates `gh-pages` branch, force-pushes. Reads `SECRET_TOKEN`. |
| GitLab CI    | Copies built docs to `public/` (GitLab Pages convention). |
| Local        | Copies to `--publish-root` (default `/tmp/rdt-doc-publish`), no push. |
