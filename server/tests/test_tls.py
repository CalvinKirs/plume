import ssl
import unittest
from unittest import mock

from plume import tls


class FakeContext:
    """Stands in for ssl.SSLContext with a chosen number of loaded CA certificates."""

    def __init__(self, loaded):
        self.loaded = loaded
        self.cafiles = []

    def cert_store_stats(self):
        return {"x509_ca": self.loaded}

    def load_verify_locations(self, cafile=None):
        self.cafiles.append(cafile)


def context_with(loaded, existing):
    fake = FakeContext(loaded)
    with mock.patch.object(tls.ssl, "create_default_context", return_value=fake), \
            mock.patch.object(tls.os.path, "isfile", side_effect=lambda p: p in existing):
        result = tls.default_context()
    assert result is fake
    return fake


class DefaultContextTests(unittest.TestCase):
    def test_an_empty_default_store_falls_back_to_the_first_system_bundle_that_exists(self):
        ctx = context_with(0, {"/etc/ssl/cert.pem", "/etc/pki/tls/certs/ca-bundle.crt"})
        self.assertEqual(ctx.cafiles, ["/etc/ssl/cert.pem"])

    def test_the_search_order_covers_debian_and_red_hat_systems(self):
        self.assertEqual(context_with(0, {"/etc/ssl/certs/ca-certificates.crt"}).cafiles, ["/etc/ssl/certs/ca-certificates.crt"])
        self.assertEqual(context_with(0, {"/etc/pki/tls/certs/ca-bundle.crt"}).cafiles, ["/etc/pki/tls/certs/ca-bundle.crt"])

    def test_a_populated_default_store_is_left_alone(self):
        self.assertEqual(context_with(140, {"/etc/ssl/cert.pem"}).cafiles, [])

    def test_no_bundle_anywhere_still_returns_a_context(self):
        self.assertEqual(context_with(0, set()).cafiles, [])

    def test_the_real_context_verifies_certificates_and_host_names(self):
        ctx = tls.default_context()
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)


if __name__ == "__main__":
    unittest.main()
