import json
import os
import tempfile
import unittest

from plume.config import EXTENSION_ORIGIN
from plume.install import HOST_NAME, install_host


class InstallTests(unittest.TestCase):
    def test_registers_manifest_and_launcher(self):
        home = tempfile.mkdtemp()
        os.makedirs(os.path.join(home, ".config", "google-chrome"))
        paths = install_host(home=home, python="/usr/bin/python3", server_dir="/opt/my plume/server", system="Linux")
        self.assertEqual(len(paths), 1)
        with open(paths[0]) as f:
            manifest = json.load(f)
        self.assertEqual(manifest["name"], HOST_NAME)
        self.assertEqual(manifest["allowed_origins"], [EXTENSION_ORIGIN + "/"])
        launcher = manifest["path"]
        self.assertTrue(os.access(launcher, os.X_OK))
        with open(launcher) as f:
            text = f.read()
        self.assertIn("PYTHONPATH='/opt/my plume/server'", text)
        self.assertIn("-m plume native", text)

    def test_no_browser_and_unsupported_os(self):
        with self.assertRaises(SystemExit):
            install_host(home=tempfile.mkdtemp(), system="Linux")
        with self.assertRaises(SystemExit):
            install_host(home=tempfile.mkdtemp(), system="Windows")


class PackagedInstallTests(unittest.TestCase):
    def test_binary_is_copied_and_registered_directly(self):
        home = tempfile.mkdtemp()
        os.makedirs(os.path.join(home, ".config", "google-chrome"))
        fake = os.path.join(tempfile.mkdtemp(), "plume-dl")
        with open(fake, "w") as f:
            f.write("binary")
        (manifest_path,) = install_host(home=home, binary=fake, system="Linux")
        with open(manifest_path) as f:
            path = json.load(f)["path"]
        self.assertEqual(path, os.path.join(home, ".local", "share", "plume", "plume"))
        self.assertTrue(os.access(path, os.X_OK))
        with open(path) as f:
            self.assertEqual(f.read(), "binary")



class MacInstallTests(unittest.TestCase):
    def mac_home(self, *dirs):
        home = tempfile.mkdtemp()
        for d in dirs:
            os.makedirs(os.path.join(home, "Library", "Application Support", d))
        return home

    def test_registers_in_library_application_support_for_every_detected_browser(self):
        home = self.mac_home("Google/Chrome", "BraveSoftware/Brave-Browser")
        paths = install_host(home=home, python="/usr/bin/python3", server_dir="/s", system="Darwin")
        self.assertEqual(sorted(os.path.relpath(p, home) for p in paths), [
            "Library/Application Support/BraveSoftware/Brave-Browser/NativeMessagingHosts/org.plume.host.json",
            "Library/Application Support/Google/Chrome/NativeMessagingHosts/org.plume.host.json",
        ])

    def test_installed_binary_loses_its_quarantine_flag_only_on_macos(self):
        from unittest import mock
        fake = os.path.join(tempfile.mkdtemp(), "dl")
        with open(fake, "w") as f:
            f.write("bin")
        with mock.patch("plume.install.subprocess.run") as run:
            install_host(home=self.mac_home("Google/Chrome"), binary=fake, system="Darwin")
            args = run.call_args[0][0]
            self.assertEqual(args[:3], ["xattr", "-dr", "com.apple.quarantine"])
            self.assertTrue(args[3].endswith("/.local/share/plume/plume"))
            run.reset_mock()
            linux_home = tempfile.mkdtemp()
            os.makedirs(os.path.join(linux_home, ".config", "google-chrome"))
            install_host(home=linux_home, binary=fake, system="Linux")
            run.assert_not_called()

    def test_explicit_browser_is_registered_even_if_not_detected(self):
        (path,) = install_host(home=tempfile.mkdtemp(), python="p", server_dir="/s", system="Darwin", browsers=["edge"])
        self.assertIn("Microsoft Edge/NativeMessagingHosts", path)


class OneDirInstallTests(unittest.TestCase):
    def build_dir(self):
        d = os.path.join(tempfile.mkdtemp(), "plume")
        os.makedirs(os.path.join(d, "_internal"))
        with open(os.path.join(d, "plume"), "w") as f:
            f.write("exe")
        with open(os.path.join(d, "_internal", "libpython3.10.dylib"), "w") as f:
            f.write("lib")
        os.symlink("libpython3.10.dylib", os.path.join(d, "_internal", "libpython.dylib"))
        return d

    def test_whole_folder_is_installed_and_registered(self):
        home = tempfile.mkdtemp()
        os.makedirs(os.path.join(home, ".config", "google-chrome"))
        src = self.build_dir()
        old = os.path.join(home, ".local", "share", "plume", "plume")
        os.makedirs(os.path.dirname(old))
        with open(old, "w") as f:
            f.write("old single-file install")
        (manifest_path,) = install_host(home=home, binary=os.path.join(src, "plume"), system="Linux")
        with open(manifest_path) as f:
            path = json.load(f)["path"]
        app = os.path.join(home, ".local", "share", "plume", "app")
        self.assertEqual(path, os.path.join(app, "plume"))
        self.assertTrue(os.access(path, os.X_OK))
        self.assertTrue(os.path.isfile(os.path.join(app, "_internal", "libpython3.10.dylib")))
        self.assertTrue(os.path.islink(os.path.join(app, "_internal", "libpython.dylib")))  # symlinks kept
        self.assertFalse(os.path.exists(old))  # replaced

    def test_reinstall_replaces_the_folder_and_macos_strips_the_whole_tree(self):
        from unittest import mock
        home = tempfile.mkdtemp()
        os.makedirs(os.path.join(home, "Library", "Application Support", "Google", "Chrome"))
        src = self.build_dir()
        with mock.patch("plume.install.subprocess.run") as run:
            install_host(home=home, binary=os.path.join(src, "plume"), system="Darwin")
            install_host(home=home, binary=os.path.join(src, "plume"), system="Darwin")
        app = os.path.join(home, ".local", "share", "plume", "app")
        self.assertEqual(run.call_args[0][0], ["xattr", "-dr", "com.apple.quarantine", app])


if __name__ == "__main__":
    unittest.main()
