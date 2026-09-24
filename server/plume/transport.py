import urllib.error
import urllib.request

from .tls import default_context


class UrllibTransport:
    def __init__(self, timeout=30):
        self.timeout = timeout

    def request(self, method, url, headers, body):
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=default_context()) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()
