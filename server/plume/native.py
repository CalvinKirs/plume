"""Chrome native messaging: length-prefixed JSON on stdin and stdout, one reply per request."""
import json
import logging
import struct

from .api import send_payload

log = logging.getLogger("plume.native")


def read_message(stream):
    """Return the next message, or None at end of input. Raises ValueError if the JSON cannot be decoded."""
    header = stream.read(4)
    if len(header) < 4:
        return None
    (size,) = struct.unpack("=I", header)  # Chrome uses the machine's native byte order.
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
