# Plume user guide

Plume adds a **Send as apache.org** button to Gmail. It sends the message through the ASF mail relay
(`mail-relay.apache.org`) with your `@apache.org` address as the sender, which Gmail's own "Send as"
will no longer do for third-party addresses from January 2027
([Google's announcement](https://support.google.com/mail/answer/17101213)).
Incoming mail is unaffected: it keeps arriving through your ASF forwarding.

> Plume is an independent, community tool. It is not affiliated with or endorsed by the Apache Software Foundation.

## How it works

```
Gmail tab ── Plume extension ── Chrome starts the Plume program on demand ── mail-relay.apache.org
```

The extension reads your draft (recipients, subject, text). Chrome then starts a small local program that
signs in to the ASF relay with your LDAP account and sends the mail. Nothing runs in the background and no
network port is opened on your computer.

## Requirements

- macOS on Apple silicon, or Linux on x86_64. (Windows is not supported yet.)
- Chrome, Chromium, Brave or Edge.
- Your ASF account (the LDAP user name and password you use for ASF services).
- Your network must allow outgoing connections to `mail-relay.apache.org` on port 587 or 465.

## 1. Install the Plume program

**Once a release is published** (see the repository's *Releases* page), one line in a terminal does everything:

```
sh -c "$(curl -fsSL https://raw.githubusercontent.com/CalvinKirs/plume/main/packaging/install.sh)"
```

**Until then, build it yourself** (needs Python 3.11 or newer):

```
git clone https://github.com/CalvinKirs/plume.git
cd plume
./packaging/build.sh
./dist/plume/plume setup
```

`setup` asks for your ASF user name and LDAP password, copies the program to `~/.local/share/plume/app/`
and registers it with every Chrome-family browser it finds. Your password is stored only on this computer
(see *Security* below).

Why a terminal command on macOS: a program downloaded in a browser is blocked by Gatekeeper because it is not
signed by Apple. Files fetched with `curl` carry no such flag. If you did download the archive in a browser, run
`xattr -dr com.apple.quarantine plume` on the extracted folder first.

## 2. Install the extension

Plume is not in the Chrome Web Store yet, so load it from the repository folder:

1. Open `chrome://extensions` and switch on **Developer mode**.
2. Click **Load unpacked** and choose the `extension` folder of the repository.
3. Open the extension's **Options** and enter your `@apache.org` address. Save.
4. **Quit the browser completely** (Cmd+Q on macOS) and start it again. This is needed once, so the browser
   notices the newly registered program.

After you update the extension later, click its **Reload** button on `chrome://extensions` **and refresh the Gmail tab**.

## 3. Use it

Open Gmail and start a new message or a reply. Next to the normal Send button there is **Send as apache.org**.
Fill in To, Cc and Bcc as usual, write your text and click it. Plume sends the mail and closes the draft.

| Message at the bottom left | Meaning |
|---|---|
| `Plume: sent (To 1, Cc 0, Bcc 0)` | Sent. The numbers are how many recipients Plume read. |
| `... no copy in Gmail Sent, write-back is not set up` | Sent, but Gmail has no copy in its Sent folder. See *Keep a copy in Gmail Sent*. |
| `... reply headers unavailable: <reason>` | Sent, but as a new thread for list readers, because Plume could not read the original message's ID. |

**Dry run:** hold **Option** (Mac) or **Alt** and click the button. Nothing is sent; Plume shows what it read
(To, Cc, Bcc, subject, body size, whether reply headers were found). Use it to check a message first.

What Plume sends: **plain text only**. Quoted replies are converted to `> ` lines, the way mailing lists expect.
Formatting, inline images and **attachments are not sent**.

## Keep a copy in Gmail Sent (optional)

Without this, mail sent through Plume does not show up in Gmail's Sent folder. To file a copy there, Plume needs
permission to *insert* (not read or send) messages into your mailbox:

1. In the [Google Cloud console](https://console.cloud.google.com/) create a project and enable the **Gmail API**.
2. Configure the OAuth consent screen (type *External*, publishing status *Testing*) and add your own Google account as a test user.
3. Create credentials: **OAuth client ID**, application type **Desktop app**. Copy the client ID and secret.
4. Run:
   ```
   ~/.local/share/plume/app/plume configure     # paste the client ID and secret, keep the other answers
   ~/.local/share/plume/app/plume auth          # opens a browser once to grant access
   ```

Google may expire the access of an app in *Testing* status after about 7 days. If Plume then reports an
authorization problem, run `plume auth` again.

## Troubleshooting

In the commands below, `plume` stands for the installed program, `~/.local/share/plume/app/plume`
(it is not added to your `PATH`).

| Symptom | What to do |
|---|---|
| No button appears | Refresh the Gmail tab. Check the extension is enabled and loaded from the `extension` folder. Gmail's page layout can change; please open an issue (see `docs/selectors.md`). |
| Clicking does nothing, or `the extension was reloaded or updated` | Refresh the Gmail tab. |
| `no recipients found` | Add at least one recipient. In an inline reply, click the recipient line to expand it. |
| `the message body reads as empty` | Type some text. Plume sends the message text, not only attachments. |
| `Plume host is not installed` | Run `plume setup` again, then quit and restart the browser. |
| `does not allow this extension id` | The extension was loaded from a modified copy. Use the original `extension` folder (its ID is fixed) and run `plume setup` again. |
| `The Plume host did not answer within 90 s` | A macOS dialog may be waiting behind the browser window, or the relay is unreachable. Answer the dialog, or run `plume setup` again. |
| `relay rejected the login` | Wrong ASF user name or password. Run `plume configure`. |
| `relay failure: ...` | Network problem or the relay refused the message. The text after the colon says why. |
| `not configured` | Run `plume setup`. |

Errors inside the program are logged to `~/.config/plume/host.log`.

## A message arrives late

When Plume says **Sent**, the ASF mail relay has accepted the message, and the notification shows the relay's own
reply (`Relay reply: 250 ... queued as <id>`) and how long the hand-over took. What happens afterwards (relay queue,
the recipient's mail server, spam filtering, list moderation) is outside Plume. To find out where the time went:

1. **Look at the hand-over time** in the notification. A few seconds or more means the relay or your network was slow.
   Trying port 465 instead of 587 sometimes helps: set `"smtp_port": 465` in `~/.config/plume/config.json`.
2. **If it was accepted quickly, follow the message.** Open the late message in Gmail, choose the three dots and
   **Show original**, and read the `Received:` lines from the bottom (oldest) to the top. Compare their timestamps with the
   `Date:` line: a big gap between two lines is where the message waited. The queue id from the relay reply lets ASF
   Infrastructure find it in their logs.
3. **Mailing lists** may hold a post for a moderator when it comes from an address the list does not recognise as a subscriber.

## Security and privacy

- Your LDAP password is kept in `~/.config/plume/config.json` with permission 0600 (readable only by you).
  It is **not encrypted**; anyone who can read your files as you can read it. Storing it in the system keychain is planned.
- Only the extension with Plume's fixed ID may start the program. The program opens no network port.
- The extension works only on `mail.google.com`. It reads a draft only when you click the button.
- Plume connects to `mail-relay.apache.org` (and to Google only if you enabled the Gmail Sent copy).
  There are no analytics and no other servers.
- The Gmail permission requested for the Sent copy is *insert only*: it cannot read your mail.

## Known limitations

- No attachments, no HTML formatting, no Windows support, no Chrome Web Store listing yet.
- Replies to a thread need the original message's ID. If Plume cannot read it, the reply is still sent, but list
  archives may not thread it.
- Gmail's page structure is not a public API. A Gmail update can break the button until the extension is adjusted.

## Uninstall

1. Remove the extension on `chrome://extensions`.
2. Delete `~/.local/share/plume` and `~/.config/plume`.
3. Delete `org.plume.host.json` from `NativeMessagingHosts` in your browser's profile folder:
   macOS `~/Library/Application Support/<Browser>/NativeMessagingHosts/`, Linux `~/.config/<browser>/NativeMessagingHosts/`.

## License

MIT. See [LICENSE](../LICENSE).
