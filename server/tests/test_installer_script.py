"""The one-line installer must refuse odd input before it downloads anything."""
import os
import shutil
import subprocess
import unittest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "packaging", "install.sh")


def run_installer(**env):
    full = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": "/nonexistent", "PLUME_FROM_SOURCE": "1"}
    full.update(env)
    return subprocess.run(["sh", SCRIPT], env=full, capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)


class InstallerValidationTests(unittest.TestCase):
    def test_a_repository_that_is_not_owner_slash_name_is_refused(self):
        for bad in ("a b", "../x", "x/..", "./x", "x/.", "owner", "owner/name/extra", "owner/na;me", "$(id)/x", "owner/name\nx", "/owner/name", "owner/"):
            result = run_installer(PLUME_REPO=bad, PLUME_VERSION="v1.0.0")
            self.assertNotEqual(result.returncode, 0, repr(bad))
            self.assertIn("PLUME_REPO", result.stderr, repr(bad))

    def test_a_release_tag_that_could_change_the_download_path_is_refused(self):
        for bad in ("v1/../../x", "a b", "v1;rm -rf x", "../../etc", "v1..2", "v1/x", "$(id)", "v1\nx", ".", "-rf", ".hidden"):
            result = run_installer(PLUME_VERSION=bad)
            self.assertNotEqual(result.returncode, 0, repr(bad))
            self.assertIn("not a valid release tag", result.stderr, repr(bad))

    @unittest.skipUnless(shutil.which("curl"), "needs curl")
    def test_only_https_is_accepted_for_a_download(self):
        for url in ("http://example.invalid/x.tar.gz", "ftp://example.invalid/x.tar.gz", "gopher://example.invalid/x"):
            result = run_installer(PLUME_VERSION="v1.0.0", PLUME_SOURCE_URL=url)
            self.assertNotEqual(result.returncode, 0, url)
            self.assertRegex(result.stderr.lower(), r"protocol|disabled|not supported|denied", url)

    def test_the_shared_fetch_allows_https_only_and_file_stays_inside_the_test_override(self):
        with open(SCRIPT) as f:
            text = f.read()
        self.assertIn("curl --proto '=https' --proto-redir '=https'", text)
        self.assertNotIn("=https,file", text)
        self.assertIn("file://*) curl --proto '=file'", text)
        self.assertIn('""|0|false|no)', text, "PLUME_FROM_SOURCE=0 must not force the source route")

    def test_a_source_url_needs_no_release_and_the_tag_lookup_is_skipped(self):
        result = run_installer(PLUME_SOURCE_URL="file:///nonexistent-plume-src.tar.gz",
                               PLUME_REPO="nobody/no-such-repo-abcxyz")
        self.assertNotEqual(result.returncode, 0)  # the file does not exist, so the download fails
        self.assertIn("Downloading the source from file:///nonexistent-plume-src.tar.gz", result.stdout)
        self.assertNotIn("Could not find a release", result.stderr)


if __name__ == "__main__":
    unittest.main()
