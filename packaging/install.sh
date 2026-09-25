#!/bin/sh
# One-line installer for macOS and Linux:
#   sh -c "$(curl -fsSL https://raw.githubusercontent.com/CalvinKirs/plume/main/packaging/install.sh)"
#
# It installs a prebuilt program where there is one (macOS on Apple silicon, Linux on x86_64). On any
# other machine, such as an Intel Mac or an ARM Linux box, it installs from source with the Python
# that is already there, so the same command works everywhere. PLUME_FROM_SOURCE=1 forces that route.
# Files downloaded with curl carry no macOS quarantine flag, so Gatekeeper does not block the program.
set -eu

REPO="${PLUME_REPO:-CalvinKirs/plume}"
# What goes into a URL is checked first, so an odd value in the environment (or in a reply from the
# GitHub API) cannot redirect the download or smuggle in a path.
# case matches the whole value, newlines included, which grep -q would not: it accepts a value if any
# one line of it matches.
valid_repo() {
  case "$1" in
    ''|/*|*/|*/*/*|*[!A-Za-z0-9_./-]*) return 1 ;;
    */*) ;;
    *) return 1 ;;
  esac
  case "${1%%/*}" in [!A-Za-z0-9_]*) return 1 ;; esac   # each part starts with a letter, digit or _,
  case "${1#*/}" in [!A-Za-z0-9_]*) return 1 ;; esac    # so it can never be "." or ".."
}
valid_repo "$REPO" || { echo "PLUME_REPO must look like owner/name." >&2; exit 1; }

case "$(uname -s)" in
  Darwin|Linux) ;;
  *) echo "Plume supports macOS and Linux. This is $(uname -s)." >&2; exit 1 ;;
esac

case "$(uname -s)-$(uname -m)" in
  Darwin-arm64) asset=plume-macos-arm64 ;;
  Linux-x86_64) asset=plume-linux-x86_64 ;;
  *) asset="" ;;
esac
# PLUME_FROM_SOURCE=1 forces the source route; empty, 0, false and no leave the default.
case "${PLUME_FROM_SOURCE:-}" in ""|0|false|no) ;; *) asset="" ;; esac

# Every download is https only, redirects included.
fetch() {
  curl --proto '=https' --proto-redir '=https' --tlsv1.2 "$@"
}

# GitHub's "latest" release never includes pre-releases, so ask for the newest release of any kind.
# PLUME_VERSION=v0.1.0-alpha.2 picks a specific one. Only called when a release is actually needed.
tag_of_newest_release() {
  sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' | head -n 1
}
resolve_tag() {
  tag="${PLUME_VERSION:-$(fetch -fsSL "https://api.github.com/repos/$REPO/releases?per_page=1" | tag_of_newest_release)}"
  [ -n "$tag" ] || { echo "Could not find a release of $REPO." >&2; exit 1; }
  case "$tag" in
    [.-]*|*[!A-Za-z0-9._-]*|*..*) echo "That is not a valid release tag: $tag" >&2; exit 1 ;;
  esac
}

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# setup asks questions, so read the answers from the terminal even if this script arrives through a pipe
run_setup() {
  if [ -t 0 ]; then "$@" setup; else "$@" setup </dev/tty; fi
}

if [ -n "$asset" ]; then
  resolve_tag
  echo "Downloading $asset ($tag) ..."
  fetch -fSL --progress-bar "https://github.com/$REPO/releases/download/$tag/$asset.tar.gz" -o "$tmp/plume.tar.gz"
  tar -xzf "$tmp/plume.tar.gz" -C "$tmp"
  run_setup "$tmp/plume/plume"
else
  command -v python3 >/dev/null 2>&1 || { echo "There is no prebuilt program for this machine, and installing from source needs python3 (3.8 or newer)." >&2; exit 1; }
  python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' || { echo "Installing from source needs Python 3.8 or newer. This is $(python3 -V 2>&1)." >&2; exit 1; }
  if [ -n "${PLUME_SOURCE_URL:-}" ]; then
    # A replacement download, for testing a checkout before it is released. No release is needed then.
    src_url="$PLUME_SOURCE_URL"
    echo "Downloading the source from $src_url, to install it with $(python3 -V 2>&1) ..."
  else
    resolve_tag
    src_url="https://github.com/$REPO/archive/refs/tags/$tag.tar.gz"
    echo "Downloading the source of $tag, to install it with $(python3 -V 2>&1) ..."
  fi
  case "$src_url" in
    file://*) curl --proto '=file' -fsSL "$src_url" -o "$tmp/source.tar.gz" ;;  # the test override only
    *) fetch -fSL --progress-bar "$src_url" -o "$tmp/source.tar.gz" ;;
  esac
  tar -xzf "$tmp/source.tar.gz" -C "$tmp"
  # The tarball's top level can hold more than one directory (macOS archivers add __MACOSX),
  # so look for the one that actually carries the program.
  src=""
  for d in "$tmp"/*/server; do
    if [ -d "$d/plume" ]; then src="$d"; break; fi
  done
  [ -n "$src" ] || { echo "The downloaded source does not contain the program." >&2; exit 1; }
  cd "$src"
  run_setup python3 -m plume
fi
