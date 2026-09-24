# Plume

Keep sending as your `@apache.org` address from Gmail.

Google is removing Gmail's "Send as" for third-party addresses in January 2027
([announcement](https://support.google.com/mail/answer/17101213)). Plume adds a **Send as apache.org**
button to Gmail: a Chrome extension reads your draft, and a small local program sends it through
`mail-relay.apache.org` with your ASF LDAP account. Chrome starts that program on demand, so nothing runs in
the background and no port is opened.

> Independent community tool, not affiliated with or endorsed by the Apache Software Foundation.

**Documentation:** [User guide](docs/user-guide.md)

## Status

Early, working version (0.1). Verified: sending as `@apache.org` from Gmail on macOS (Apple silicon), Cc/Bcc in
new messages, plain-text quoting. Known gaps: no attachments or HTML, no Windows, not on the Chrome Web Store,
no published release yet (build from source, see the user guide), inline-reply edge cases (recipient rows,
reply headers) still being tuned. Gmail's markup is not a public API and may break the button.

## Quick start (from source)

```
git clone https://github.com/CalvinKirs/plume.git && cd plume
./packaging/build.sh && ./dist/plume/plume setup     # needs Python 3.11+
```

Then load `extension/` in `chrome://extensions` (Developer mode → Load unpacked), enter your address in the
extension options, and restart the browser. Details, troubleshooting and the optional Gmail Sent copy are in the
[user guide](docs/user-guide.md).

## Development

```
cd server && python3 -m unittest discover -s tests              # 39 tests, standard library only
cd extension && npm install && npm test                          # jsdom tests
cd extension && CHROME=/path/to/chrome npm run e2e               # real Chromium, mock Gmail page
```

- `server/plume/` — the send service. `cli.py` has `setup`, `configure`, `install-host`, `native`, `serve`, `auth`.
- `extension/` — Chrome MV3 extension. All Gmail selectors live in `src/gmail-dom.js` ([notes](docs/selectors.md)).
- `packaging/` — PyInstaller build (one-directory on purpose, see below) and the one-line installer.
- `docs/design.md` — design notes and open questions.

Architecture (ports and adapters, every port has a fake in the tests):

```
app.py (HTTP, debugging) ┐
native.py (Chrome host)  ┴-> api.send_payload -> service.SendService -> ports.Mailer      <- relay.SmtpRelayMailer
                                                                       -> ports.SentArchive <- gmail.GmailArchive | archive.NullArchive
gmail.GmailArchive -> tokens.TokenProvider -> oauth.GoogleOAuth, ports.TokenStore <- tokens.FileTokenStore
                   -> ports.Transport <- transport.UrllibTransport
```

Why the packaged program is a folder and not a single file: a one-file build unpacks itself into a new temp folder
on every launch, and on macOS files unpacked by a process that Chrome started are quarantined, so Gatekeeper prompted
for `libpython3.x.dylib` on every send and the host never answered.

Debug transport: `PLUME_TOKEN=<random> python3 -m plume serve` starts a token-protected server on `127.0.0.1:8765`
(`POST /send`), and the extension options have an *Advanced* switch for it. Environment variables
(`PLUME_USER`, `PLUME_PASSWORD`, `PLUME_SMTP_HOST`, `PLUME_SMTP_PORT`, `PLUME_PORT`, `PLUME_CONFIG`, ...) override
the config file `~/.config/plume/config.json`.

## License

[MIT](LICENSE) © 2026 Calvin Kirs
