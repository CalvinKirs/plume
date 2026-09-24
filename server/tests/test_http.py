import json
import smtplib
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from plume.app import make_handler
from plume.config import Config
from plume.service import SendService

from test_message import payload


class FakeMailer:
    def __init__(self):
        self.sent, self.error = [], None

    def send(self, msg, recipients):
        if self.error:
            raise self.error
        self.sent.append((msg, recipients))


class FakeArchive:
    def __init__(self):
        self.stored, self.error = [], None

    def archive(self, msg, thread_id=None):
        if self.error:
            raise self.error
        self.stored.append((msg, thread_id))
        return "gm-1"


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.mailer, self.archive = FakeMailer(), FakeArchive()
        cfg = Config(user="u", password="p", token="secret")
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cfg, SendService(self.mailer, self.archive)))
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def post(self, body, token="secret", origin=None):
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if origin:
            headers["Origin"] = origin
        req = urllib.request.Request(self.url + "/send", json.dumps(body).encode(), headers)
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_send_ok_and_archived(self):
        status, body = self.post(payload(threadId="t9"), origin="https://mail.google.com")
        self.assertEqual(status, 200)
        self.assertTrue(body["archived"])
        self.assertEqual(body["archiveId"], "gm-1")
        self.assertEqual(len(self.mailer.sent), 1)
        self.assertEqual(self.archive.stored[0][1], "t9")

    def test_auth_and_origin(self):
        self.assertEqual(self.post(payload(), token="wrong")[0], 401)
        self.assertEqual(self.post(payload(), token=None)[0], 401)
        self.assertEqual(self.post(payload(), origin="https://evil.example")[0], 403)
        self.assertEqual(self.mailer.sent, [])

    def test_bad_payload_and_relay_errors(self):
        self.assertEqual(self.post(payload(to=[]))[0], 400)
        self.mailer.error = smtplib.SMTPAuthenticationError(535, b"no")
        self.assertEqual(self.post(payload())[0], 502)
        self.mailer.error = ConnectionRefusedError("down")
        self.assertEqual(self.post(payload())[0], 502)
        self.assertEqual(self.archive.stored, [])

    def test_archive_failure_does_not_fail_send(self):
        self.archive.error = RuntimeError("gmail down")
        status, body = self.post(payload())
        self.assertEqual(status, 200)
        self.assertFalse(body["archived"])
        self.assertIn("gmail down", body["archiveError"])


if __name__ == "__main__":
    unittest.main()
