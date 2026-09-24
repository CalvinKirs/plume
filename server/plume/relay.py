import smtplib
import ssl
import time

from .ports import RelayReceipt


class _RecordsDataReply:
    """Keeps the relay's answer to DATA: that is where it says `queued as <id>`."""

    def data(self, msg):
        code, response = super().data(msg)
        self.last_data_reply = (code, response)
        return code, response


class _SMTP(_RecordsDataReply, smtplib.SMTP):
    pass


class _SMTP_SSL(_RecordsDataReply, smtplib.SMTP_SSL):
    pass


class SmtpRelayMailer:
    """Submit through an authenticated SMTP relay. Port 465 uses implicit TLS, others STARTTLS."""

    def __init__(self, host, port, user, password):
        self.host, self.port, self.user, self.password = host, port, user, password

    def send(self, msg, recipients):
        started = time.monotonic()
        ctx = ssl.create_default_context()
        if self.port == 465:
            smtp = _SMTP_SSL(self.host, self.port, context=ctx, timeout=30)
        else:
            smtp = _SMTP(self.host, self.port, timeout=30)
        with smtp:
            if self.port != 465:
                smtp.starttls(context=ctx)
            smtp.login(self.user, self.password)
            smtp.send_message(msg, from_addr=msg["From"], to_addrs=recipients)
            code, response = getattr(smtp, "last_data_reply", (None, b""))
        text = response.decode(errors="replace").strip() if isinstance(response, bytes) else str(response)
        return RelayReceipt(response=f"{code} {text}".strip(), seconds=round(time.monotonic() - started, 2))
