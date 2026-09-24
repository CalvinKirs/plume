import unittest
from email.message import EmailMessage

from plume.service import SendService, with_bcc


def sample():
    m = EmailMessage()
    m["From"], m["To"], m["Cc"], m["Subject"], m["Message-ID"] = "a@apache.org", "d@x.org", "c@x.org", "s", "<1@apache.org>"
    m.set_content("hi")
    return m


class ServiceTests(unittest.TestCase):
    def test_with_bcc_only_adds_hidden_recipients(self):
        out = with_bcc(sample(), ["d@x.org", "c@x.org", "Hidden@x.org"])
        self.assertEqual(out["Bcc"], "Hidden@x.org")
        self.assertIsNone(sample()["Bcc"])

    def test_without_hidden_recipients_no_bcc(self):
        self.assertIsNone(with_bcc(sample(), ["d@x.org"])["Bcc"])

    def test_relay_receipt_is_carried_into_the_result(self):
        from plume.ports import RelayReceipt

        class M:
            def send(self, *a):
                return RelayReceipt(response="250 queued as 1", seconds=0.8)
        r = SendService(M()).send(sample(), ["d@x.org"])
        self.assertEqual((r.relay_response, r.relay_seconds), ("250 queued as 1", 0.8))

    def test_null_archive_skips(self):
        class M:
            def send(self, *a):
                pass
        r = SendService(M()).send(sample(), ["d@x.org"])
        self.assertEqual((r.archived, r.archive_error), (False, None))


if __name__ == "__main__":
    unittest.main()
