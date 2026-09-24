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


if __name__ == "__main__":
    unittest.main()
