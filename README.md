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

Plume is an alpha release (0.1.0-alpha.2). It has been used to send mail as `@apache.org` from Gmail on
macOS (Apple silicon), for new messages and for replies written inline in a thread, with To, Cc and Bcc.
The Linux build passes its tests but has had little real use. Attachments and HTML formatting are not
supported, so messages go out as plain text, and there is no Windows support yet. The extension is not in
the Chrome Web Store, so you load it by hand. Gmail's page markup is not a public API, so a Gmail update
can break the button until the extension is adjusted. Expect some rough edges, and please report them.

## Getting started

Install the program with one command. It downloads the latest release for macOS (Apple silicon) or Linux
(x86_64), asks for your ASF user name and password, and registers the program with your browser:

```
sh -c "$(curl -fsSL https://raw.githubusercontent.com/CalvinKirs/plume/main/packaging/install.sh)"
```

Then download `plume-extension.zip` from the [releases page](https://github.com/CalvinKirs/plume/releases)
and unzip it. Open `chrome://extensions`, turn on Developer mode, choose Load unpacked and select the
unzipped folder. Enter your `@apache.org` address in the extension's options and restart the browser.

To build the program from source instead, you need Python 3.11 or newer:

```
git clone https://github.com/CalvinKirs/plume.git
cd plume
./packaging/build.sh
./dist/plume/plume setup
```

The [user guide](docs/user-guide.md) covers the rest, including troubleshooting and uninstalling.

## Development

```
cd server && python3 -m unittest discover -s tests     # standard library only
cd extension && npm install && npm test                 # unit tests, using jsdom
cd extension && CHROME=/path/to/chrome npm run e2e      # real Chromium against a mock Gmail page
```

`server/plume/` is the program that sends mail, `extension/` is the Chrome extension (Manifest V3) and
`packaging/` holds the PyInstaller build and the one-line installer.
[docs/architecture.md](docs/architecture.md) explains how a message travels from Gmail through the ASF mail
relay, [docs/design.md](docs/design.md) records why it is built this way, and
[docs/selectors.md](docs/selectors.md) covers the Gmail selectors, which are the part most likely to break.

## License

MIT. See [LICENSE](LICENSE). Copyright 2026 Calvin Kirs.
