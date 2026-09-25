import os
import tempfile

REAL_SOURCE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the server directory of this checkout


def fake_source():
    """A directory shaped like a checkout's server directory: it holds a plume package."""
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, "plume"))
    with open(os.path.join(root, "plume", "__init__.py"), "w") as f:
        f.write("")
    return root
