# Plume user guide

Plume adds a "Send as apache.org" button to Gmail. When you click it, your message is sent through the ASF
mail relay (`mail-relay.apache.org`) with your `@apache.org` address as the sender. Gmail's own "Send mail
as" stops working for third-party addresses in January 2027
([Google's announcement](https://support.google.com/mail/answer/17101213)), and Plume is a replacement for
it. Mail sent to you is not affected, because it still reaches Gmail through your ASF forwarding.

Plume is an independent project. It is not affiliated with or endorsed by the Apache Software Foundation.
[architecture.md](architecture.md) describes how it works.

## What you need

You need a Mac with Apple silicon or a Linux machine (x86_64), Chrome, Chromium, Brave or Edge, and your ASF
account, meaning the LDAP user name and password you use for ASF services. Windows is not supported yet.
Your network must allow connections to `mail-relay.apache.org` on port 587 or 465.

## Installing the program

For now you build the program yourself, which needs Python 3.11 or newer:

```
git clone https://github.com/CalvinKirs/plume.git
cd plume
./packaging/build.sh
./dist/plume/plume setup
```

`setup` asks for your ASF user name and password, copies the program to `~/.local/share/plume/app/` and
registers it with every Chrome-based browser it finds.

Once release builds are published, this one-liner will install the program without needing Python:

```
sh -c "$(curl -fsSL https://raw.githubusercontent.com/CalvinKirs/plume/main/packaging/install.sh)"
```

It uses `curl` on purpose. macOS marks files downloaded in a browser as quarantined, and Gatekeeper then
refuses to run a program that Apple has not signed. If you did download an archive in a browser, run
`xattr -dr com.apple.quarantine plume` on the extracted folder before running `setup`.

## Installing the extension

Plume is not in the Chrome Web Store yet, so you load it from the repository. Open `chrome://extensions`,
turn on Developer mode, choose Load unpacked and select the `extension` directory. Then open the
extension's Options, enter your `@apache.org` address and save. Finally, quit the browser completely
(Cmd+Q on macOS) and start it again. That is only needed once, so that the browser notices the program you
registered. After you update the extension later, press its Reload button on `chrome://extensions` and
refresh the Gmail tab.

## Sending mail

Open Gmail and start a new message or a reply. Next to the usual Send button there is now a "Send as
apache.org" button. Fill in To, Cc and Bcc as usual, write your message and click it. Plume sends the
message and closes the draft.

When the send is finished, a notification appears at the top of the page and stays for about ten seconds.
Click it to dismiss it. A green one starting with "Sent as" means the ASF relay accepted the message. It
lists the recipients, shows how long the hand-over took and quotes the relay's reply. An amber one means the
message was sent but with a caveat, for example that a reply could not be threaded because Plume could not
read the original Message-ID. A red one starting with "NOT sent" means nothing was sent, and it says why.

If you want to check what Plume will send before sending it, hold Option (Alt on Linux) while you click the
button. Nothing is sent. Plume shows the recipients, the subject, the size of the text and whether it found
the reply headers.

The Options page of the extension lists your last 50 sends, with the time, result, recipients, subject, the
relay's queue reply and the Message-ID, so you can check a message even if you missed the notification.
The list stays in your browser and never contains message text. "Clear the list" empties it.

Messages go out as plain text. Quoted text in replies becomes lines that start with "> ", which is what
mailing lists expect. Formatting, inline images and attachments are not sent.

## A copy in Gmail's Sent folder

Mail sent through Plume does not go through Gmail, so it does not show up in Gmail's Sent folder. If you want
a copy there, Plume needs permission to add messages to your mailbox. It cannot read your mail or send
anything through Gmail.

In the [Google Cloud console](https://console.cloud.google.com/), create a project and enable the Gmail
API. Set up the OAuth consent screen with the External type, leave the publishing status on Testing and add
your own Google account as a test user. Then create an OAuth client ID of type Desktop app and note the
client ID and secret. Finally run these two commands:

```
~/.local/share/plume/app/plume configure    # enter the client ID and secret, keep the other answers
~/.local/share/plume/app/plume auth         # opens a browser once so you can grant access
```

Google may expire the authorization of an app in Testing status after about a week. If Plume then reports
an authorization problem, run `plume auth` again.

## If a message arrives late

A green notification means the ASF relay has accepted the message. What happens next, in the relay's queue,
on the recipient's mail server, in spam filters or in mailing list moderation, is outside Plume. To find
out where the time went, start with the hand-over time in the notification. If it took several seconds, the
relay or your network was slow. Port 465 sometimes works better than 587, and you can try it by adding
`"smtp_port": 465` to `~/.config/plume/config.json`.

If the relay took the message quickly, follow it from there. Open the late copy in Gmail, choose "Show
original" from the three-dot menu and read the `Received:` lines from the bottom, which is the oldest, to
the top. Compare their timestamps with the `Date:` line. A large gap between two lines is where the message
waited. The queue ID in the relay's reply lets ASF Infrastructure find the message in their logs. Note also
that a mailing list may hold a post for a moderator if it comes from an address the list does not
recognise as a subscriber.

## Troubleshooting

In the commands below, `plume` means the installed program, `~/.local/share/plume/app/plume`. It is not on
your `PATH`. Errors inside the program are logged to `~/.config/plume/host.log`.

- If the button does not appear, refresh the Gmail tab and check that the extension is enabled and was
  loaded from the `extension` directory. If Gmail has changed its layout, the extension needs an update
  (see [selectors.md](selectors.md)).
- If clicking does nothing, or the notification says the extension was reloaded or updated, refresh the
  Gmail tab.
- "no recipients found": add at least one recipient. In an inline reply, click the recipient line to expand it.
- "the message body reads as empty": type some text. Plume does not send attachments on their own.
- "Plume host is not installed": run `plume setup` again, then quit and restart the browser.
- "does not allow this extension id": the extension was loaded from a modified copy. Use the original
  `extension` directory, whose ID is fixed, and run `plume setup` again.
- "did not answer within 90 s": a macOS dialog may be waiting behind the browser window, or the relay
  cannot be reached. Answer the dialog, or run `plume setup` again.
- "relay rejected the login": the ASF user name or password is wrong. Run `plume configure`.
- "relay failure: ...": a network problem, or the relay refused the message. The text after the colon says
  which.
- "Plume is not configured": run `plume setup`.

## Privacy and security

Your LDAP password is stored in `~/.config/plume/config.json`, which only you can read (mode 0600). It is
not encrypted, so anyone who can read your files as you can read it. Storing it in the system keychain is
planned.

Only the extension with Plume's fixed ID can start the program, and the program opens no network port. The
extension runs only on `mail.google.com` and reads a draft only when you click the button. It keeps the list
of your last 50 sends (recipients, subject and outcome, no message text) in your browser and nowhere else.
Plume connects to `mail-relay.apache.org`, and to Google only if you set up the Sent copy. It has no
analytics and talks to no other servers.

## Limitations

There is no support for attachments, HTML formatting or Windows, and the extension is not in the Chrome Web
Store yet. A reply is threaded correctly on a mailing list only if Plume can read the original message's
ID. Otherwise the reply is still sent, but list archives may show it as a new thread. Finally, Gmail's page
structure is not a public interface, so a Gmail update can break the button until the extension is adjusted.

## Uninstalling

Remove the extension on `chrome://extensions`, delete `~/.local/share/plume` and `~/.config/plume`, and
delete `org.plume.host.json` from the `NativeMessagingHosts` directory of your browser profile. On macOS
that is `~/Library/Application Support/<browser>/NativeMessagingHosts/`, on Linux
`~/.config/<browser>/NativeMessagingHosts/`.

## License

MIT. See [LICENSE](../LICENSE).
