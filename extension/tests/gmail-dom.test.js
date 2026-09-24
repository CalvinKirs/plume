const test = require('node:test');
const assert = require('node:assert');
const { composeHtml, page } = require('./fixtures');
const gmail = require('../src/gmail-dom');

require('../src/dom-text');

test('finds a compose and reads recipients, subject and body', () => {
  const doc = page(composeHtml());
  const [compose] = gmail.findComposeWindows(doc);
  const d = gmail.readDraft(compose);
  assert.deepStrictEqual(d.to, ['dev@apache.org', 'bob@example.org']);
  assert.deepStrictEqual(d.cc, ['carol@example.org']);
  assert.deepStrictEqual(d.bcc, []);
  assert.strictEqual(d.subject, 'Re: [VOTE] release');
  assert.strictEqual(d.text, '+1\n\nthanks');
});

test('works with a Chinese UI (labels differ, classes do not)', () => {
  // Chinese interface: the labels for "Send" and "Discard draft", written as Unicode escapes.
  const doc = page(composeHtml({ send: '\u53d1\u9001', discard: '\u653e\u5f03\u8349\u7a3f' }));
  const [compose] = gmail.findComposeWindows(doc);
  assert.ok(gmail.findSendButton(compose));
  assert.ok(gmail.findDiscardButton(compose));
});

test('two composes are told apart', () => {
  const doc = page(composeHtml() + composeHtml({ subject: 'other' }));
  const composes = gmail.findComposeWindows(doc);
  assert.strictEqual(composes.length, 2);
  assert.strictEqual(gmail.readDraft(composes[1]).subject, 'other');
});

test('anchor is the send button cell; a bodyless page has no compose', () => {
  const [compose] = gmail.findComposeWindows(page(composeHtml()));
  assert.strictEqual(gmail.buttonAnchor(compose).tagName, 'TD');
  assert.deepStrictEqual(gmail.findComposeWindows(page('<div>inbox</div>')), []);
});

test('recipient and subject rows outside the body+send container are still part of the compose', () => {
  const doc = page(composeHtml({ split: true }));
  const [compose] = gmail.findComposeWindows(doc);
  const d = gmail.readDraft(compose);
  assert.deepStrictEqual(d.to, ['dev@apache.org', 'bob@example.org']);
  assert.strictEqual(d.subject, 'Re: [VOTE] release');
  assert.strictEqual(d.text, '+1\n\nthanks');
});

test('widening never merges two composes or climbs out of the main region', () => {
  const doc = page(composeHtml({ split: true }) + composeHtml({ split: true, subject: 'other' }));
  const composes = gmail.findComposeWindows(doc);
  assert.strictEqual(composes.length, 2);
  assert.strictEqual(gmail.readDraft(composes[1]).subject, 'other');
  assert.strictEqual(gmail.readDraft(composes[0]).subject, 'Re: [VOTE] release');
  const inMain = page(`<div role="main">${composeHtml({ split: true })}</div>`);
  const [c] = gmail.findComposeWindows(inMain);
  assert.notStrictEqual(c.getAttribute('role'), 'main');
});

test('body: the first editor with text wins, textarea copies are a fallback, empty stays empty', () => {
  const doc = page('<div id="c"><div role="textbox" g_editable="true"></div><div role="textbox" aria-label="Message Body"><div>real text</div></div><textarea aria-label="Message Body">copy</textarea></div>');
  const c = doc.getElementById('c');
  assert.strictEqual(gmail.readBodyText(c), 'real text');
  assert.strictEqual(gmail.bodyCandidates(c), 3);

  const onlyTextarea = page('<div id="c"><div role="textbox" g_editable="true"><div><br></div></div><textarea aria-label="Message Body">line1\r\nline2</textarea></div>').getElementById('c');
  assert.strictEqual(gmail.readBodyText(onlyTextarea), 'line1\nline2');

  const empty = page('<div id="c"><div role="textbox" g_editable="true"><div><br></div></div><textarea aria-label="Message Body"></textarea></div>').getElementById('c');
  assert.strictEqual(gmail.readBodyText(empty), '');
});

// jsdom has no layout, so visibility is decided by an attribute in these tests.
const shown = (el) => !el.hasAttribute('data-hidden');

test('body fallback: the visible editor nearest the button is read, hidden decoys are skipped', () => {
  const doc = page(`
    <div id="a"><div role="textbox" g_editable="true" data-hidden="1">decoy</div></div>
    <div id="b"><div role="textbox" g_editable="true"><div>real text</div></div><div role="button" id="send" class="aoO">Send</div></div>`);
  assert.strictEqual(gmail.readBodyNear(doc.getElementById('send'), shown), 'real text');
});

test('body fallback: an empty compose does not pick up the text of another open draft', () => {
  const doc = page(`
    <div id="a"><div role="textbox" g_editable="true"><div>other draft</div></div></div>
    <div id="b"><div role="textbox" g_editable="true"><div><br></div></div><div role="button" id="send" class="aoO">Send</div></div>`);
  assert.strictEqual(gmail.readBodyNear(doc.getElementById('send'), shown), '');
});

test('body fallback: no visible editor gives an empty string, and the editors are described', () => {
  const doc = page('<div role="textbox" g_editable="true" data-hidden="1">x</div><div role="button" id="send" class="aoO"></div>');
  assert.strictEqual(gmail.readBodyNear(doc.getElementById('send'), shown), '');
  assert.match(gmail.describeEditors(doc, shown), /1 editor\(s\) on the page, 0 visible, text length of each: hidden 1/);
});
