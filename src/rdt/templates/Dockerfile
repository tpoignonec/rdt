ARG ROS_DISTRO=jazzy
ARG BASE_IMAGE=ros:${ROS_DISTRO}-ros-base

# ── Builder ───────────────────────────────────────────────────────────────────
# Full build environment: installs all deps and compiles in Release mode.
# Artifacts land at INSTALL_PREFIX — nothing else is kept.
FROM ${BASE_IMAGE} AS builder

ARG ROS_DISTRO=jazzy
ARG INSTALL_PREFIX=/opt/ros/PROJECT_NAME

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

# ── Runtime ───────────────────────────────────────────────────────────────────
# Lean image: only runtime rosdep dependencies + compiled artifacts.
FROM ${BASE_IMAGE} AS runtime

ARG ROS_DISTRO=jazzy
ARG INSTALL_PREFIX=/opt/ros/PROJECT_NAME

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3-pip \
    && pip install rdt \
    && rm -rf /var/lib/apt/lists/*

# Bring sources in temporarily to resolve rosdep dependencies, then discard them
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
