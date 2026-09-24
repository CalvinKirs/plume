import base64
import json
import unittest
from email.message import EmailMessage
from urllib.parse import parse_qs, urlparse

from plume.errors import ArchiveError, AuthError
from plume.gmail import GmailArchive
from plume.oauth import GoogleOAuth, pkce_pair
from plume.tokens import FileTokenStore, TokenProvider


class FakeTransport:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def request(self, method, url, headers, body):
        self.calls.append((method, url, headers, body))
        status, data = self.responses.pop(0)
        return status, json.dumps(data).encode()


class MemStore:
    def __init__(self, tok=None):
        self.tok = tok

    def load(self):
        return dict(self.tok) if self.tok else None

    def save(self, tok):
        self.tok = dict(tok)


def sample():
    m = EmailMessage()
    m["From"], m["To"], m["Cc"], m["Subject"], m["Message-ID"] = "a@apache.org", "d@x.org", "c@x.org", "s", "<1@apache.org>"
    m.set_content("hi")
    return m


class OAuthTests(unittest.TestCase):
    def oauth(self, transport):
        return GoogleOAuth("cid", "sec", transport, now=lambda: 1000)

    def test_authorization_url(self):
        _, challenge = pkce_pair()
        q = parse_qs(urlparse(self.oauth(None).authorization_url("http://127.0.0.1:1", "st", challenge)).query)
        self.assertEqual(q["scope"], ["https://www.googleapis.com/auth/gmail.insert"])
        self.assertEqual(q["code_challenge_method"], ["S256"])
        self.assertEqual(q["access_type"], ["offline"])

    def test_pkce_challenge_matches_verifier(self):
        import hashlib
        v, c = pkce_pair()
        self.assertEqual(c, base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).rstrip(b"=").decode())

    def test_exchange_and_refresh(self):
        t = FakeTransport((200, {"access_token": "a1", "expires_in": 3600, "refresh_token": "r1"}),
                          (200, {"access_token": "a2", "expires_in": 100}))
        o = self.oauth(t)
        self.assertEqual(o.exchange_code("c", "v", "http://x"), {"access_token": "a1", "expires_at": 4600, "refresh_token": "r1"})
        self.assertEqual(o.refresh("r1"), {"access_token": "a2", "expires_at": 1100})
        self.assertIn(b"grant_type=refresh_token", t.calls[1][3])

    def test_refused(self):
        with self.assertRaises(AuthError):
            self.oauth(FakeTransport((400, {"error": "invalid_grant"}))).refresh("r")


class TokenTests(unittest.TestCase):
    def test_uses_cached_then_refreshes(self):
        store = MemStore({"refresh_token": "r", "access_token": "old", "expires_at": 1030})
        t = FakeTransport((200, {"access_token": "new", "expires_in": 3600}))
        prov = TokenProvider(GoogleOAuth("c", "s", t, now=lambda: 1000), store, now=lambda: 1000)
        self.assertEqual(prov.access_token(), "new")  # within the 60s skew: refreshed
        self.assertEqual(store.tok["refresh_token"], "r")
        self.assertEqual(prov.access_token(), "new")  # now cached
        self.assertEqual(len(t.calls), 1)

    def test_not_authorized(self):
        with self.assertRaises(AuthError):
            TokenProvider(None, MemStore()).access_token()

    def test_file_store_mode(self):
        import os, tempfile
        path = os.path.join(tempfile.mkdtemp(), "sub", "tok.json")
        s = FileTokenStore(path)
        self.assertIsNone(s.load())
        s.save({"a": 1})
        self.assertEqual(s.load(), {"a": 1})
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)


class TokensStub:
    def __init__(self):
        self.forced = []

    def access_token(self, force_refresh=False):
        self.forced.append(force_refresh)
        return "tok2" if force_refresh else "tok1"


class GmailArchiveTests(unittest.TestCase):
    def test_insert_request(self):
        t = FakeTransport((200, {"id": "m1"}))
        self.assertEqual(GmailArchive(TokensStub(), t).archive(sample(), "th1"), "m1")
        method, url, headers, body = t.calls[0]
        self.assertTrue(url.endswith("/messages?internalDateSource=dateHeader"))
        self.assertEqual(headers["Authorization"], "Bearer tok1")
        data = json.loads(body)
        self.assertEqual((data["labelIds"], data["threadId"]), (["SENT"], "th1"))
        self.assertIn(b"Message-ID: <1@apache.org>", base64.urlsafe_b64decode(data["raw"]))

    def test_retries_once_on_401(self):
        toks, t = TokensStub(), FakeTransport((401, {}), (200, {"id": "m2"}))
        self.assertEqual(GmailArchive(toks, t).archive(sample()), "m2")
        self.assertEqual(toks.forced, [False, True])
        self.assertEqual(t.calls[1][2]["Authorization"], "Bearer tok2")

    def test_failures_become_archive_errors(self):
        with self.assertRaises(ArchiveError):
            GmailArchive(TokensStub(), FakeTransport((500, {}))).archive(sample())

        class NoAuth:
            def access_token(self, force_refresh=False):
                raise AuthError("run auth")
        with self.assertRaises(ArchiveError):
            GmailArchive(NoAuth(), FakeTransport()).archive(sample())


if __name__ == "__main__":
    unittest.main()
