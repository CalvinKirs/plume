import unittest

from plume.message import BadMessage, build_message


def payload(**kw):
    base = {"from": "Alice <alice@apache.org>", "to": ["dev@example.org"], "subject": "hi", "text": "body"}
    base.update(kw)
    return base


class MessageTests(unittest.TestCase):
    def test_headers_and_recipients(self):
        msg, rcpt = build_message(payload(cc=["bob@x.org"], bcc=["secret@x.org"], inReplyTo="<a@b>", references="<a@b>"))
        self.assertEqual(rcpt, ["dev@example.org", "bob@x.org", "secret@x.org"])
        self.assertEqual(msg["Cc"], "bob@x.org")
        self.assertIsNone(msg["Bcc"])
        self.assertNotIn("secret@x.org", msg.as_string())
        self.assertEqual(msg["In-Reply-To"], "<a@b>")
        self.assertTrue(msg["Message-ID"].endswith("@apache.org>"))

    def test_html_alternative(self):
        msg, _ = build_message(payload(html="<b>x</b>"))
        self.assertEqual(msg.get_content_type(), "multipart/alternative")

    def test_rejects_bad_input(self):
        for bad in (payload(**{"from": ""}), payload(to=[]), payload(text="", html=""),
                    payload(subject="a\r\nBcc: evil@x.org")):
            with self.assertRaises(BadMessage):
                build_message(bad)


if __name__ == "__main__":
    unittest.main()
