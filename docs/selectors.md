# Maintaining the Gmail selectors

Everything the extension assumes about Gmail's markup is in `extension/src/gmail-dom.js`, apart from the
lookup of reply headers, which is in `extension/src/reply-context.js`. Gmail's markup is not a public API
and changes without notice, so these are the first places to look when the button disappears or a draft
is read incorrectly.

The fixtures in `extension/tests/fixtures.js` are a hand-built approximation of the compose window. They
were not captured from Gmail, so a passing test does not prove that the real page still matches.

## Checking the selectors against Gmail

Open a compose window in Gmail and run these in the browser's developer console:

```
document.querySelectorAll('div[role="textbox"][g_editable="true"]').length   // message body, expect 1 per compose
document.querySelector('.aoO[role="button"]')                                // Send button
document.querySelector('input[name="subjectbox"]').value                     // subject
document.querySelectorAll('[name="to"] [email], input[name="to"]')           // recipients
document.querySelector('.og[role="button"]')                                 // Discard button
document.querySelectorAll('[data-legacy-message-id]')                        // messages of the open thread
```

An empty result points to the constant in `gmail-dom.js` that needs to change. If the Plume button does
not appear at all, the detection of the compose window has failed. That detection looks for a message body
and a Send button inside the same container.

The Send and Discard selectors match both English and Chinese labels, and also the class names `.aoO` and
`.og`, which do not depend on the interface language.

## Reply headers

To thread a reply correctly on a mailing list, the extension reads the original message from
`/mail/u/<n>/?view=om&permmsgid=msg-f:<decimal id>`, the address behind Gmail's "Show original". This
address is not documented. When it fails, the mail is still sent, the notification says why the reply
headers are missing, and list archives fall back to grouping by subject.

## End-to-end test

`extension/e2e/run.js` loads the extension into real Chromium against a mock Gmail page and drives the
whole chain: the button, the draft, the background worker, native messaging and the Python host. It checks
the wiring. It says nothing about Gmail's real markup.

```
cd extension && npm install && CHROME=/path/to/chrome npm run e2e
```
