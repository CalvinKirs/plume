<p align="center"><img src="assets/logo.svg" alt="Plume logo" width="96" height="96"></p>

<h1 align="center">Plume</h1>

Plume lets you keep sending mail from Gmail as your `@apache.org` address.

Google will stop supporting "Send mail as" for third-party addresses in January 2027
([announcement](https://support.google.com/mail/answer/17101213)). Plume adds a "Send as apache.org"
button to Gmail's compose window. A Chrome extension reads the draft and passes it to a small local
program, which sends it through `mail-relay.apache.org` with your ASF account. Chrome starts the program
when it is needed, so nothing keeps running in the background and no network port is opened.

Plume is an independent project. It is not affiliated with or endorsed by the Apache Software Foundation.

## Status

This is an early version. It has been used to send mail as `@apache.org` from Gmail on macOS (Apple
silicon), including Cc and Bcc on new messages. What is missing or unfinished:

- Attachments and HTML formatting. Messages are sent as plain text.
- Windows support.
- A Chrome Web Store listing and published release binaries. For now you load the extension from a
  checkout and build the program yourself.
- Inline replies (the box that opens inside a thread) still have rough edges around recipients and
  reply headers.

Gmail's page markup is not a public API, so a Gmail update can break the button until the extension is
adjusted.

## Getting started

You need Python 3.11 or newer to build the program, and a Chromium-based browser.

```
git clone https://github.com/CalvinKirs/plume.git
cd plume
./packaging/build.sh
./dist/plume/plume setup
```

`setup` asks for your ASF user name and password and registers the program with your browser. Then open
`chrome://extensions`, turn on Developer mode, choose Load unpacked and select the `extension` directory.
Enter your `@apache.org` address in the extension's options and restart the browser.

The [user guide](docs/user-guide.md) covers the rest: using the button, keeping a copy in Gmail's Sent
folder, troubleshooting and uninstalling.

## Development

```
cd server && python3 -m unittest discover -s tests     # standard library only
cd extension && npm install && npm test                 # unit tests, using jsdom
cd extension && CHROME=/path/to/chrome npm run e2e      # real Chromium against a mock Gmail page
```

The code is laid out as follows.

- `server/plume/` is the program that sends mail. `cli.py` provides the commands `setup`, `configure`,
  `install-host`, `native`, `serve` and `auth`.
- `extension/` is the Chrome extension (Manifest V3). All Gmail selectors are in `src/gmail-dom.js`; see
  [docs/selectors.md](docs/selectors.md).
- `packaging/` holds the PyInstaller build and the one-line installer.
- [docs/architecture.md](docs/architecture.md) shows how a message travels and who does what, including the
  ASF mail relay that actually sends it. [docs/design.md](docs/design.md) explains why it is built this way.

## License

MIT. See [LICENSE](LICENSE). Copyright 2026 Calvin Kirs.
