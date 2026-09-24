import smtplib
import time

from .ports import RelayReceipt
from .tls import default_context


class _RecordsDataReply:
    """Remembers the relay's reply to DATA, which is where it says `queued as <id>`."""

    def data(self, msg):
        code, response = super().data(msg)
        self.last_data_reply = (code, response)
        return code, response


class _SMTP(_RecordsDataReply, smtplib.SMTP):
    pass


class _SMTP_SSL(_RecordsDataReply, smtplib.SMTP_SSL):
    pass


def connect(host, port, ctx=None):
    """Open an encrypted connection to the relay. Port 465 uses implicit TLS, other ports use STARTTLS."""
    ctx = ctx or default_context()
    if port == 465:
        return _SMTP_SSL(host, port, context=ctx, timeout=30)
    smtp = _SMTP(host, port, timeout=30)
    try:
        smtp.starttls(context=ctx)
    except Exception:
        smtp.close()
        raise
    return smtp


class SmtpRelayMailer:
    """Submit through an authenticated SMTP relay. Port 465 uses implicit TLS, other ports use STARTTLS."""

    def __init__(self, host, port, user, password):
        self.host, self.port, self.user, self.password = host, port, user, password

    def send(self, msg, recipients):
        started = time.monotonic()
        with connect(self.host, self.port) as smtp:
            smtp.login(self.user, self.password)
            # The envelope sender is the bare address, even when the From header carries a display name.
            smtp.send_message(msg, from_addr=msg["From"].addresses[0].addr_spec, to_addrs=recipients)
            code, response = getattr(smtp, "last_data_reply", (None, b""))
        text = response.decode(errors="replace").strip() if isinstance(response, bytes) else str(response)
        return RelayReceipt(response=f"{code} {text}".strip(), seconds=round(time.monotonic() - started, 2))
