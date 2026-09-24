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


class DisplayNameTests(unittest.TestCase):
    def sender(self, **kw):
        msg, _ = build_message(payload(**kw))
        return msg

    def test_a_name_shows_up_in_the_from_header_next_to_the_address(self):
        msg = self.sender(fromName="Calvin Kirs")
        (addr,) = msg["From"].addresses
        self.assertEqual((addr.display_name, addr.addr_spec), ("Calvin Kirs", "alice@apache.org"))
        self.assertIn(b"From: Calvin Kirs <alice@apache.org>", msg.as_bytes())

    def test_without_a_name_the_header_is_the_bare_address_as_before(self):
        for kw in ({}, {"fromName": ""}, {"fromName": "   "}, {"fromName": None}):
            self.assertIn(b"From: alice@apache.org", self.sender(**kw).as_bytes(), kw)

    def test_commas_and_quotes_in_a_name_are_quoted_and_survive_a_round_trip(self):
        import email
        from email import policy
        raw = self.sender(fromName='Kirs, Calvin "CK"').as_bytes()
        (addr,) = email.message_from_bytes(raw, policy=policy.default)["From"].addresses
        self.assertEqual((addr.display_name, addr.addr_spec), ('Kirs, Calvin "CK"', "alice@apache.org"))

    def test_a_non_ascii_name_is_encoded_for_the_wire_and_decoded_back(self):
        import email
        from email import policy
        name = "Jos\u00e9 N\u00fa\u00f1ez"
        raw = self.sender(fromName=name).as_bytes()
        header = raw.split(b"\r\n\r\n")[0].split(b"\n\n")[0]
        self.assertTrue(header.isascii(), "the header block must be plain ASCII")
        (addr,) = email.message_from_bytes(raw, policy=policy.default)["From"].addresses
        self.assertEqual(addr.display_name, name)

    def test_a_newline_or_a_non_text_name_is_refused(self):
        for bad in ("Calvin\r\nBcc: evil@x.org", "Calvin\nKirs", 42, ["a"]):
            with self.assertRaises(BadMessage, msg=repr(bad)):
                build_message(payload(fromName=bad))


if __name__ == "__main__":
    unittest.main()
