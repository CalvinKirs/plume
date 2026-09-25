"""Telling a launch by a browser from a person typing a command.

Chrome starts a native messaging host with the origin of the calling extension as its argument.
Firefox starts it with the path of the host manifest, followed by the id of the add-on. Either one
means the program is being used as a host and must speak the native messaging protocol on stdin and
stdout instead of running a command.
"""
import os

from .config import HOST_NAME

_CHROMIUM_PREFIX = "chrome-extension://"


def is_native_launch(argv):
    if not argv:
        return False
    first = argv[0]
    if first.startswith(_CHROMIUM_PREFIX):
        return True
    return os.path.basename(first) == HOST_NAME + ".json"
