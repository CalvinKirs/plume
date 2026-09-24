"""Interfaces (ports) the service depends on. Adapters live in their own modules."""
from dataclasses import dataclass
from typing import Optional, Protocol, Tuple


@dataclass
class RelayReceipt:
    """What the relay said when it took the message: its final reply, which includes the queue id, and how long the hand-over took."""

    response: str
    seconds: float


class Mailer(Protocol):
    def send(self, msg, recipients) -> Optional[RelayReceipt]:
        """Submit msg to the outbound relay. Raises on failure."""


class SentArchive(Protocol):
    def archive(self, msg, thread_id: Optional[str] = None) -> str:
        """Store a copy of an already-sent message; return the archive's id for it."""


class TokenStore(Protocol):
    def load(self) -> Optional[dict]: ...
    def save(self, token: dict) -> None: ...


class Transport(Protocol):
    def request(self, method: str, url: str, headers: dict, body: Optional[bytes]) -> Tuple[int, bytes]:
        """Return (status, body) for any HTTP status. Raise OSError only if the network fails."""
