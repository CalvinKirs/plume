import json
import os
import re
import unittest

from plume import __version__

MANIFEST = os.path.join(os.path.dirname(__file__), "..", "..", "extension", "manifest.json")


class VersionTests(unittest.TestCase):
    def test_program_and_extension_carry_the_same_version(self):
        with open(MANIFEST) as f:
            manifest = json.load(f)
        self.assertEqual(manifest["version_name"], __version__)
        # Chrome's "version" must be dotted numbers, so it is the release part of the full version.
        self.assertEqual(manifest["version"], re.match(r"\d+\.\d+\.\d+", __version__).group())

    def test_version_flag_prints_it(self):
        import io
        from contextlib import redirect_stdout
        from plume import cli

        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as raised:
            cli.main(["--version"])
        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(out.getvalue().strip(), f"plume {__version__}")


if __name__ == "__main__":
    unittest.main()
