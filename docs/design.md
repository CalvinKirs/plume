# Design notes

## Overview

Plume has two parts. A Chrome extension adds a button to Gmail's compose window and reads the draft. A
local program, started by Chrome on demand, signs in to `mail-relay.apache.org` and sends the message.
Optionally the program also files a copy of the message under Gmail's Sent label.

## How a send works

1. The content script reads recipients, subject and text from the compose window. For a reply it also
   looks up the Message-ID and References of the message being answered.
2. It passes the draft to the extension's background worker, which forwards it to the local program
   through Chrome's native messaging. (An HTTP transport exists for debugging.)
3. The program builds the message and submits it to the relay over SMTP with STARTTLS (port 587) or
   implicit TLS (port 465), logging in with the ASF LDAP account.
4. If Gmail write-back is set up, the program inserts a copy into Gmail's Sent folder. A failure here is
   reported but does not turn the send into a failure, because the mail has already gone out.
5. The extension shows the outcome, closes the draft and adds an entry to the list of recent sends.

## Structure of the program

See [architecture.md](architecture.md) for the components, the path of a message and the layout of the
program's code.

## Decisions

**Native messaging instead of a local HTTP server.** A server would have to be started at login, would
occupy a port and would need a token to keep other web pages away from it. With native messaging Chrome
starts the program only when the button is used, and only the extension with the pinned ID can start it.
The HTTP server is still available for debugging.

**A one-directory build instead of a single file.** A single-file PyInstaller program unpacks itself into
a new temporary folder on every launch. On macOS, files unpacked by a process that Chrome started get the
quarantine flag, so Gatekeeper asked about `libpython3.x.dylib` on every send and the host never
answered. The folder is copied once by `setup`, with the quarantine flag cleared, and nothing is unpacked
afterwards. Startup is also faster.

**Plain text only.** Mailing lists and PonyMail expect plain text. Quoted replies are converted to lines
starting with "> ". Attachments are not read from the compose window yet.

**Insert-only Gmail access.** The Sent copy uses `users.messages.insert` with the `gmail.insert` scope,
which cannot read mail or send it. Authorization uses the loopback flow with PKCE, and the token file is
readable only by the user.

**A local log of recent sends.** The extension keeps the last 50 sends (recipients, subject, outcome,
relay reply, Message-ID) in `chrome.storage.local`, never the message text. It lets you check a message
after the notification has gone, and it gives ASF Infrastructure a queue ID to look for when a message
arrives late.

## Security model

- Only the extension with the pinned ID may start the native host. The host opens no network port.
- The relay password is stored in `~/.config/plume/config.json` with mode 0600. It is not encrypted.
  Moving it to the system keychain is planned.
- In HTTP mode the server listens on 127.0.0.1 only and requires a bearer token and an allowed Origin.
- The extension runs only on `mail.google.com` and reads a draft only when the button is clicked.

## Open questions

- Whether the relay accepts a From address other than the authenticated user's own. Only the user's own
  address has been tried.
- How long the Gmail authorization lasts for an app in "Testing" status. Google may expire it after seven
  days; this has not been checked.
- Reply headers depend on Gmail's undocumented "Show original" URL. It has failed in some threads, and the
  notification now says why.
- Attachments, HTML formatting, Windows, and storing the password in the keychain.
