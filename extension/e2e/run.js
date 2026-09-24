// End-to-end check: real Chromium, the real extension, a mock Gmail page and the real native host
// (started through the source launcher). It exercises the wiring from the content script through
// the background worker and native messaging to the Python host. It does not exercise Gmail's own
// markup (see docs/selectors.md).
// Usage: CHROME=/path/to/chrome node e2e/run.js
const { chromium } = require('playwright-core');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { composeHtml } = require('../tests/fixtures');

const root = path.resolve(__dirname, '..', '..');
const home = fs.mkdtempSync(path.join(os.tmpdir(), 'plume-e2e-'));
const profile = path.join(home, '.config', 'chromium');
fs.mkdirSync(profile, { recursive: true });

// Register the host in a throwaway profile and point the relay at a closed port.
execFileSync('python3', ['-c', `from plume.install import install_host; install_host(home=${JSON.stringify(home)}, browsers=["chromium"], system="Linux")`],
  { cwd: path.join(root, 'server'), env: { ...process.env, PYTHONPATH: path.join(root, 'server') } });
fs.mkdirSync(path.join(home, '.config', 'plume'), { recursive: true });
fs.writeFileSync(path.join(home, '.config', 'plume', 'config.json'),
  JSON.stringify({ user: 'u', password: 'p', smtp_host: '127.0.0.1', smtp_port: 1 }));

