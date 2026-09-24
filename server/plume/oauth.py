import base64
import hashlib
import json
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

from .errors import AuthError

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE_INSERT = "https://www.googleapis.com/auth/gmail.insert"  # Insert only. This scope cannot read or send mail.


class GoogleOAuth:
    """OAuth 2.0 client for installed apps (authorization code flow with PKCE)."""

    def __init__(self, client_id, client_secret, transport, now=time.time):
        self.client_id, self.client_secret, self.transport, self.now = client_id, client_secret, transport, now

    def authorization_url(self, redirect_uri, state, challenge):
        return AUTH_URL + "?" + urlencode({
            "client_id": self.client_id, "redirect_uri": redirect_uri, "response_type": "code",
            "scope": SCOPE_INSERT, "state": state, "access_type": "offline", "prompt": "consent",
            "code_challenge": challenge, "code_challenge_method": "S256",
        })

    def exchange_code(self, code, verifier, redirect_uri):
        return self._token_request({
            "grant_type": "authorization_code", "code": code,
            "code_verifier": verifier, "redirect_uri": redirect_uri,
        })

    def refresh(self, refresh_token):
        return self._token_request({"grant_type": "refresh_token", "refresh_token": refresh_token})

    def _token_request(self, params):
        params = dict(params, client_id=self.client_id, client_secret=self.client_secret)
        status, body = self.transport.request(
            "POST", TOKEN_URL, {"Content-Type": "application/x-www-form-urlencoded"}, urlencode(params).encode())
        try:
            data = json.loads(body)
        except ValueError:
            data = {}
        if status != 200 or "access_token" not in data:
            raise AuthError(f"token endpoint refused the request: {data.get('error', status)}")
        token = {"access_token": data["access_token"], "expires_at": self.now() + int(data.get("expires_in", 3600))}
        if data.get("refresh_token"):
            token["refresh_token"] = data["refresh_token"]
        return token


def pkce_pair():
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def run_local_auth(oauth, store, open_browser=webbrowser.open, out=print, timeout=300):
    """One-time interactive authorization using a loopback redirect on 127.0.0.1."""
    verifier, challenge = pkce_pair()
    state = secrets.token_urlsafe(16)
    result = {}

    class Catcher(BaseHTTPRequestHandler):
        def do_GET(self):
            q = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
            if q.get("state") == state and "code" in q:
                result["code"] = q["code"]
                text = "Plume is authorized. You can close this tab."
            else:
                result["error"] = q.get("error", "unexpected callback")
                text = "Authorization failed."
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(text.encode())

        def log_message(self, *args):
            pass

    httpd = HTTPServer(("127.0.0.1", 0), Catcher)
    httpd.timeout = 5
    redirect = f"http://127.0.0.1:{httpd.server_address[1]}"
    url = oauth.authorization_url(redirect, state, challenge)
    out("Open this URL to authorize Plume (Gmail insert-only access):\n" + url)
    open_browser(url)
    deadline = time.time() + timeout
    while not result and time.time() < deadline:
        httpd.handle_request()
    httpd.server_close()
    if "code" not in result:
        raise AuthError(result.get("error", "timed out waiting for authorization"))
    store.save(oauth.exchange_code(result["code"], verifier, redirect))
