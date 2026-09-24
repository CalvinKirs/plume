#!/bin/sh
# Builds the `plume` program for the current platform and packs it into dist/<name>.tar.gz.
# Usage: packaging/build.sh [name]      (default name: plume-<os>-<arch>)
#
# This is a one-directory build on purpose. A one-file build unpacks itself into a new temp folder
# on every launch, and on macOS that makes Gatekeeper prompt each time Chrome starts the native host.
set -eu
cd "$(dirname "$0")/.."
name="${1:-plume-$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m)}"
rm -rf dist/plume dist/"$name".tar.gz
python3 -m venv build/venv
build/venv/bin/pip install --quiet pyinstaller
build/venv/bin/pyinstaller --onedir --name plume --paths server --distpath dist --workpath build/pyi \
  --specpath build --clean --noconfirm packaging/entry.py
tar -czf "dist/$name.tar.gz" -C dist plume
echo "built: $(pwd)/dist/plume/plume  and  $(pwd)/dist/$name.tar.gz"
