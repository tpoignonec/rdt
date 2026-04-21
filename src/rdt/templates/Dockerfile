ARG ROS_DISTRO=jazzy
ARG BASE_IMAGE=ros:${ROS_DISTRO}-ros-base

# ── Builder ───────────────────────────────────────────────────────────────────
# Full build environment: installs all deps and compiles in Release mode.
# Artifacts land at INSTALL_PREFIX — nothing else is kept.
FROM ${BASE_IMAGE} AS builder

ARG INSTALL_PREFIX=/opt/ros/PROJECT_NAME

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3-pip python3-venv git \
    && python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install git+https://github.com/tpoignonec/rdt.git@main \
    && ln -s /opt/venv/bin/rdt /usr/local/bin/rdt \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ws
COPY . .

# Install all workspace dependencies (apt + rosdep)
RUN rdt deps

# Build in Release mode into the relocatable install prefix
RUN rdt build  --install-base ${INSTALL_PREFIX}

# ── Runtime ───────────────────────────────────────────────────────────────────
# Lean image: only runtime rosdep dependencies + compiled artifacts.
FROM ${BASE_IMAGE} AS runtime

ARG INSTALL_PREFIX=/opt/ros/PROJECT_NAME

# Install rdt
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3-pip python3-venv git \
    && python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install git+https://github.com/tpoignonec/rdt.git@main \
    && ln -s /opt/venv/bin/rdt /usr/local/bin/rdt \
    && rm -rf /var/lib/apt/lists/*

# Bring sources in temporarily to resolve rosdep dependencies, then discard them
COPY . /tmp/ws
WORKDIR /tmp/ws
RUN rdt deps --ros-distro ${ROS_DISTRO} \
    && rm -rf /tmp/ws \
    && rm -rf /var/lib/apt/lists/*

# Install only the compiled artifacts — no sources, no build cache
COPY --from=builder ${INSTALL_PREFIX} ${INSTALL_PREFIX}

WORKDIR /
ENTRYPOINT ["/bin/bash", "-c", ". ${INSTALL_PREFIX}/setup.bash && exec \"$@\"", "--"]
CMD ["bash"]
