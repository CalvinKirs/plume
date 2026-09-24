const test = require('node:test');
const assert = require('node:assert');
const { page } = require('./fixtures');
const { domToText } = require('../src/dom-text');

const text = (html) => domToText(page(`<div id="b">${html}</div>`).getElementById('b'));

test('divs and br become lines, blank div becomes a blank line', () => {
  assert.strictEqual(text('<div>one</div><div><br></div><div>two</div>'), 'one\n\ntwo');
});

test('quoted reply is prefixed with > and nested quotes stack', () => {
  const out = text('<div>reply</div><div class="gmail_quote"><div>On Mon, A wrote:</div><blockquote><div>q1</div><blockquote><div>deep</div></blockquote></blockquote></div>');
  assert.strictEqual(out, 'reply\nOn Mon, A wrote:\n> q1\n> > deep');
});

test('nbsp and zero-width characters are cleaned, inline tags stay inline', () => {
  assert.strictEqual(text('a&nbsp;<b>b</b>​ <a href="x">c</a>'), 'a b c');
});
