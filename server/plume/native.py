"""Chrome native messaging: length-prefixed JSON on stdin and stdout, one reply per request."""
import json
import logging
import struct

from .api import send_payload

log = logging.getLogger("plume.native")

# Well above any plain-text mail. The length comes from the caller, and Python would try to allocate it.
MAX_MESSAGE = 32 * 1024 * 1024


class MessageTooLarge(ValueError):
    pass


def read_message(stream):
    """Return the next message, or None at end of input. Raises ValueError if the JSON cannot be decoded."""
    header = stream.read(4)
    if len(header) < 4:
        return None
    (size,) = struct.unpack("=I", header)  # Chrome uses the machine's native byte order.
    if size > MAX_MESSAGE:
        raise MessageTooLarge(f"message of {size} bytes exceeds the limit of {MAX_MESSAGE}")
    data = stream.read(size)
    if len(data) < size:
        return None
    return json.loads(data)


def write_message(stream, obj):
    data = json.dumps(obj).encode()
    stream.write(struct.pack("=I", len(data)))
    stream.write(data)
    stream.flush()


def serve(service, stdin, stdout):
    while True:
        try:
            msg = read_message(stdin)
        except MessageTooLarge as e:
            # The stream cannot be resynchronised after an oversized header, so answer once and stop.
            write_message(stdout, {"ok": False, "error": str(e)})
            return
        except ValueError:
            write_message(stdout, {"ok": False, "error": "undecodable message"})
            continue
        if msg is None:
            return
        if not isinstance(msg, dict) or msg.get("type") != "send":
            write_message(stdout, {"ok": False, "error": "unknown request"})
            continue
        try:
            reply = send_payload(service, msg.get("payload"))[1]
        except Exception as e:  # Report anything unexpected to the extension instead of dying silently.
            log.exception("unexpected failure while sending")
            reply = {"ok": False, "error": f"internal error: {type(e).__name__}: {e}"}
        write_message(stdout, reply)
