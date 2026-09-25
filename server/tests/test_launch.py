import unittest
from unittest import mock

from plume import cli
from plume.launch import is_native_launch


class LaunchTests(unittest.TestCase):
    def test_chrome_passes_the_origin_of_the_extension(self):
        self.assertTrue(is_native_launch(["chrome-extension://abcdefgh/"]))

    def test_firefox_passes_the_manifest_path_and_the_addon_id(self):
        self.assertTrue(is_native_launch(["/home/u/.mozilla/native-messaging-hosts/org.plume.host.json", "plume@calvinkirs.github.io"]))
        self.assertTrue(is_native_launch(["/Users/u/Library/Application Support/Mozilla/NativeMessagingHosts/org.plume.host.json"]))

    def test_a_person_typing_a_command_is_not_a_launch_by_a_browser(self):
        for argv in ([], ["setup"], ["--version"], ["check"], ["/tmp/other.json"], ["org.plume.host"], ["chrome-extension"]):
            self.assertFalse(is_native_launch(argv), argv)

    def test_the_command_line_enters_native_mode_for_either_browser(self):
        for argv in (["chrome-extension://abc/"], ["/x/org.plume.host.json", "plume@calvinkirs.github.io"]):
            with mock.patch.object(cli, "cmd_native") as native, mock.patch.object(cli, "load_config"):
                cli.main(argv)
            native.assert_called_once()


if __name__ == "__main__":
    unittest.main()
