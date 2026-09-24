// Real Chromium + the real extension + a mock Gmail page + the real native host (source launcher).
// Gmail's own markup is NOT exercised here (see docs/selectors.md): this covers the wiring
// content script -> background -> native messaging -> Python host.
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

// Register the host into the throwaway profile and point the relay at a closed port.
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

    // A second compose in the same container changes how far the first one's root widens.
    // That must not stack a second button on the first compose's Send button.
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
