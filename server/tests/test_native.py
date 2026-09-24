import io
import json
import struct
import unittest

from plume.config import load_config
from plume.native import read_message, serve, write_message
from plume.service import SendService
from plume.wiring import build_service


def frame(obj):
    data = json.dumps(obj).encode()
    return struct.pack("=I", len(data)) + data


def replies(raw):
    stream, out = io.BytesIO(raw), []
    while (m := read_message(stream)) is not None:
        out.append(m)
    return out


class Mailer:
    def __init__(self):
        self.sent = []

    def send(self, msg, rcpt):
        self.sent.append((msg, rcpt))


GOOD = {"from": "a@apache.org", "to": ["b@x.org"], "subject": "s", "text": "t"}


class NativeTests(unittest.TestCase):
    def run_host(self, raw, mailer=None):
        out = io.BytesIO()
        serve(SendService(mailer or Mailer()), io.BytesIO(raw), out)
        return replies(out.getvalue())

    def test_framing_roundtrip(self):
        buf = io.BytesIO()
        write_message(buf, {"a": "é"})
        buf.seek(0)
        self.assertEqual(read_message(buf), {"a": "é"})
        self.assertIsNone(read_message(buf))

    def test_send_and_multiple_messages(self):
        m = Mailer()
        out = self.run_host(frame({"type": "send", "payload": GOOD}) * 2, m)
        self.assertEqual([r["ok"] for r in out], [True, True])
        self.assertEqual(len(m.sent), 2)

    def test_errors_are_replies_not_crashes(self):
        junk = struct.pack("=I", 3) + b"{x}"
        out = self.run_host(junk + frame({"type": "nope"}) + frame({"type": "send", "payload": {"to": []}}))
        self.assertEqual([r["ok"] for r in out], [False, False, False])
        self.assertIn("undecodable", out[0]["error"])
        self.assertIn("unknown", out[1]["error"])

    def test_truncated_input_ends_quietly(self):
        self.assertEqual(self.run_host(struct.pack("=I", 50) + b"short"), [])

    def test_unconfigured_host_says_how_to_fix_it(self):
        out = io.BytesIO()
        serve(build_service(load_config({}, path="/nonexistent.json")), io.BytesIO(frame({"type": "send", "payload": GOOD})), out)
        self.assertIn("plume setup", replies(out.getvalue())[0]["error"])


if __name__ == "__main__":
    unittest.main()
