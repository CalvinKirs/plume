import json
import os
import tempfile
import unittest

from plume.browsers import BROWSERS, TARGETS, UnsupportedSystem
from plume.config import EXTENSION_ORIGIN, FIREFOX_EXTENSION_ID, HOST_NAME
from plume.install import install_host

from sources import fake_source

PATCH = os.path.join(os.path.dirname(__file__), "..", "..", "extension", "targets", "firefox", "manifest.patch.json")
BASE = {"name": HOST_NAME, "description": "d", "path": "/p/plume", "type": "stdio"}


def home_with(*dirs):
    home = tempfile.mkdtemp()
    for d in dirs:
        os.makedirs(os.path.join(home, d))
    return home


def read(path):
    with open(path) as f:
        return json.load(f)


class RegistryTests(unittest.TestCase):
    def test_the_supported_browsers(self):
        self.assertEqual(BROWSERS, ["brave", "chrome", "chromium", "edge", "firefox"])

    def test_chromium_family_trusts_the_extension_by_origin_and_never_by_id(self):
        for name in ("chrome", "chromium", "brave", "edge"):
            manifest = TARGETS[name].host_manifest(BASE)
            self.assertEqual(manifest["allowed_origins"], [EXTENSION_ORIGIN + "/"], name)
            self.assertNotIn("allowed_extensions", manifest, name)

    def test_firefox_trusts_the_addon_by_id_and_never_by_origin(self):
        manifest = TARGETS["firefox"].host_manifest(BASE)
        self.assertEqual(manifest["allowed_extensions"], [FIREFOX_EXTENSION_ID])
        self.assertNotIn("allowed_origins", manifest)

    def test_the_registry_only_adds_the_trust_field_to_the_common_part(self):
        for name, browser in TARGETS.items():
            manifest = browser.host_manifest(BASE)
            self.assertEqual({k: manifest[k] for k in BASE}, BASE, name)
            self.assertEqual(len(manifest) - len(BASE), 1, name)

    def test_the_firefox_id_here_is_the_one_in_the_extension(self):
        with open(PATCH) as f:
            self.assertEqual(json.load(f)["browser_specific_settings"]["gecko"]["id"], FIREFOX_EXTENSION_ID)

    def test_manifest_directories(self):
        firefox = TARGETS["firefox"]
        self.assertEqual(firefox.manifest_dir("/h", "Linux"), "/h/.mozilla/native-messaging-hosts")
        self.assertEqual(firefox.manifest_dir("/h", "Darwin"), "/h/Library/Application Support/Mozilla/NativeMessagingHosts")
        self.assertEqual(TARGETS["chrome"].manifest_dir("/h", "Linux"), "/h/.config/google-chrome/NativeMessagingHosts")
        self.assertEqual(TARGETS["chrome"].manifest_dir("/h", "Darwin"), "/h/Library/Application Support/Google/Chrome/NativeMessagingHosts")

    def test_an_unsupported_system_is_reported_by_every_browser(self):
        for name, browser in TARGETS.items():
            with self.assertRaises(UnsupportedSystem, msg=name):
                browser.manifest_dir("/h", "Windows")


class InstallWithFirefoxTests(unittest.TestCase):
    def install(self, home, system, **kw):
        return install_host(home=home, python="/usr/bin/python3", server_dir=fake_source(), system=system, **kw)

    def test_a_firefox_profile_alone_is_enough_to_be_detected(self):
        home = home_with(".mozilla/firefox")
        (path,) = self.install(home, "Linux")
        self.assertEqual(path, os.path.join(home, ".mozilla", "native-messaging-hosts", "org.plume.host.json"))
        manifest = read(path)
        self.assertEqual(manifest["allowed_extensions"], [FIREFOX_EXTENSION_ID])
        self.assertTrue(os.access(manifest["path"], os.X_OK))

    def test_on_macos_the_manifest_goes_under_the_mozilla_directory(self):
        home = home_with("Library/Application Support/Firefox")
        (path,) = self.install(home, "Darwin")
        self.assertIn("Library/Application Support/Mozilla/NativeMessagingHosts/org.plume.host.json", path)

    def test_each_browser_gets_a_manifest_in_its_own_format(self):
        home = home_with(".config/google-chrome", ".mozilla/firefox")
        paths = {("firefox" if ".mozilla" in p else "chrome"): read(p) for p in self.install(home, "Linux")}
        self.assertEqual(set(paths), {"chrome", "firefox"})
        self.assertIn("allowed_origins", paths["chrome"])
        self.assertNotIn("allowed_extensions", paths["chrome"])
        self.assertIn("allowed_extensions", paths["firefox"])
        self.assertNotIn("allowed_origins", paths["firefox"])
        self.assertEqual(paths["chrome"]["path"], paths["firefox"]["path"], "one program serves both")

    def test_firefox_is_registered_only_when_asked_for_or_found(self):
        home = home_with(".config/google-chrome")
        paths = self.install(home, "Linux")
        self.assertEqual(len(paths), 1)
        self.assertFalse(os.path.exists(os.path.join(home, ".mozilla")), "nothing is created for a browser that is not there")
        (forced,) = self.install(home, "Linux", browsers=["firefox"])
        self.assertIn(".mozilla/native-messaging-hosts", forced)


if __name__ == "__main__":
    unittest.main()
