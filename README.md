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
the Chrome Web Store, so you load it by hand. Firefox works too, and has been tried by hand on
macOS. Firefox only runs signed extensions, so until a signed build is published you load it temporarily.
Gmail's page markup is not a public API, so a Gmail update can break the button until the extension is
adjusted. Expect some rough edges, and please report them.

## Getting started

The recommended way to install the program is from source. Plume signs in to the ASF relay with your
password, so it is worth being able to read the code you are about to run, and a source install runs
exactly what is in the checkout. It is a few hundred lines of Python with no dependencies beyond the
standard library, there is no build step, and it works on any macOS or Linux machine, whatever the
processor, with Python 3.8 or newer:

```
git clone https://github.com/CalvinKirs/plume.git
cd plume/server
python3 -m plume setup
```

`setup` asks for your ASF user name and password, copies the program to `~/.local/share/plume` and
registers it with your browser. You can delete the checkout afterwards.

There are also prebuilt packages, for machines that have no suitable Python and for people who prefer a
single command over reading code. They bundle their own Python, so nothing else has to be installed, at
the price of running a binary you cannot inspect. The installer below uses the prebuilt program on macOS
with Apple silicon and on Linux with x86_64, and installs from source on any other machine
(`PLUME_FROM_SOURCE=1` forces the source route everywhere):

```
sh -c "$(curl -fsSL https://raw.githubusercontent.com/CalvinKirs/plume/main/packaging/install.sh)"
```

Both routes end in the same place. Then download `plume-extension.zip` from the
[releases page](https://github.com/CalvinKirs/plume/releases) and unzip it. Open `chrome://extensions`,
turn on Developer mode, choose Load unpacked and select the unzipped folder. Enter your `@apache.org`
address in the extension's options, plus your name if you want it shown to recipients, and restart the
browser.

The [user guide](docs/user-guide.md) covers the rest, including troubleshooting and uninstalling.

## Development

```
cd server && python3 -m unittest discover -s tests     # standard library only
cd extension && npm install && npm test                 # unit tests, using jsdom
cd extension && CHROME=/path/to/chrome npm run e2e      # real Chromium against a mock Gmail page
node extension/scripts/build-extension.js firefox       # one package per browser: chrome or firefox
```

`server/plume/` is the program that sends mail, `extension/` is the Chrome extension (Manifest V3) and
`packaging/` holds the PyInstaller build and the one-line installer.
[docs/architecture.md](docs/architecture.md) explains how a message travels from Gmail through the ASF mail
relay, [docs/design.md](docs/design.md) records why it is built this way, and
[docs/selectors.md](docs/selectors.md) covers the Gmail selectors, which are the part most likely to break.

## License

MIT. See [LICENSE](LICENSE). Copyright 2026 Calvin Kirs.
