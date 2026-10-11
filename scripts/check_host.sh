#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
#
# Check that this machine can serve as the Aureproof evaluation/isolation host
# (see docs/guides/linux-host.md). Read-only, except that it pulls one small
# public image and runs it with networking disabled to confirm egress is blocked.
set -euo pipefail

IMAGE="${AUREPROOF_CHECK_IMAGE:-busybox:1.36}"
failures=0

pass() { printf '  PASS  %s\n' "$1"; }
fail() { printf '  FAIL  %s\n' "$1"; failures=$((failures + 1)); }
warn() { printf '  WARN  %s\n' "$1"; }

echo "Aureproof evaluation-host check"

# Linux kernel: Docker Desktop VMs on macOS/Windows are for development only.
if [[ "$(uname -s)" == "Linux" ]]; then
  pass "Linux kernel $(uname -r)"
else
  fail "not Linux ($(uname -s)); use a Linux host or VM for isolation work"
fi

# cgroup v2 (resource limits for sandboxes).
if [[ -f /sys/fs/cgroup/cgroup.controllers ]]; then
  pass "cgroup v2"
else
  fail "cgroup v2 not mounted at /sys/fs/cgroup"
fi

# nftables: Harbor's egress allowlist (v0.2) depends on it.
if command -v nft >/dev/null 2>&1; then
  pass "nftables: $(nft --version 2>/dev/null | head -1)"
else
  fail "nft not found (install the nftables package)"
fi
if [[ -r /proc/modules ]] && grep -q '^nf_tables ' /proc/modules; then
  pass "nf_tables kernel module loaded"
else
  warn "nf_tables not listed in /proc/modules (it may be built in; otherwise: sudo modprobe nf_tables)"
fi

# Docker Engine, and a container with networking disabled really has no egress.
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  pass "Docker Engine $(docker version --format '{{.Server.Version}}' 2>/dev/null)"
  if docker run --rm --network none "$IMAGE" true >/dev/null 2>&1; then
    pass "container starts with --network none"
    if docker run --rm --network none "$IMAGE" wget -q -T 3 -O /dev/null http://example.com >/dev/null 2>&1; then
      fail "egress was possible with --network none"
    else
      pass "egress blocked with --network none"
    fi
  else
    fail "could not run $IMAGE with --network none (can the image be pulled?)"
  fi
else
  fail "Docker Engine not reachable (install Docker Engine; add your user to the docker group)"
fi

# Toolchain.
if command -v uv >/dev/null 2>&1; then
  pass "uv $(uv --version | awk '{print $2}')"
else
  fail "uv not found (https://docs.astral.sh/uv/)"
fi
if command -v git >/dev/null 2>&1; then
  pass "git $(git --version | awk '{print $3}')"
else
  fail "git not found"
fi

echo
if ((failures == 0)); then
  echo "Host is ready."
else
  echo "${failures} check(s) failed."
fi
exit $((failures > 0 ? 1 : 0))