(async () => {
  const ctx = await chromium.launchPersistentContext(profile, {
    executablePath: process.env.CHROME, headless: false, env: { ...process.env, HOME: home },
    args: ['--headless=new', '--no-sandbox', `--disable-extensions-except=${path.join(root, 'extension')}`, `--load-extension=${path.join(root, 'extension')}`],
  });
  const results = [];
  const check = (name, ok, detail = '') => { results.push(ok); console.log(`${ok ? 'PASS' : 'FAIL'} ${name} ${detail}`); };
  try {
    await ctx.route('https://mail.google.com/**', (r) => r.fulfill({ contentType: 'text/html', body: `<body><div id="wrap">${composeHtml({ split: true })}</div></body>` }));
    const sw = ctx.serviceWorkers()[0] || (await ctx.waitForEvent('serviceworker', { timeout: 15000 }));
    check('extension loaded with the pinned id', sw.url().startsWith('chrome-extension://mabkbpnhmakajgmgpcehigllechcaehb/'), sw.url());

    const page = await ctx.newPage();
    await page.goto('https://mail.google.com/mail/u/0/');
    await page.waitForSelector('.plume-btn', { timeout: 10000 });
    check('exactly one button per compose', (await page.$$('.plume-btn')).length === 1);

    await page.click('.plume-btn', { modifiers: ['Alt'] });
    let dry = await page.waitForSelector('.plume-toast', { timeout: 10000 });
    const dryText = await dry.textContent();
    check('Alt-click is a dry run that lists To, Cc, Bcc without sending',
      /dry run/.test(dryText) && /To: dev@apache.org, bob@example.org/.test(dryText) && /Cc: carol@example.org/.test(dryText) && /Bcc: -/.test(dryText), JSON.stringify(dryText));
    await page.evaluate(() => document.querySelectorAll('.plume-toast').forEach((e) => e.remove()));

    await page.click('.plume-btn'); // no address configured yet
    let toast = await page.waitForSelector('.plume-toast', { timeout: 10000 });
    let text = await toast.textContent();
    check('unconfigured address is reported', /options/.test(text), text);
    await page.evaluate(() => document.querySelectorAll('.plume-toast').forEach((e) => e.remove()));

    await sw.evaluate(() => chrome.storage.local.set({ from: 'me@apache.org' }));
    await page.click('.plume-btn');
    toast = await page.waitForSelector('.plume-toast', { timeout: 15000 });
    text = await toast.textContent();
    check('draft reached the Python host and the relay error came back', /relay failure.*(refused|Errno 111)/i.test(text), text);
    check('button is usable again after a failed send', await page.$eval('.plume-btn', (b) => !b.disabled));

    // Success path: answer the way the host does when the relay accepts the mail. The real relay is not reachable here.
    await sw.evaluate(() => { chrome.runtime.sendNativeMessage = async () => { await new Promise((r) => setTimeout(r, 400)); return { ok: true, messageId: '<e2e@apache.org>', archived: false, relayResponse: '250 2.0.0 Ok: queued as E2E42', relaySeconds: 0.4 }; }; });
    await page.evaluate(() => document.querySelectorAll('.plume-toast').forEach((e) => e.remove()));
    let sawSending = false;
    const label = page.waitForFunction(() => document.querySelector('.plume-btn') && document.querySelector('.plume-btn').textContent === 'Sending…', null, { timeout: 3000 }).then(() => { sawSending = true; }).catch(() => {});
    await page.click('.plume-btn');
    // The subject starts with "Re:", but the mock page has no thread to read. The mail is still sent, with a visible warning about threading.
    const warn = await page.waitForSelector('.plume-toast-warn', { timeout: 10000 });
    const warnText = await warn.textContent();
    await label;
    check('a reply that could not be threaded is sent with an amber warning',
      /✓ Sent as me@apache.org/.test(warnText) && /Not threaded for list readers/.test(warnText), JSON.stringify(warnText));
    check('the button shows Sending… while working', sawSending);
    check('the button gets its label back afterwards', (await page.$eval('.plume-btn', (b) => b.textContent)) === 'Send as apache.org');
    await page.evaluate(() => document.querySelectorAll('.plume-toast').forEach((e) => e.remove()));

    await page.evaluate(() => { document.querySelector('input[name="subjectbox"]').value = 'plain subject'; });
    await page.click('.plume-btn');
    const ok = await page.waitForSelector('.plume-toast-success', { timeout: 10000 });
    const okText = await ok.textContent();
    check('success is a prominent green notification naming the sender, recipients and relay',
      /✓ Sent as me@apache.org/.test(okText) && /To: dev@apache.org, bob@example.org/.test(okText) && /Cc: carol@example.org/.test(okText) && /Accepted by the ASF mail relay in 0.4 s/.test(okText) && /Relay reply: 250 2.0.0 Ok: queued as E2E42/.test(okText), JSON.stringify(okText));
    await page.click('.plume-toast-success'); // click dismisses
    check('a notification is dismissed by clicking it', (await page.$$('.plume-toast-success')).length === 0);

    const log = (await sw.evaluate(() => chrome.storage.local.get('history'))).history;
    check('every send attempt is logged, newest first, without the message text',
      log.length >= 3 && log[0].ok === true && log[0].relayResponse === '250 2.0.0 Ok: queued as E2E42' && log.some((e) => !e.ok && /relay failure/.test(e.error)) && !JSON.stringify(log).includes('thanks'),
      `entries=${log.length}`);
    const opts = await ctx.newPage();
    await opts.goto(`chrome-extension://mabkbpnhmakajgmgpcehigllechcaehb/src/options.html`);
    await opts.waitForSelector('#history tbody tr');
    const rows = await opts.$$eval('#history tbody tr', (trs) => trs.map((tr) => tr.textContent));
    check('the options page lists the recent sends with their outcome', rows.length >= 3 && /✓ sent/.test(rows[0]) && /queued as E2E42/.test(rows[0]) && rows.some((r) => /✗ not sent/.test(r)), rows[0]);
    await opts.close();

    // A second compose in the same container changes how far the first one's root is widened.
    // That must not put a second button next to the first compose's Send button.
    const second = composeHtml({ split: true, subject: 'other' });
    await page.evaluate((html) => document.getElementById('wrap').insertAdjacentHTML('beforeend', html), second);
    await page.waitForFunction(() => document.querySelectorAll('.plume-btn').length >= 2, null, { timeout: 5000 });
    await page.waitForTimeout(500);
    const count = (await page.$$('.plume-btn')).length;
    check('one button per compose after a second compose appears', count === 2, `count=${count}`);
    const valid = await page.evaluate(() => [...document.querySelectorAll('.plume-btn')].every((b) => b.parentElement.tagName !== 'TR'));
    check('the button is never a direct child of a table row', valid);
  } finally {
    await ctx.close();
    fs.rmSync(home, { recursive: true, force: true });
  }
  process.exit(results.every(Boolean) ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(1); });
