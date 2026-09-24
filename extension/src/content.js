// Glue code: finds compose windows, adds the button, sends the draft and shows the result.
// The real logic lives in the other modules.
(function () {
  const { gmail, replyContext } = Plume;
  const sending = new WeakSet();

  const HOLD_MS = { success: 12000, warn: 14000, error: 15000, info: 6000 };

  // kind is one of success, warn, error or info. Clicking a notification dismisses it.
  function notify(kind, title, detail, ms) {
    let box = document.getElementById('plume-toasts');
    if (!box) {
      box = document.createElement('div');
      box.id = 'plume-toasts';
      document.body.appendChild(box);
    }
    const el = document.createElement('div');
    el.className = `plume-toast plume-toast-${kind}`;
    el.title = 'Click to dismiss';
    const head = document.createElement('div');
    head.className = 'plume-toast-title';
    head.textContent = title;
    el.appendChild(head);
    if (detail) {
      const body = document.createElement('div');
      body.className = 'plume-toast-detail';
      body.textContent = detail;
      el.appendChild(body);
    }
    el.addEventListener('click', () => el.remove());
    box.appendChild(el);
    setTimeout(() => el.remove(), ms || HOLD_MS[kind]);
  }

  const list = (a) => (a.length ? a.join(', ') : '-');

  async function onClick(compose, button, dryRun) {
    if (sending.has(button)) return; // Ignore clicks while a send is running, so nothing is sent twice.
    sending.add(button);
    const label = button.textContent;
    button.textContent = 'Sending…';
    button.disabled = true;
    try {
      const draft = gmail.readDraft(compose);
      if (!draft.to.length && !draft.cc.length && !draft.bcc.length) {
        return notify('error', 'Plume: nothing sent, no recipients found',
          'Add at least one recipient. In an inline reply, click the recipient line to expand it. (Or Gmail\'s layout changed.)');
      }
      if (!draft.text.trim()) {
        return notify('error', 'Plume: nothing sent, the message body reads as empty',
          `${gmail.bodyCandidates(compose)} editor(s) found. Type some text. (Or Gmail's layout changed.)`);
      }
      // Matches "Re:" in English and the Chinese equivalents (\u56de\u590d and \u7b54\u590d, both meaning
      // "reply"), followed by an ASCII colon or the full-width one (\uff1a).
      const isReply = /^\s*(re|\u56de\u590d|\u7b54\u590d)\s*[:\uff1a]/i.test(draft.subject);
      const found = isReply ? await replyContext.fetchReplyContext(document, location, fetch.bind(window)) : { ctx: null, reason: null };
      const ctx = found.ctx;
      if (dryRun) { // Option or Alt click: show what would be sent, without sending it.
        console.log('[Plume dry run]', { draft, ctx });
        return notify('info', 'Plume dry run: nothing was sent',
          `To: ${list(draft.to)}\nCc: ${list(draft.cc)}\nBcc: ${list(draft.bcc)}\nSubject: ${draft.subject}\nBody: ${draft.text.length} characters\nReply headers: ${isReply ? (ctx ? 'found, thread ' + ctx.threadId : 'NOT found: ' + found.reason) : 'not a reply'}`, 30000);
      }
      const res = await chrome.runtime.sendMessage({ type: 'plume:send', draft, ctx });
      if (!res || !res.ok) {
        return notify('error', 'Plume: NOT sent', (res && res.error) || 'The extension gave no answer.');
      }
      const lines = [`To: ${list(draft.to)}`];
      if (draft.cc.length) lines.push(`Cc: ${list(draft.cc)}`);
      if (draft.bcc.length) lines.push(`Bcc: ${list(draft.bcc)}`);
      lines.push('Accepted by the ASF mail relay' + (res.relaySeconds == null ? '.' : ` in ${res.relaySeconds} s.`));
      if (res.relayResponse) lines.push(`Relay reply: ${res.relayResponse}`);
      const problems = [];
      if (isReply && !ctx) problems.push(`Not threaded for list readers: reply headers unavailable (${found.reason}).`);
      if (!res.archived) {
        lines.push(res.archiveError ? `No copy in Gmail Sent: ${res.archiveError}` : 'No copy in Gmail Sent (write-back is not set up).');
      }
      const discard = gmail.findDiscardButton(compose);
      if (discard) discard.click(); else lines.push('Close this draft manually.');
      notify(problems.length ? 'warn' : 'success', `✓ Sent as ${res.from}`, lines.concat(problems).join('\n'));
    } catch (e) {
      // Report every error. An exception here used to leave the click looking dead.
      const m = String((e && e.message) || e);
      const stale = /context invalidated|Receiving end|message port closed/i.test(m);
      notify('error', 'Plume: NOT sent', stale ? 'The extension was reloaded or updated. Refresh this Gmail tab and try again.' : m);
    } finally {
      sending.delete(button);
      button.textContent = label;
      button.disabled = false;
    }
  }

  // Each Send button gets exactly one Plume button. The compose root can grow or shrink as the
  // page changes, so the marker sits on the anchor and the root is looked up again on click.
  function decorate(compose) {
    const anchor = gmail.buttonAnchor(compose);
    if (!anchor || anchor.dataset.plume) return;
    anchor.dataset.plume = '1';
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'plume-btn';
    button.textContent = 'Send as apache.org';
    button.addEventListener('click', (e) => {
      const current = gmail.findComposeWindows(document).find((c) => c.contains(button)) || compose;
      onClick(current, button, e.altKey);
    });
    // In a toolbar row the button needs its own cell. Elsewhere a plain wrapper is enough.
    const host = document.createElement(anchor.tagName === 'TD' ? 'td' : 'span');
    host.className = 'plume-host';
    host.appendChild(button);
    anchor.insertAdjacentElement('afterend', host);
  }

  const scan = () => gmail.findComposeWindows(document).forEach(decorate);
  let queued = false;
  new MutationObserver(() => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; scan(); });
  }).observe(document.body, { childList: true, subtree: true });
  scan();
})();
