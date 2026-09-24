import copy
import logging
from dataclasses import dataclass
from email.utils import getaddresses
from typing import Optional

from .archive import NullArchive

log = logging.getLogger("plume")


@dataclass
class SendResult:
    message_id: str
    archived: bool = False
    archive_id: Optional[str] = None
    archive_error: Optional[str] = None
    relay_response: Optional[str] = None
    relay_seconds: Optional[float] = None


def with_bcc(msg, recipients):
    """Return a copy of msg with a Bcc header for the recipients that are not visible in To or Cc.

    The copy is for the sender's own record.
    """
    visible = {a.lower() for _, a in getaddresses(msg.get_all("To", []) + msg.get_all("Cc", []))}
    hidden = [r for r in recipients if r.lower() not in visible]
    out = copy.deepcopy(msg)
    if hidden:
        out["Bcc"] = ", ".join(hidden)
    return out


class SendService:
    """Send through the mailer, then try to archive a copy.

    If the mailer fails, the exception propagates because nothing was sent. If archiving fails,
    the mail is already out, so the failure is reported in the result instead.
    """

    def __init__(self, mailer, archive=None):
        self.mailer = mailer
        self.archive = archive or NullArchive()

    def send(self, msg, recipients, thread_id=None) -> SendResult:
        receipt = self.mailer.send(msg, recipients)
        result = SendResult(message_id=msg["Message-ID"])
        if receipt:
            result.relay_response, result.relay_seconds = receipt.response, receipt.seconds
        if isinstance(self.archive, NullArchive):
            return result
        try:
            result.archive_id = self.archive.archive(with_bcc(msg, recipients), thread_id)
            result.archived = True
        except Exception as e:  # Deliberately broad. The mail is already out, so nothing here may turn into a failure.
            log.warning("sent but not archived: %s", e)
            result.archive_error = str(e)
        return result
