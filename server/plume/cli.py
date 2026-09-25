import argparse
import getpass
import logging
import os
import platform
import smtplib
import ssl
import sys
from http.server import ThreadingHTTPServer

from . import __version__
from .app import make_handler
from .config import DEFAULT_CONFIG_PATH, ensure_private_dir, load_config, save_config
from .install import BROWSERS, install_host
from .launch import is_native_launch
from .native import serve as serve_native
from .oauth import run_local_auth
from .relay import connect
from .tls import default_context
from .tokens import FileTokenStore
from .wiring import UnconfiguredService, build_oauth, build_service


def cmd_serve(cfg, args):
    if not (cfg.user and cfg.password and cfg.token):
        raise SystemExit("set user and password (see `configure`) and PLUME_TOKEN")
    service = build_service(cfg)
    httpd = ThreadingHTTPServer(("127.0.0.1", cfg.listen_port), make_handler(cfg, service))
    print(f"plume listening on 127.0.0.1:{cfg.listen_port} (archive: {type(service.archive).__name__})", flush=True)
    httpd.serve_forever()


def _host_log():
    """Log warnings and tracebacks to ~/.config/plume/host.log, because Chrome throws away a native host's stderr."""
    try:
        path = os.path.expanduser("~/.config/plume/host.log")
        ensure_private_dir(os.path.dirname(path))
        # The log can contain recipient addresses, so create it readable by the user only.
        os.close(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600))
        os.chmod(path, 0o600)
        logging.basicConfig(filename=path, level=logging.WARNING, format="%(asctime)s %(name)s %(message)s")
    except OSError:
        pass


def cmd_native(cfg, args):
    # stdout carries the protocol, so stray prints must go to stderr instead.
    out = sys.stdout.buffer
    sys.stdout = sys.stderr
    _host_log()
    try:
        service = build_service(cfg or load_config())
    except Exception as e:  # e.g. unreadable config: answer every request with the reason instead of dying
        logging.getLogger("plume").exception("host failed to start")
        service = UnconfiguredService(f"Plume could not start: {type(e).__name__}: {e}")
    serve_native(service, sys.stdin.buffer, out)


def cmd_auth(cfg, args):
    if not (cfg.gmail_client_id and cfg.gmail_client_secret):
        raise SystemExit("set gmail_client_id and gmail_client_secret (Google Cloud desktop OAuth client)")
    run_local_auth(build_oauth(cfg), FileTokenStore(cfg.token_path))
    print(f"authorized; token saved to {cfg.token_path}")


def cmd_configure(cfg, args):
    values = {
        "user": input(f"ASF username [{cfg.user}]: ").strip() or cfg.user,
        "password": getpass.getpass("LDAP password (hidden): ") or cfg.password,
    }
    client_id = input(f"Gmail OAuth client id, empty to skip [{cfg.gmail_client_id}]: ").strip() or cfg.gmail_client_id
    if client_id:
        values["gmail_client_id"] = client_id
        values["gmail_client_secret"] = getpass.getpass("Gmail OAuth client secret (hidden): ") or cfg.gmail_client_secret
    save_config(values)
    print(f"saved to {DEFAULT_CONFIG_PATH} (mode 0600)")


def cmd_setup(cfg, args):
    """Guided first run: ask for the relay account, then register the host with Chrome."""
    print("Plume setup\n")
    cmd_configure(cfg, args)
    args.browser = None
    cmd_install_host(cfg, args)
    if getattr(sys, "frozen", False):
        input("\nPress Enter to close this window.")  # a double-clicked console would vanish otherwise


def cmd_check(cfg, args):
    """Connect to the relay and verify its certificate, without logging in or sending anything."""
    ctx = default_context()
    print(f"plume {__version__}, Python {platform.python_version()}, {ssl.OPENSSL_VERSION}")
    print(f"trusted certificates loaded: {ctx.cert_store_stats().get('x509_ca', 0)}")
    try:
        with connect(cfg.smtp_host, cfg.smtp_port, ctx) as smtp:
            cert = smtp.sock.getpeercert()
    except (OSError, smtplib.SMTPException) as e:
        raise SystemExit(f"cannot connect to {cfg.smtp_host}:{cfg.smtp_port}: {e}")
    subject = dict(item[0] for item in cert["subject"]).get("commonName", "?")
    issuer = dict(item[0] for item in cert["issuer"]).get("organizationName", "?")
    print(f"{cfg.smtp_host}:{cfg.smtp_port}: TLS verified. Certificate for {subject}, issued by {issuer}, valid until {cert['notAfter']}.")


def cmd_install_host(cfg, args):
    for path in install_host(browsers=args.browser):
        print("registered:", path)
    print("Restart your browser, then use the extension.")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="plume")
    parser.add_argument("--version", action="version", version=f"plume {__version__}")
    sub = parser.add_subparsers(dest="command")
    for name in ("serve", "native", "auth", "setup", "configure", "check"):
        sub.add_parser(name)
    inst = sub.add_parser("install-host")
    inst.add_argument("--browser", action="append", choices=BROWSERS)
    argv = sys.argv[1:] if argv is None else argv
    if is_native_launch(argv):
        return cmd_native(None, None)  # a browser started us as its native messaging host
    args = parser.parse_args(argv)
    handlers = {"serve": cmd_serve, "native": cmd_native, "auth": cmd_auth, "setup": cmd_setup,
                "configure": cmd_configure, "install-host": cmd_install_host, "check": cmd_check}
    args.command = args.command or "setup"  # double-clicked binary: run the guided setup
    # The native host loads its own config, so a broken file is reported back to the extension.
    handlers[args.command](None if args.command == "native" else load_config(), args)
