from email.message import EmailMessage
from email.utils import formatdate, make_msgid, getaddresses


class BadMessage(ValueError):
    pass


def _addrs(value):
    if not value:
        return []
    if isinstance(value, str):
        value = [value]
    return [a for _, a in getaddresses(value) if a]


def build_message(payload):
    """Build an EmailMessage from the JSON payload. Returns the message and the envelope recipients."""
    sender = _addrs(payload.get("from"))
    to = _addrs(payload.get("to"))
    cc = _addrs(payload.get("cc"))
    bcc = _addrs(payload.get("bcc"))
    if len(sender) != 1:
        raise BadMessage("exactly one from address is required")
    if not (to or cc or bcc):
        raise BadMessage("at least one recipient is required")
    text = payload.get("text")
    html = payload.get("html")
    if not text and not html:
        raise BadMessage("text or html body is required")

    msg = EmailMessage()
    try:
        msg["From"] = sender[0]
        if to:
            msg["To"] = ", ".join(to)
        if cc:
            msg["Cc"] = ", ".join(cc)
        msg["Subject"] = payload.get("subject", "")
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain=sender[0].rpartition("@")[2] or None)
        if payload.get("inReplyTo"):
            msg["In-Reply-To"] = payload["inReplyTo"]
        if payload.get("references"):
            msg["References"] = payload["references"]
    except ValueError as e:  # A newline in a header value (header injection) and similar problems end up here.
        raise BadMessage(str(e)) from e

    if text:
        msg.set_content(text)
        if html:
            msg.add_alternative(html, subtype="html")
    else:
        msg.set_content(html, subtype="html")
    return msg, to + cc + bcc
