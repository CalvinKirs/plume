class AuthError(Exception):
    """OAuth credentials are missing, expired or rejected."""


class ArchiveError(Exception):
    """The sent copy could not be stored."""


class ConfigError(Exception):
    """Plume is not configured (missing relay credentials)."""
