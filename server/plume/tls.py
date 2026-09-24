import os
import ssl

# System CA bundles, tried in this order when Python's own default location holds no certificates.
# macOS ships /etc/ssl/cert.pem, Debian and Ubuntu use ca-certificates.crt, and Red Hat systems ca-bundle.crt.
_SYSTEM_BUNDLES = (
    "/etc/ssl/cert.pem",
    "/etc/ssl/certs/ca-certificates.crt",
    "/etc/pki/tls/certs/ca-bundle.crt",
    "/etc/ssl/ca-bundle.pem",
    "/etc/pki/tls/cert.pem",
)


def default_context():
    """A TLS context that verifies certificates against the system's trusted roots.

    A packaged program carries its own Python, and on macOS that Python has no certificates at its
    default location, so every connection would fail with "unable to get local issuer certificate".
    When the default location is empty, fall back to the operating system's own bundle.
    """
    ctx = ssl.create_default_context()
    if ctx.cert_store_stats().get("x509_ca", 0) == 0:
        for path in _SYSTEM_BUNDLES:
            if os.path.isfile(path):
                ctx.load_verify_locations(cafile=path)
                break
    return ctx
