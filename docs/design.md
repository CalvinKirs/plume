# Design notes

This file records why Plume is built the way it is. For the components and the path of a message, see
[architecture.md](architecture.md).

## Native messaging instead of a local server

The first version was a small HTTP server that the extension called on 127.0.0.1. That works, but the
server has to be started at login, it occupies a port, and it needs a token so that other web pages cannot
use it. With native messaging, Chrome starts the program only when the button is used, no port is opened,
and only the extension with the pinned ID can start it. The HTTP server is still there for debugging and
for scripts.

## A folder instead of a single file

A single-file PyInstaller program unpacks itself into a new temporary folder every time it starts. On
macOS, files unpacked by a process that Chrome started get the quarantine flag, so Gatekeeper asked about
`libpython3.x.dylib` on every send, and the program never got to answer. The packaged program is therefore
a folder. `setup` copies it once and clears the quarantine flag, and nothing is unpacked afterwards. It also
starts faster.

## Plain text only

Mailing lists and PonyMail expect plain text, so Plume sends plain text and turns quoted replies into lines
that start with "> ". Attachments are not read from the compose window yet.

## Gmail access

The copy in the Sent folder uses `users.messages.insert` with the `gmail.insert` scope, which can add
messages to a mailbox but cannot read or send anything. Authorization uses the loopback flow with PKCE, and
the token file is readable only by the user.

## The list of recent sends

The extension keeps the last 50 sends, with recipients, subject, outcome, the relay's reply and the
Message-ID, but never the message text. It exists because the notification is easy to miss when the draft
closes right after sending, and because the relay's queue ID is what ASF Infrastructure needs to trace a
message that arrives late.

## Security

Only the extension with the pinned ID may start the native host, and the host opens no network port. In
HTTP mode the server listens on 127.0.0.1 only and requires a bearer token and an allowed Origin. The
extension runs only on `mail.google.com` and reads a draft only when the button is clicked. The relay
password is stored in `~/.config/plume/config.json` with mode 0600. It is not encrypted, and moving it to
the system keychain is planned.

## Open questions

- Whether the relay accepts a From address other than the authenticated user's own. Only the user's own
  address has been tried.
- How long the Gmail authorization lasts for an app in Testing status. Google may expire it after seven
  days. This has not been checked.
- Reply headers depend on Gmail's undocumented "Show original" address. It has failed in some threads, and
  the notification now says why.
- Attachments, HTML formatting, Windows support and keychain storage are not done.
