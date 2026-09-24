import io
import os
import tempfile
import unittest
from unittest import mock

from plume.native import serve

from test_native import GOOD, frame, replies


class HostRobustnessTests(unittest.TestCase):
    def test_unexpected_exception_is_a_reply_not_a_crash(self):
        class Boom:
            def send(self, *a, **k):
                raise RuntimeError("kaboom")
        out = io.BytesIO()
        serve(Boom(), io.BytesIO(frame({"type": "send", "payload": GOOD}) * 2), out)
        replies_ = replies(out.getvalue())
        self.assertEqual(len(replies_), 2)  # still alive for the second message
        self.assertIn("kaboom", replies_[0]["error"])

    def test_unreadable_config_is_reported_to_the_extension(self):
        import sys
        from types import SimpleNamespace
        from unittest import mock
        from plume import cli
        bad = os.path.join(tempfile.mkdtemp(), "config.json")
        with open(bad, "w") as f:
            f.write("{not json")
        out = io.BytesIO()
        saved = sys.stdout
        try:
            with mock.patch.dict(os.environ, {"PLUME_CONFIG": bad, "HOME": tempfile.mkdtemp()}), \
                    mock.patch.object(sys, "stdin", SimpleNamespace(buffer=io.BytesIO(frame({"type": "send", "payload": GOOD})))), \
                    mock.patch.object(sys, "stdout", SimpleNamespace(buffer=out)):
                cli.main(["chrome-extension://abc/"])
        finally:
            sys.stdout = saved
        (reply,) = replies(out.getvalue())
        self.assertFalse(reply["ok"])
        self.assertIn("could not start", reply["error"])


class CliDispatchTests(unittest.TestCase):
    def test_chrome_origin_argument_selects_native_mode(self):
        from plume import cli
        with mock.patch.object(cli, "cmd_native") as native, mock.patch.object(cli, "load_config"):
            cli.main(["chrome-extension://abc/"])
        native.assert_called_once()


class CheckCommandTests(unittest.TestCase):
    class Connection:
        def __init__(self, cert):
            self.sock = type("Sock", (), {"getpeercert": lambda _self: cert})()

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def run_check(self, connect):
        import contextlib
        from plume import cli
        from plume.config import Config

        out = io.StringIO()
        with mock.patch.object(cli, "connect", connect), contextlib.redirect_stdout(out):
            cli.cmd_check(Config(smtp_host="relay.example", smtp_port=587), None)
        return out.getvalue()

    def test_reports_the_version_the_certificate_store_and_the_verified_certificate(self):
        cert = {"subject": ((("commonName", "relay.example"),),), "issuer": ((("organizationName", "Some CA"),),), "notAfter": "Jan  1 00:00:00 2030 GMT"}
        text = self.run_check(lambda host, port, ctx: self.Connection(cert))
        self.assertIn("plume ", text)
        self.assertIn("trusted certificates loaded:", text)
        self.assertIn("relay.example:587: TLS verified. Certificate for relay.example, issued by Some CA", text)

    def test_a_failed_handshake_ends_with_the_reason(self):
        import ssl

        def refuse(host, port, ctx):
            raise ssl.SSLCertVerificationError("unable to get local issuer certificate")
        with self.assertRaises(SystemExit) as raised:
            self.run_check(refuse)
        self.assertIn("cannot connect to relay.example:587", str(raised.exception))
        self.assertIn("unable to get local issuer certificate", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
