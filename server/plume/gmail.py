import base64
import json
from typing import Optional

from .errors import ArchiveError, AuthError

API = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailArchive:
    """Files a sent copy into Gmail with users.messages.insert (label SENT).

    insert only stores the message; it never sends anything.
    """

    def __init__(self, tokens, transport, api=API):
        self.tokens, self.transport, self.api = tokens, transport, api

    def archive(self, msg, thread_id: Optional[str] = None) -> str:
        body = {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode(), "labelIds": ["SENT"]}
        if thread_id:
            body["threadId"] = thread_id
        payload = json.dumps(body).encode()
        status, data = self._post(payload, force_refresh=False)
        if status == 401:  # access token revoked or expired early: refresh once and retry
            status, data = self._post(payload, force_refresh=True)
        if status != 200:
            raise ArchiveError(f"gmail insert failed with HTTP {status}")
        return json.loads(data)["id"]

    def _post(self, payload, force_refresh):
        try:
            token = self.tokens.access_token(force_refresh=force_refresh)
        except AuthError as e:
            raise ArchiveError(str(e)) from e
        return self.transport.request(
            "POST", f"{self.api}/messages?internalDateSource=dateHeader",
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, payload)
