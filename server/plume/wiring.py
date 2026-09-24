from .archive import NullArchive
from .errors import ConfigError
from .gmail import GmailArchive
from .oauth import GoogleOAuth
from .relay import SmtpRelayMailer
from .service import SendService
from .tokens import FileTokenStore, TokenProvider
from .transport import UrllibTransport


def build_oauth(cfg, transport=None):
    return GoogleOAuth(cfg.gmail_client_id, cfg.gmail_client_secret, transport or UrllibTransport())


def build_service(cfg):
    if not (cfg.user and cfg.password):
        return UnconfiguredService()
    mailer = SmtpRelayMailer(cfg.smtp_host, cfg.smtp_port, cfg.user, cfg.password)
    store = FileTokenStore(cfg.token_path)
    if cfg.gmail_client_id and store.load():
        transport = UrllibTransport()
        tokens = TokenProvider(build_oauth(cfg, transport), store)
        archive = GmailArchive(tokens, transport)
    else:
        archive = NullArchive()
    return SendService(mailer, archive)


class UnconfiguredService:
    """Stands in when Plume cannot start (no credentials, unreadable config). Every request gets the reason back."""

    def __init__(self, reason="Plume is not configured: run `plume setup`"):
        self.reason = reason

    def send(self, *args, **kwargs):
        raise ConfigError(self.reason)
