"""The from-source route, end to end, with real processes.

This is what someone does on a machine that has no prebuilt program (an Intel Mac, an ARM Linux box, any
other distribution): clone, run install-host with their own Python, delete the clone, and let a browser
start the program. It runs on every platform and Python version the test suite runs on.
"""
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

from sources import REAL_SOURCE

GOOD = {"from": "a@apache.org", "to": ["b@x.org"], "subject": "s", "text": "t"}


def run_cli(home, cwd, *args):
    env = {"HOME": home, "PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    return subprocess.run([sys.executable, "-m", "plume", *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=60)


def ask_host(launcher, home, argv, payload=GOOD):
    """Start the registered launcher the way a browser does, send one message, read one reply."""
    data = json.dumps({"type": "send", "payload": payload}).encode()
    p = subprocess.run([launcher, *argv], input=struct.pack("=I", len(data)) + data, capture_output=True,
                       env={"HOME": home, "PATH": "/usr/bin:/bin"}, timeout=60)
    (size,) = struct.unpack("=I", p.stdout[:4])
    assert len(p.stdout) == 4 + size, "stdout must carry the framed reply and nothing else"
    return json.loads(p.stdout[4:4 + size])


class SourceInstallTests(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="plume home ")  # a space, as in "Application Support"
        os.makedirs(os.path.join(self.home, ".config", "google-chrome"))
        os.makedirs(os.path.join(self.home, ".mozilla", "firefox"))
        os.makedirs(os.path.join(self.home, ".config", "plume"))
        with open(os.path.join(self.home, ".config", "plume", "config.json"), "w") as f:
            json.dump({"user": "u", "password": "p", "smtp_host": "127.0.0.1", "smtp_port": 1}, f)
        # a private "clone" so that it can be deleted
        self.clone = tempfile.mkdtemp(prefix="plume clone ")
        shutil.copytree(os.path.join(REAL_SOURCE, "plume"), os.path.join(self.clone, "plume"),
                        ignore=shutil.ignore_patterns("__pycache__"))

    def test_install_delete_the_clone_and_let_each_browser_start_it(self):
        result = run_cli(self.home, self.clone, "install-host")
        self.assertEqual(result.returncode, 0, result.stderr)
        shutil.rmtree(self.clone)  # the installed program must not need the clone

        chrome = os.path.join(self.home, ".config", "google-chrome", "NativeMessagingHosts", "org.plume.host.json")
        firefox = os.path.join(self.home, ".mozilla", "native-messaging-hosts", "org.plume.host.json")
        for manifest_path, argv_for in ((chrome, lambda m: ["chrome-extension://abc/"]),
                                        (firefox, lambda m: [manifest_path, m["allowed_extensions"][0]])):
            with open(manifest_path) as f:
                manifest = json.load(f)
            reply = ask_host(manifest["path"], self.home, argv_for(manifest))
            # Nothing listens on the relay port, so the send fails; what matters is that the host ran
            # from the installed copy, understood the launch, decoded the message and answered.
            self.assertFalse(reply["ok"])
            self.assertIn("relay failure", reply["error"], manifest_path)

    def test_running_install_again_replaces_the_installed_copy(self):
        run_cli(self.home, self.clone, "install-host", "--browser", "chrome")
        installed = os.path.join(self.home, ".local", "share", "plume", "src", "plume")
        with open(os.path.join(installed, "stale.py"), "w") as f:
            f.write("# left over from an older version")
        run_cli(self.home, self.clone, "install-host", "--browser", "chrome")
        self.assertFalse(os.path.exists(os.path.join(installed, "stale.py")))
        self.assertTrue(os.path.isfile(os.path.join(installed, "__init__.py")))

    def test_reregistering_through_a_symlinked_home_does_not_destroy_the_install(self):
        # macOS spells /var as /private/var, and a mounted /home is a symlink on many Linux systems, so
        # the installed copy and the install target can be the same directory under two spellings.
        run_cli(self.home, self.clone, "install-host", "--browser", "chrome")
        src = os.path.join(self.home, ".local", "share", "plume", "src")
        alias = self.home.rstrip("/") + "-alias"
        os.symlink(self.home, alias)
        result = subprocess.run([sys.executable, "-m", "plume", "install-host", "--browser", "chrome"],
                                cwd=src, env={"HOME": alias, "PATH": os.environ.get("PATH", "/usr/bin:/bin")},
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(os.path.isfile(os.path.join(src, "plume", "__init__.py")), "the package must survive")

    def test_the_installed_copy_can_register_again_without_the_clone(self):
        run_cli(self.home, self.clone, "install-host", "--browser", "chrome")
        shutil.rmtree(self.clone)
        src = os.path.join(self.home, ".local", "share", "plume", "src")
        again = run_cli(self.home, src, "install-host", "--browser", "chrome")
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertTrue(os.path.isfile(os.path.join(src, "plume", "__init__.py")))

    def test_ending_the_input_during_setup_is_a_cancellation_not_a_traceback(self):
        result = subprocess.run([sys.executable, "-m", "plume", "configure"], cwd=self.clone, stdin=subprocess.DEVNULL,
                                env={"HOME": self.home, "PATH": os.environ.get("PATH", "/usr/bin:/bin")},
                                capture_output=True, text=True, timeout=60)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("Cancelled", result.stderr)

    def test_the_version_flag_works_from_the_clone(self):
        out = run_cli(self.home, self.clone, "--version")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertTrue(out.stdout.startswith("plume "))


if __name__ == "__main__":
    unittest.main()
