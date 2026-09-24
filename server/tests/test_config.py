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


if __name__ == "__main__":
    unittest.main()
