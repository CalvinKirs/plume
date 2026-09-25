import sys

if sys.version_info < (3, 8):
    raise SystemExit("Plume needs Python 3.8 or newer, and this is Python %d.%d." % sys.version_info[:2])

__version__ = "0.1.0-alpha.3"
