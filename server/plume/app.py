import hmac
import json
from http.server import BaseHTTPRequestHandler

from .api import send_payload

MAX_BODY = 25 * 1024 * 1024


def make_handler(cfg, service):
    class Handler(BaseHTTPRequestHandler):
        server_version = "Plume"

        def log_message(self, fmt, *args):
            pass  # never log message contents or headers

        def _origin_ok(self):
            origin = self.headers.get("Origin")
            return origin is None or origin in cfg.allowed_origins

        def _reply(self, status, body):
            data = json.dumps(body).encode()
            self.send_response(status)
            origin = self.headers.get("Origin")
            if origin and origin in cfg.allowed_origins:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_OPTIONS(self):
            if not self._origin_ok():
                return self._reply(403, {"error": "origin not allowed"})
            self.send_response(204)
            origin = self.headers.get("Origin")
            if origin:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "POST, GET")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.end_headers()

        def do_GET(self):
            if self.path == "/health":
                return self._reply(200, {"ok": True})
            self._reply(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/send":
                return self._reply(404, {"error": "not found"})
            if not self._origin_ok():
                return self._reply(403, {"error": "origin not allowed"})
            supplied = self.headers.get("Authorization", "")
            expected = f"Bearer {cfg.token}"
            if not cfg.token or not hmac.compare_digest(supplied, expected):
                return self._reply(401, {"error": "bad token"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if length <= 0 or length > MAX_BODY:
                return self._reply(400, {"error": "bad content length"})
            try:
                payload = json.loads(self.rfile.read(length))
            except ValueError as e:
                return self._reply(400, {"ok": False, "error": str(e)})
            status, body = send_payload(service, payload)
            self._reply(status, body)

    return Handler

