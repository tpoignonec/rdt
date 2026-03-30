# Project-specific Dockerfile for rdt (Robotics Dev Tools)
# ──────────────────────────────────────────────────────────────────────
# This file is for EXOTIC / project-specific dependencies ONLY.
# Common tools (colcon, rosdep, git) are installed automatically
# by the rdt CI and deploy pipelines — do NOT add them here.
#
# If your project has no special dependencies you can leave this
# file unchanged or delete it entirely.

ARG ROS_DISTRO=jazzy
FROM ros:${ROS_DISTRO}-ros-base

# Example: add project-specific system packages
# RUN apt-get update && apt-get install -y --no-install-recommends \
#       libsomelib-dev \
#     && rm -rf /var/lib/apt/lists/*
