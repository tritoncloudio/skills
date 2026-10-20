#!/usr/bin/env bash
#
# Regenerate skills/tritoncloud/references from mariana-trench.
#
# Usage: scripts/update-references.sh [branch]
#
# MARIANA_DIR=<checkout> uses an existing checkout instead of cloning.
# TRITONCTL=<binary> uses an existing tritonctl instead of building one.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BRANCH="${1:-main}"
REPO_URL="${MARIANA_REPO_URL:-https://github.com/TritonDataCenter/mariana-trench.git}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

src="${MARIANA_DIR:-}"
if [[ -z "$src" ]]; then
    src="$TMP_DIR/mariana-trench"
    echo "Cloning mariana-trench ($BRANCH)..."
    git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$src"
fi

bin="${TRITONCTL:-}"
if [[ -z "$bin" ]]; then
    echo "Building tritonctl..."
    git -C "$src" submodule update --quiet --init --depth 1 \
        images/triton-platform/manta-storage
    cargo install --quiet --locked --root "$TMP_DIR/cargo" --path "$src/cli/tritonctl"
    bin="$TMP_DIR/cargo/bin/tritonctl"
fi

python3 "$SCRIPT_DIR/generate.py" --tritonctl "$bin" --source "$src"
