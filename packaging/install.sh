#!/bin/sh
# One-line installer for macOS and Linux:
#   sh -c "$(curl -fsSL https://raw.githubusercontent.com/CalvinKirs/plume/main/packaging/install.sh)"
# Files fetched with curl carry no macOS quarantine flag, so Gatekeeper does not block the program.
set -eu

REPO="${PLUME_REPO:-CalvinKirs/plume}"

case "$(uname -s)-$(uname -m)" in
  Darwin-arm64)  asset=plume-macos-arm64 ;;
  Linux-x86_64)  asset=plume-linux-x86_64 ;;
  Darwin-x86_64) echo "Intel Macs have no prebuilt program; run from source (see README)." >&2; exit 1 ;;
  *) echo "Unsupported platform: $(uname -s) $(uname -m)" >&2; exit 1 ;;
esac

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
echo "Downloading $asset ..."
curl -fSL --progress-bar "https://github.com/$REPO/releases/latest/download/$asset.tar.gz" -o "$tmp/plume.tar.gz"
tar -xzf "$tmp/plume.tar.gz" -C "$tmp"
# setup asks questions: read them from the terminal even when this script itself came through a pipe
if [ -t 0 ]; then "$tmp/plume/plume" setup; else "$tmp/plume/plume" setup </dev/tty; fi
