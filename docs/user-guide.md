# Plume user guide

Plume adds a "Send as apache.org" button to Gmail. It sends your message through the ASF mail relay
(`mail-relay.apache.org`) with your `@apache.org` address as the sender. Gmail's own "Send mail as" stops
working for third-party addresses in January 2027
([Google's announcement](https://support.google.com/mail/answer/17101213)). Mail sent to you is not
affected, because it still reaches Gmail through your ASF forwarding.

Plume is an independent project and is not affiliated with or endorsed by the Apache Software Foundation.

## How it works

```
Gmail tab  ->  Plume extension  ->  Plume program (started by Chrome)  ->  mail-relay.apache.org
```

The extension reads your draft. Chrome then starts a small program on your computer, which logs in to the
ASF relay with your LDAP account and hands the message over. The program runs only while a message is
being sent, and it opens no network port.

## Requirements

- macOS on Apple silicon, or Linux on x86_64. Windows is not supported yet.
- Chrome, Chromium, Brave or Edge.
- Your ASF account: the LDAP user name and password you use for ASF services.
- A network that allows outgoing connections to `mail-relay.apache.org` on port 587 or 465.

## Installing the program

Build it from a checkout of the repository. You need Python 3.11 or newer.

```
git clone https://github.com/CalvinKirs/plume.git
cd plume
./packaging/build.sh
./dist/plume/plume setup
```

`setup` asks for your ASF user name and password, copies the program to `~/.local/share/plume/app/` and
registers it with every Chrome-based browser it finds.

Once release builds are published, one command will do all of this without Python:

```
sh -c "$(curl -fsSL https://raw.githubusercontent.com/CalvinKirs/plume/main/packaging/install.sh)"
```

The installer downloads the program with `curl` on purpose. A program downloaded in a browser gets a
quarantine flag from macOS, and Gatekeeper refuses to run it because it is not signed by Apple. If you
downloaded an archive in a browser anyway, run `xattr -dr com.apple.quarantine plume` on the extracted
folder before `setup`.

## Installing the extension

Plume is not in the Chrome Web Store yet, so load it from the repository:

1. Open `chrome://extensions` and turn on Developer mode.
2. Choose Load unpacked and select the `extension` directory of the repository.
3. Open the extension's Options, enter your `@apache.org` address and save.
4. Quit the browser completely (Cmd+Q on macOS) and start it again. This is only needed once, so that the
   browser notices the newly registered program.

After you update the extension, use its Reload button on `chrome://extensions` and refresh the Gmail tab.

## Sending mail

Open Gmail and start a new message or a reply. Next to the usual Send button you will see "Send as
apache.org". Fill in To, Cc and Bcc as usual, write your text and click it. Plume sends the message and
closes the draft.

When the send finishes, a notification appears at the top of the page and stays for about ten seconds.
Click it to dismiss it.

| Notification | Meaning |
|---|---|
| Green, "Sent as ..." | The ASF relay accepted the message. The notification lists the recipients, how long the hand-over took and the relay's reply. |
| Amber, "Sent as ..." | Sent, but with a caveat that is spelled out in the notification, for example that a reply could not be threaded because the original Message-ID could not be read. |
| Red, "NOT sent" | Nothing was sent. The notification gives the reason. |

**Dry run.** Hold Option (Alt on Linux) while clicking the button. Nothing is sent. Plume shows what it
read from the draft: To, Cc, Bcc, subject, body size and whether reply headers were found.

**Recent sends.** The extension's Options page lists your last 50 sends with the time, result, recipients,
subject, the relay's queue reply and the Message-ID. It is kept in this browser only and never contains
the message text. "Clear the list" empties it.

**What is sent.** Plain text only. Quoted text in replies is converted to lines starting with "> ", which is
what mailing lists expect. Formatting, inline images and attachments are not sent.

## Keeping a copy in Gmail's Sent folder

Without this step, mail sent through Plume does not appear in Gmail's Sent folder. To have a copy filed
there, Plume needs permission to insert messages into your mailbox. It cannot read your mail or send
anything through Gmail.

1. In the [Google Cloud console](https://console.cloud.google.com/), create a project and enable the Gmail API.
2. Configure the OAuth consent screen. Choose the External type, leave the publishing status on Testing
   and add your own Google account as a test user.
3. Create an OAuth client ID of type Desktop app and note the client ID and secret.
4. Run:
   ```
   ~/.local/share/plume/app/plume configure    # enter the client ID and secret, keep the other answers
   ~/.local/share/plume/app/plume auth         # opens a browser once so you can grant access
   ```

Google may expire the authorization of an app in Testing status after about a week. If Plume then reports
an authorization problem, run `plume auth` again.

## When a message arrives late

A green notification means the ASF relay has accepted the message. What happens after that (the relay's
queue, the recipient's mail server, spam filtering, mailing list moderation) is outside Plume. To find out
where the time went:

1. Look at the hand-over time in the notification. If it took several seconds, the relay or your network
   was slow. Port 465 sometimes works better than 587; add `"smtp_port": 465` to
   `~/.config/plume/config.json` to try it.
2. If the relay accepted the message quickly, follow the message. Open the late copy in Gmail, choose the
   three-dot menu and "Show original", and read the `Received:` lines from the bottom (oldest) to the top.
   Compare their timestamps with the `Date:` line. A large gap between two lines shows where the message
   waited. The queue ID in the relay's reply lets ASF Infrastructure find the message in their logs.
3. A mailing list may hold a post for a moderator if it comes from an address the list does not recognise
   as a subscriber.

## Troubleshooting

In these commands, `plume` means the installed program, `~/.local/share/plume/app/plume`. It is not added
to your `PATH`. Errors inside the program are logged to `~/.config/plume/host.log`.

| What you see | What to do |
|---|---|
| No button | Refresh the Gmail tab. Check that the extension is enabled and was loaded from the `extension` directory. If Gmail changed its layout, the extension needs an update; see `docs/selectors.md`. |
| Clicking does nothing, or "The extension was reloaded or updated" | Refresh the Gmail tab. |
| "no recipients found" | Add at least one recipient. In an inline reply, click the recipient line to expand it. |
| "the message body reads as empty" | Type some text. Plume does not send attachments on their own. |
| "Plume host is not installed" | Run `plume setup` again, then quit and restart the browser. |
| "does not allow this extension id" | The extension was loaded from a modified copy. Use the original `extension` directory, whose ID is fixed, and run `plume setup` again. |
| "did not answer within 90 s" | A macOS dialog may be waiting behind the browser window, or the relay cannot be reached. Answer the dialog, or run `plume setup` again. |
| "relay rejected the login" | The ASF user name or password is wrong. Run `plume configure`. |
| "relay failure: ..." | A network problem, or the relay refused the message. The text after the colon says which. |
| "Plume is not configured" | Run `plume setup`. |

## Security and privacy

- Your LDAP password is stored in `~/.config/plume/config.json`, readable only by you (mode 0600). It is
  not encrypted, so anyone who can read your files as you can read it. Storing it in the system keychain
  is planned.
- Only the extension with Plume's fixed ID can start the program, and the program opens no network port.
- The extension runs only on `mail.google.com` and reads a draft only when you click the button.
- The extension keeps a log of your last 50 sends (recipients, subject and outcome, but no message text)
  in this browser only.
- Plume connects to `mail-relay.apache.org`, and to Google only if you set up the Sent copy. It has no
  analytics and talks to no other servers.

## Limitations

- No attachments, no HTML formatting, no Windows support and no Chrome Web Store listing yet.
- A reply is threaded correctly only if Plume can read the original message's ID. Otherwise the reply is
  still sent, but list archives may show it as a new thread.
- Gmail's page structure is not a public interface. A Gmail update can break the button until the
  extension is adjusted.

## Uninstalling

1. Remove the extension on `chrome://extensions`.
2. Delete `~/.local/share/plume` and `~/.config/plume`.
3. Delete `org.plume.host.json` from the `NativeMessagingHosts` directory of your browser profile. On macOS
   that is `~/Library/Application Support/<browser>/NativeMessagingHosts/`, on Linux
   `~/.config/<browser>/NativeMessagingHosts/`.

## License

MIT. See [LICENSE](../LICENSE).
