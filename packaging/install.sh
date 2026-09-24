#!/bin/sh
# One-line installer for macOS and Linux:
#   sh -c "$(curl -fsSL https://raw.githubusercontent.com/CalvinKirs/plume/main/packaging/install.sh)"
# Files downloaded with curl carry no macOS quarantine flag, so Gatekeeper does not block the program.
set -eu

REPO="${PLUME_REPO:-CalvinKirs/plume}"

case "$(uname -s)-$(uname -m)" in
  Darwin-arm64)  asset=plume-macos-arm64 ;;
  Linux-x86_64)  asset=plume-linux-x86_64 ;;
  Darwin-x86_64) echo "Intel Macs have no prebuilt program; run from source (see README)." >&2; exit 1 ;;
  *) echo "Unsupported platform: $(uname -s) $(uname -m)" >&2; exit 1 ;;
esac

# GitHub's "latest" release never includes pre-releases, so ask for the newest release of any kind.
# PLUME_VERSION=v0.1.0-alpha.1 picks a specific one.
tag_of_newest_release() {
  sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' | head -n 1
}
tag="${PLUME_VERSION:-$(curl -fsSL "https://api.github.com/repos/$REPO/releases?per_page=1" | tag_of_newest_release)}"
[ -n "$tag" ] || { echo "Could not find a release of $REPO." >&2; exit 1; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
echo "Downloading $asset ($tag) ..."
curl -fSL --progress-bar "https://github.com/$REPO/releases/download/$tag/$asset.tar.gz" -o "$tmp/plume.tar.gz"
tar -xzf "$tmp/plume.tar.gz" -C "$tmp"
# setup asks questions, so read the answers from the terminal even if this script arrives through a pipe
if [ -t 0 ]; then "$tmp/plume/plume" setup; else "$tmp/plume/plume" setup </dev/tty; fi
