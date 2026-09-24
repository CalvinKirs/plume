import json
import os
import time

from .errors import AuthError


class FileTokenStore:
    """JSON token file, created with mode 0600."""

    def __init__(self, path):
        self.path = os.path.expanduser(path)

    def load(self):
        try:
            with open(self.path) as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    def save(self, token):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(token, f)
        os.replace(tmp, self.path)


class TokenProvider:
    """Hands out a valid access token, refreshing and persisting as needed."""

    def __init__(self, oauth, store, now=time.time, skew=60):
        self.oauth, self.store, self.now, self.skew = oauth, store, now, skew

    def access_token(self, force_refresh=False):
        tok = self.store.load()
        if not tok or not tok.get("refresh_token"):
            raise AuthError("no Gmail authorization yet: run `python3 -m plume auth`")
        if not force_refresh and tok.get("access_token") and tok.get("expires_at", 0) - self.skew > self.now():
            return tok["access_token"]
        tok.update(self.oauth.refresh(tok["refresh_token"]))
        self.store.save(tok)
        return tok["access_token"]
