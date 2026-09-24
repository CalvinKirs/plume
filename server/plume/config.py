import json
import os
from dataclasses import dataclass, field


# The extension's manifest pins a key, so its origin is stable across machines.
EXTENSION_ORIGIN = "chrome-extension://mabkbpnhmakajgmgpcehigllechcaehb"


@dataclass(frozen=True)
class Config:
    smtp_host: str = "mail-relay.apache.org"
    smtp_port: int = 587
    user: str = ""
    password: str = ""
    token: str = ""
    listen_port: int = 8765
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    token_path: str = "~/.config/plume/gmail-token.json"
    allowed_origins: tuple = field(default_factory=lambda: (EXTENSION_ORIGIN, "https://mail.google.com"))


DEFAULT_CONFIG_PATH = "~/.config/plume/config.json"

_STR_KEYS = ("smtp_host", "user", "password", "token", "gmail_client_id", "gmail_client_secret", "token_path")
_INT_KEYS = ("smtp_port", "listen_port")
_ENV_NAMES = {"listen_port": "PLUME_PORT"}


def _read_file(path):
    try:
        with open(os.path.expanduser(path)) as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def load_config(env=None, path=None):
    """Settings from the config file, overridden by PLUME_* environment variables.

    A browser-launched native host has no shell environment, so the file is the normal source;
    the environment stays useful for the HTTP server and for tests.
    """
    env = os.environ if env is None else env
    values = _read_file(path or env.get("PLUME_CONFIG", DEFAULT_CONFIG_PATH))
    for key in _STR_KEYS + _INT_KEYS:
        name = _ENV_NAMES.get(key, "PLUME_" + key.upper())
        if name in env:
            values[key] = env[name]
    for key in _INT_KEYS:
        if key in values:
            values[key] = int(values[key])
    origins = env.get("PLUME_ALLOWED_ORIGINS")
    if origins:
        values["allowed_origins"] = tuple(o for o in origins.split() if o)
    known = set(_STR_KEYS + _INT_KEYS + ("allowed_origins",))
    return Config(**{k: v for k, v in values.items() if k in known})


def save_config(values, path=DEFAULT_CONFIG_PATH):
    """Write the config file with mode 0600 (it holds the relay password)."""
    path = os.path.expanduser(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(values, f, indent=2)
    os.chmod(path, 0o600)
