"""Register Plume as a native messaging host with the installed browsers (Linux and macOS)."""
import json
import os
import platform
import shlex
import shutil
import stat
import subprocess
import sys

from .browsers import BROWSERS, TARGETS, UnsupportedSystem  # noqa: F401  (BROWSERS is re-exported for the CLI)
from .config import HOST_NAME


def _frozen_binary():
    return sys.executable if getattr(sys, "frozen", False) else None


def _strip_quarantine(path):
    """Try to clear the macOS quarantine flag. The user chose to run this program, so the installed copy should not be quarantined."""
    subprocess.run(["xattr", "-dr", "com.apple.quarantine", path], capture_output=True, check=False)


def install_host(home=None, python=None, server_dir=None, browsers=None, system=None, binary=None):
    """Register the host with each browser and return the paths of the manifests written.

    Run from source, the host is a small launcher script that starts `python -m plume native`.
    Run from a packaged build (`binary`), the program itself is copied to a fixed location and
    registered. Chrome starts it with the extension's origin as an argument, and the program
    takes that as the cue to run in native mode.

    A PyInstaller one-directory build (a folder holding the program and `_internal/`) is copied
    as a whole. This matters on macOS: files unpacked at run time by a process that Chrome started
    get the quarantine flag, and Gatekeeper then prompts on every launch. Nothing may be unpacked
    at run time.
    """
    binary = binary or _frozen_binary()
    home = home or os.path.expanduser("~")
    python = python or sys.executable
    server_dir = server_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    system = system or platform.system()
    if browsers:
        unknown = set(browsers) - set(TARGETS)
        if unknown:
            raise SystemExit(f"unknown browser: {', '.join(sorted(unknown))}")
        targets = [TARGETS[name] for name in browsers]
    else:
        try:
            targets = [b for b in TARGETS.values() if b.installed(home, system)]
        except UnsupportedSystem as e:
            raise SystemExit(f"install-host: {e}") from None
        if not targets:
            raise SystemExit("no Chrome, Chromium, Brave, Edge or Firefox profile found; pass --browser <name>")

    install_dir = os.path.join(home, ".local", "share", "plume")
    os.makedirs(install_dir, exist_ok=True)
    if binary:
        binary = os.path.abspath(binary)
        src_dir = os.path.dirname(binary)
        if os.path.isdir(os.path.join(src_dir, "_internal")):  # a one-directory build
            app_dir = os.path.join(install_dir, "app")
            if src_dir != os.path.abspath(app_dir):
                shutil.rmtree(app_dir, ignore_errors=True)
                shutil.copytree(src_dir, app_dir, symlinks=True)
            launcher, cleanup = os.path.join(app_dir, os.path.basename(binary)), app_dir
            old = os.path.join(install_dir, "plume")  # left over from an earlier single-file install
            if os.path.isfile(old):
                os.remove(old)
        else:  # single file
            launcher = cleanup = os.path.join(install_dir, "plume")
            if binary != os.path.abspath(launcher):
                shutil.copy2(binary, launcher)
        if system == "Darwin":
            _strip_quarantine(cleanup)
    else:
        launcher = os.path.join(install_dir, "plume-native-host")
        with open(launcher, "w") as f:
            f.write(f"#!/bin/sh\nexport PYTHONPATH={shlex.quote(server_dir)}\nexec {shlex.quote(python)} -m plume native\n")
    os.chmod(launcher, os.stat(launcher).st_mode | stat.S_IXUSR)

    base = {
        "name": HOST_NAME,
        "description": "Plume: send mail through the ASF relay",
        "path": launcher,
        "type": "stdio",
    }
    written = []
    for browser in targets:
        try:
            host_dir = browser.manifest_dir(home, system)
        except UnsupportedSystem as e:
            raise SystemExit(f"install-host: {e}") from None
        os.makedirs(host_dir, exist_ok=True)
        path = os.path.join(host_dir, HOST_NAME + ".json")
        with open(path, "w") as f:
            json.dump(browser.host_manifest(base), f, indent=2)
        written.append(path)
    return written
