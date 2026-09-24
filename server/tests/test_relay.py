import unittest
from email.message import EmailMessage
from unittest import mock

from plume import relay
from plume.relay import SmtpRelayMailer


def message():
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = "me@apache.org", "you@example.org", "s"
    m.set_content("hi")
    return m


class FakeSmtp:
    """Stands in for smtplib.SMTP: records the calls and answers DATA like a Postfix relay."""

    instances = []

    def __init__(self, host, port, **kwargs):
        self.calls = [("connect", host, port)]
        self.kwargs = kwargs
        FakeSmtp.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.calls.append(("starttls",))

    def login(self, user, password):
        self.calls.append(("login", user))

    def send_message(self, msg, from_addr, to_addrs):
        self.calls.append(("send", from_addr, tuple(to_addrs)))
        self.last_data_reply = (250, b"2.0.0 Ok: queued as 4ABC123")


class RelayTests(unittest.TestCase):
    def setUp(self):
        FakeSmtp.instances = []

    def test_starttls_on_587_and_the_queue_reply_is_returned(self):
        with mock.patch.object(relay, "_SMTP", FakeSmtp):
            receipt = SmtpRelayMailer("relay.example", 587, "u", "p").send(message(), ["you@example.org"])
        (smtp,) = FakeSmtp.instances
        self.assertEqual([c[0] for c in smtp.calls], ["connect", "starttls", "login", "send"])
        self.assertEqual(receipt.response, "250 2.0.0 Ok: queued as 4ABC123")
        self.assertGreaterEqual(receipt.seconds, 0)

    def test_implicit_tls_on_465_has_no_starttls(self):
        with mock.patch.object(relay, "_SMTP_SSL", FakeSmtp):
            SmtpRelayMailer("relay.example", 465, "u", "p").send(message(), ["you@example.org"])
        (smtp,) = FakeSmtp.instances
        self.assertNotIn("starttls", [c[0] for c in smtp.calls])

    def test_records_the_data_reply_of_a_real_smtp_subclass(self):
        class Base:
            def data(self, msg):
                return 250, b"2.0.0 Ok: queued as XYZ"

        class Recording(relay._RecordsDataReply, Base):
            pass

        smtp = Recording()
        self.assertEqual(smtp.data(b"x"), (250, b"2.0.0 Ok: queued as XYZ"))
        self.assertEqual(smtp.last_data_reply, (250, b"2.0.0 Ok: queued as XYZ"))


if __name__ == "__main__":
    unittest.main()
