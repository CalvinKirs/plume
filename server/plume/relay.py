import smtplib
import ssl


class SmtpRelayMailer:
    """Submit through an authenticated SMTP relay. Port 465 uses implicit TLS, others STARTTLS."""

    def __init__(self, host, port, user, password):
        self.host, self.port, self.user, self.password = host, port, user, password

    def send(self, msg, recipients):
        ctx = ssl.create_default_context()
        if self.port == 465:
            smtp = smtplib.SMTP_SSL(self.host, self.port, context=ctx, timeout=30)
        else:
            smtp = smtplib.SMTP(self.host, self.port, timeout=30)
        with smtp:
            if self.port != 465:
                smtp.starttls(context=ctx)
            smtp.login(self.user, self.password)
            smtp.send_message(msg, from_addr=msg["From"], to_addrs=recipients)
