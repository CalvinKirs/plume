"""Transport-independent send operation shared by the HTTP and native-messaging entry points."""
import smtplib

from .errors import ConfigError
from .message import BadMessage, build_message


def send_payload(service, payload):
    """Run one send; return (http_status, body). Never raises for expected failures."""
    try:
        if not isinstance(payload, dict):
            raise BadMessage("payload must be an object")
        msg, recipients = build_message(payload)
    except BadMessage as e:
        return 400, {"ok": False, "error": str(e)}
    try:
        result = service.send(msg, recipients, thread_id=payload.get("threadId"))
    except ConfigError as e:
        return 503, {"ok": False, "error": str(e)}
    except smtplib.SMTPAuthenticationError:
        return 502, {"ok": False, "error": "relay rejected the login"}
    except (smtplib.SMTPException, OSError) as e:
        return 502, {"ok": False, "error": f"relay failure: {e}"}
    return 200, {
        "ok": True, "messageId": result.message_id, "archived": result.archived,
        "archiveId": result.archive_id, "archiveError": result.archive_error,
        "relayResponse": result.relay_response, "relaySeconds": result.relay_seconds,
    }
