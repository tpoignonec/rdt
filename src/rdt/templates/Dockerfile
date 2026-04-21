ARG ROS_DISTRO=jazzy
ARG BASE_IMAGE=ros:${ROS_DISTRO}-ros-base

# ── Deps ──────────────────────────────────────────────────────────────────────
# Installs rdt and all workspace dependencies (apt + rosdep + vcs).
# Git credentials (optional — pass via rdt docker-build):
#   HTTPS token  --secret id=git_token,env=GIT_TOKEN
#   SSH agent    --ssh default
FROM ${BASE_IMAGE} AS deps

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3-pip python3-venv git openssh-client \
    && python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install git+https://github.com/tpoignonec/rdt.git@main \
    && ln -s /opt/venv/bin/rdt /usr/local/bin/rdt \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ws
COPY . .

RUN --mount=type=secret,id=git_token,required=false \
    --mount=type=ssh,required=false \
    set -e \
    && GIT_TOKEN="$(cat /run/secrets/git_token 2>/dev/null || true)" \
    && if [ -n "$GIT_TOKEN" ]; then \
           git config --global \
               url."https://gitlab-ci-token:${GIT_TOKEN}@git.unistra.fr/".insteadOf \
               "https://git.unistra.fr/"; \
       else \
           mkdir -p /root/.ssh \
           && ssh-keyscan git.unistra.fr >> /root/.ssh/known_hosts 2>/dev/null \
           && git config --global \
               url."git@git.unistra.fr:".insteadOf "https://git.unistra.fr/"; \
       fi \
    && rdt deps \
    && git config --global --remove-section \
        "url.https://gitlab-ci-token:${GIT_TOKEN}@git.unistra.fr/" 2>/dev/null || true

# ── Builder ───────────────────────────────────────────────────────────────────
# Compiles the workspace in Release mode. Artifacts land at INSTALL_PREFIX.
FROM deps AS builder

ARG INSTALL_PREFIX=/opt/ros/PROJECT_NAME

RUN rdt build --install-base ${INSTALL_PREFIX}

# ── Runtime ───────────────────────────────────────────────────────────────────
# Lean image: deps already installed, sources discarded, only built artifacts kept.
FROM deps AS runtime

ARG INSTALL_PREFIX=/opt/ros/PROJECT_NAME

# Cleanup sources and intermediate files, keep only built artifacts.
RUN rm -rf /ws

# Copy built artifacts from builder stage.
COPY --from=builder ${INSTALL_PREFIX} ${INSTALL_PREFIX}

WORKDIR /
ENTRYPOINT ["/bin/bash", "-c", ". ${INSTALL_PREFIX}/setup.bash && exec \"$@\"", "--"]
CMD ["bash"]
