"""The browsers Plume can register its native messaging host with.

A browser is a small object that answers three questions: is it installed, where does its host
manifest go, and what does that manifest say about who may start the host. install.py works only
through this interface. Supporting another browser means adding a class here, and nothing about one
browser can change how another is handled.
"""
import os

from .config import EXTENSION_ORIGIN, FIREFOX_EXTENSION_ID


class UnsupportedSystem(Exception):
    pass


def _for_system(table, system):
    try:
        return table[system]
    except KeyError:
        raise UnsupportedSystem(f"{system} is not supported yet (Linux and macOS only)") from None


class Chromium:
    """Chrome and the browsers built on it. They agree on the manifest format: allowed_origins lists the
    origins of the extensions that may start the host, and the manifest sits in the profile directory."""

    def __init__(self, name, linux_profile, mac_profile):
        self.name = name
        self._profiles = {"Linux": linux_profile, "Darwin": mac_profile}

    def _profile(self, home, system):
        return os.path.join(home, _for_system(self._profiles, system))

    def installed(self, home, system):
        return os.path.isdir(self._profile(home, system))

    def manifest_dir(self, home, system):
        return os.path.join(self._profile(home, system), "NativeMessagingHosts")

    def host_manifest(self, base):
        return {**base, "allowed_origins": [EXTENSION_ORIGIN + "/"]}


class Firefox:
    """Firefox names the add-ons that may start the host (allowed_extensions), and keeps host manifests in
    a per-user directory of its own rather than inside a profile."""

    name = "firefox"
    _PROFILES = {"Linux": ".mozilla/firefox", "Darwin": "Library/Application Support/Firefox"}
    _MANIFESTS = {"Linux": ".mozilla/native-messaging-hosts", "Darwin": "Library/Application Support/Mozilla/NativeMessagingHosts"}

    def installed(self, home, system):
        return os.path.isdir(os.path.join(home, _for_system(self._PROFILES, system)))

    def manifest_dir(self, home, system):
        return os.path.join(home, _for_system(self._MANIFESTS, system))

    def host_manifest(self, base):
        return {**base, "allowed_extensions": [FIREFOX_EXTENSION_ID]}


TARGETS = {b.name: b for b in (
    Chromium("chrome", ".config/google-chrome", "Library/Application Support/Google/Chrome"),
    Chromium("chromium", ".config/chromium", "Library/Application Support/Chromium"),
    Chromium("brave", ".config/BraveSoftware/Brave-Browser", "Library/Application Support/BraveSoftware/Brave-Browser"),
    Chromium("edge", ".config/microsoft-edge", "Library/Application Support/Microsoft Edge"),
    Firefox(),
)}
BROWSERS = sorted(TARGETS)
