#!/usr/bin/env bash
# Screen-recording helper for the speedrun team video.
# Each command is typed out, run for real, then the script waits for Enter,
# so you can talk over the output at your own pace.
cd "$(dirname "$0")/../../.." || exit 1

run() {
  printf '\n\033[1;32m$\033[0m '
  for ((i = 0; i < ${#1}; i++)); do printf '%s' "${1:i:1}"; sleep 0.02; done
  printf '\n'
  eval "$1"
  read -r _
}

clear
run "uv run --extra sign aureproof validate bundles/m2-slice-2 --require-signature"
run "uv run aureproof score bundles/m2-slice-2 --offline"
run "uv run aureproof compare --protocol protocols/agent-explore/protocol.json --a bundles/agent-explore-A --b bundles/agent-explore-B | head -4"
