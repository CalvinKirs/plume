// All Gmail-specific selectors live in this file. When Gmail changes its markup, this is the
// only place that needs to change (see docs/selectors.md).
(function (root) {
  const P = (root.Plume = root.Plume || {});

  // The class .aoO marks Gmail's Send button and does not depend on the interface language.
  // The label matches cover the English and Chinese interfaces. The Chinese labels are written as
  // Unicode escapes: \u53d1\u9001 is "Send" and \u653e\u5f03 is "Discard".
  const SEND = [
    '.aoO[role="button"]',
    '[role="button"][data-tooltip^="Send"]', '[role="button"][aria-label^="Send"]',
    '[role="button"][data-tooltip^="\u53d1\u9001"]', '[role="button"][aria-label^="\u53d1\u9001"]',
  ].join(',');
  const BODY = 'div[role="textbox"][g_editable="true"], div[role="textbox"][aria-label="Message Body"]';
  // Gmail keeps a hidden textarea copy of the body, and plain-text mode uses a textarea as the editor.
  const BODY_TEXTAREA = 'textarea[aria-label="Message Body"], textarea[name="body"]';
  const SUBJECT = 'input[name="subjectbox"]';
  const DISCARD = [
    '.og[role="button"]',
    '[role="button"][data-tooltip^="Discard"]', '[role="button"][aria-label^="Discard"]',
    '[role="button"][data-tooltip^="\u653e\u5f03"]', '[role="button"][aria-label^="\u653e\u5f03"]',
  ].join(',');

  const ADDRESS = /[^\s<>,;"']+@[^\s<>,;"']+/g;

  function emailsIn(text) {
    return (text || '').match(ADDRESS) || [];
  }

  function recipients(compose, field) {
    const found = [];
    compose.querySelectorAll(`input[name="${field}"], textarea[name="${field}"]`)
      .forEach((el) => found.push(...emailsIn(el.value)));
    compose.querySelectorAll(`[name="${field}"] [email], [name="${field}"] [data-hovercard-id]`)
      .forEach((el) => found.push(...emailsIn(el.getAttribute('email') || el.getAttribute('data-hovercard-id'))));
    const seen = new Set();
    return found.filter((a) => {
      const k = a.toLowerCase();
      return seen.has(k) ? false : (seen.add(k), true);
    });
  }

  const MAX_WIDEN = 12;

  // A compose window starts as the smallest ancestor of a message body that also contains a Send
  // button. It is then widened as long as the parent contains only this one body, because the
  // recipient and subject rows are often siblings of that ancestor rather than inside it.
  function findComposeWindows(scope) {
    const composes = [];
    scope.querySelectorAll(BODY).forEach((body) => {
      let el = body.parentElement;
      while (el && !el.querySelector(SEND)) el = el.parentElement;
      if (!el) return;
      for (let i = 0; i < MAX_WIDEN; i++) {
        const parent = el.parentElement;
        if (!parent || parent.tagName === 'BODY' || parent.getAttribute('role') === 'main') break;
        if (parent.querySelectorAll(BODY).length !== 1) break;
        el = parent;
      }
      if (!composes.includes(el)) composes.push(el);
    });
    return composes;
  }

  const findBody = (c) => c.querySelector(BODY);
  const bodyCandidates = (c) => c.querySelectorAll(BODY).length + c.querySelectorAll(BODY_TEXTAREA).length;

  // Rich editors come first. A textarea copy is only a fallback, used when no editor has any text.
  function readBodyText(compose) {
    for (const el of compose.querySelectorAll(BODY)) {
      const text = P.domToText(el);
      if (text.trim()) return text;
    }
    for (const el of compose.querySelectorAll(BODY_TEXTAREA)) {
      if (el.value && el.value.trim()) return el.value.replace(/\r\n/g, '\n');
    }
    return '';
  }
  const findSendButton = (c) => c.querySelector(SEND);
  const findDiscardButton = (c) => c.querySelector(DISCARD);

  function readDraft(compose) {
    const subject = compose.querySelector(SUBJECT);
    return {
      to: recipients(compose, 'to'),
      cc: recipients(compose, 'cc'),
      bcc: recipients(compose, 'bcc'),
      subject: subject ? subject.value : '',
      text: readBodyText(compose),
    };
  }

  const isShown = (el) => el.getClientRects().length > 0;

  // Number of ancestors that a and b share, counted from the document root down.
  function sharedDepth(a, b) {
    const ancestors = [];
    for (let n = a; n; n = n.parentNode) ancestors.push(n);
    for (let n = b; n; n = n.parentNode) {
      const i = ancestors.indexOf(n);
      if (i >= 0) return ancestors.length - i;
    }
    return 0;
  }

  // Fallback for a compose root that holds no text: the text of the visible editor closest to the
  // button in the document tree. The closest editor is used even when it is empty, so that an
  // empty compose never sends the text of another draft that happens to be open.
  function readBodyNear(button, isVisible = isShown) {
    let best = null;
    let bestDepth = -1;
    for (const el of button.ownerDocument.querySelectorAll(BODY)) {
      if (!isVisible(el)) continue;
      const depth = sharedDepth(button, el);
      if (depth > bestDepth) {
        best = el;
        bestDepth = depth;
      }
    }
    if (!best) return '';
    return P.domToText(best) || (best.innerText || '').trim();
  }

  // A short description of the editors on the page, for the message shown when no text was found.
  function describeEditors(doc, isVisible = isShown) {
    const editors = [...doc.querySelectorAll(BODY)];
    const shown = editors.filter(isVisible);
    const lengths = editors.map((el) => (isVisible(el) ? '' : 'hidden ') + P.domToText(el).length);
    return `${editors.length} editor(s) on the page, ${shown.length} visible, text length of each: ${lengths.join(', ') || 'none'}`;
  }

  // The button goes right after the toolbar cell that holds the Send button.
  function buttonAnchor(compose) {
    const send = findSendButton(compose);
    return send ? send.closest('td') || send.parentElement : null;
  }

  P.gmail = { findComposeWindows, findBody, bodyCandidates, readBodyText, readBodyNear, describeEditors, findSendButton, findDiscardButton, readDraft, buttonAnchor, recipients };
  if (typeof module !== 'undefined') module.exports = P.gmail;
})(typeof globalThis !== 'undefined' ? globalThis : this);
