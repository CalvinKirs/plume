import os
import stat
import tempfile
import unittest

from plume.config import load_config, save_config


class ConfigTests(unittest.TestCase):
    def test_defaults_and_overrides(self):
        cfg = load_config({"PLUME_USER": "u", "PLUME_SMTP_PORT": "465"})
        self.assertEqual((cfg.smtp_host, cfg.smtp_port, cfg.user), ("mail-relay.apache.org", 465, "u"))
        self.assertIn("chrome-extension://mabkbpnhmakajgmgpcehigllechcaehb", cfg.allowed_origins)


class ConfigFileTests(unittest.TestCase):
    def test_file_then_env_override_and_mode(self):
        path = os.path.join(tempfile.mkdtemp(), "c", "config.json")
        save_config({"user": "file-user", "password": "pw", "smtp_port": 465}, path)
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        cfg = load_config({"PLUME_USER": "env-user"}, path=path)
        self.assertEqual((cfg.user, cfg.password, cfg.smtp_port), ("env-user", "pw", 465))

    def test_unknown_keys_ignored_and_missing_file_ok(self):
        self.assertEqual(load_config({}, path="/nonexistent.json").user, "")



class PrivateFilesTests(unittest.TestCase):
    def test_config_directory_and_log_are_private_even_if_the_directory_already_existed(self):
        from unittest import mock
        home = tempfile.mkdtemp()
        os.makedirs(os.path.join(home, ".config", "plume"), mode=0o775)
        os.chmod(os.path.join(home, ".config", "plume"), 0o775)
        with mock.patch.dict(os.environ, {"HOME": home}):
            from plume import cli
            save_config({"user": "u", "password": "p"})
            cli._host_log()
        mode = lambda p: stat.S_IMODE(os.stat(os.path.join(home, ".config", "plume", *p)).st_mode)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(home, ".config", "plume")).st_mode), 0o700)
        self.assertEqual((mode(["config.json"]), mode(["host.log"])), (0o600, 0o600))

    def test_other_directories_keep_their_permissions(self):
        from plume.config import ensure_private_dir
        shared = tempfile.mkdtemp()
        os.chmod(shared, 0o755)
        ensure_private_dir(shared)
        self.assertEqual(stat.S_IMODE(os.stat(shared).st_mode), 0o755)


if __name__ == "__main__":
    unittest.main()
