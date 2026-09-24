# Gmail selectors: what to check and how to fix

All Gmail markup assumptions are in `extension/src/gmail-dom.js` (plus the reply lookup in
`extension/src/reply-context.js`). The test fixtures in `extension/tests/fixtures.js` are a
hand-built approximation, **not captured from live Gmail**, so the first real run may need fixes.

## First real run checklist
Open a compose window in Gmail, DevTools console:

    document.querySelectorAll('div[role="textbox"][g_editable="true"]').length   // body: expect 1 per compose
    document.querySelector('.aoO[role="button"]')                                // send button
    document.querySelector('input[name="subjectbox"]').value                     // subject
    document.querySelectorAll('[name="to"] [email], input[name="to"]')           // recipients
    document.querySelector('.og[role="button"]')                                 // discard button
    document.querySelectorAll('[data-legacy-message-id]')                        // open thread's messages

Whatever is empty tells you which constant in `gmail-dom.js` to adjust. If the button does not
appear at all, the compose detection (body textbox + send button) is what failed.

## Reply headers
`fetchReplyContext` reads the original message from
`/mail/u/<n>/?view=om&permmsgid=msg-f:<decimal id>` (Gmail's "Show original"), which is an
undocumented endpoint. If it stops working the send still succeeds, the toast says
"reply headers unavailable", and list threading falls back to the subject.

## Automated end-to-end check
`extension/e2e/run.js` loads the extension into real Chromium against a **mock** Gmail page and drives
the whole chain (button, draft, background worker, native messaging, the Python host; the relay is
pointed at a closed port so the expected outcome is a relay error). It proves the wiring, not Gmail's
real markup:

    cd extension && npm install && CHROME=/path/to/chrome npm run e2e
