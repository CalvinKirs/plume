// Thin glue: find compose windows, add the button, send, report. Logic lives in the other modules.
(function () {
  const { gmail, replyContext } = Plume;
  const sending = new WeakSet();

  function toast(text, isError, isWarn, ms) {
    const el = document.createElement('div');
    el.className = 'plume-toast' + (isError ? ' plume-toast-error' : '') + (isWarn ? ' plume-toast-warn' : '');
    el.textContent = text;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), ms || (isError ? 8000 : 4000));
  }

  const list = (a) => (a.length ? a.join(', ') : '-');

  async function onClick(compose, button, dryRun) {
    if (sending.has(button)) return; // never send twice
    sending.add(button);
    button.disabled = true;
    try {
      const draft = gmail.readDraft(compose);
      if (!draft.to.length && !draft.cc.length && !draft.bcc.length) {
        return toast('Plume: no recipients found (add one, or Gmail\'s layout changed).', true);
      }
      if (!draft.text.trim()) {
        return toast(`Plume: the message body reads as empty (${gmail.bodyCandidates(compose)} editor(s) found). Type some text, or Gmail's layout changed.`, true);
      }
      const isReply = /^\s*(re|\u56de\u590d|\u7b54\u590d)\s*[:\uff1a]/i.test(draft.subject);
      const found = isReply ? await replyContext.fetchReplyContext(document, location, fetch.bind(window)) : { ctx: null, reason: null };
      const ctx = found.ctx;
      if (dryRun) { // Option/Alt-click: show what would be sent, send nothing
        console.log('[Plume dry run]', { draft, ctx });
        return toast(`Plume dry run (nothing sent)\nTo: ${list(draft.to)}\nCc: ${list(draft.cc)}\nBcc: ${list(draft.bcc)}\nSubject: ${draft.subject}\nBody: ${draft.text.length} chars\nReply headers: ${isReply ? (ctx ? 'found, thread ' + ctx.threadId : 'NOT found: ' + found.reason) : 'not a reply'}`, false, false, 30000);
      }
      const res = await chrome.runtime.sendMessage({ type: 'plume:send', draft, ctx });
      if (!res || !res.ok) return toast('Plume: ' + ((res && res.error) || 'no answer from the extension'), true);
      const notes = [];
      if (isReply && !ctx) notes.push('reply headers unavailable: ' + found.reason);
      if (!res.archived) notes.push(res.archiveError ? 'no copy in Gmail Sent: ' + res.archiveError : 'no copy in Gmail Sent, write-back is not set up');
      const n = (a) => a.length;
      notes.unshift(`To ${n(draft.to)}, Cc ${n(draft.cc)}, Bcc ${n(draft.bcc)}`);
      toast('Plume: sent (' + notes.join('; ') + ')', false, notes.length > 1);
      const discard = gmail.findDiscardButton(compose);
      if (discard) discard.click(); else toast('Plume: sent. Close this draft manually.');
    } catch (e) {
      // Never fail silently: an error here used to leave the click looking dead.
      const m = String((e && e.message) || e);
      const stale = /context invalidated|Receiving end|message port closed/i.test(m);
      toast('Plume: ' + (stale ? 'the extension was reloaded or updated. Refresh this Gmail tab and try again.' : m), true);
    } finally {
      sending.delete(button);
      button.disabled = false;
    }
  }

  // One button per Send button, whatever compose root is computed: the root can grow or shrink
  // as the page changes, so the marker lives on the anchor and the root is looked up again on click.
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
    // Inside a toolbar row the button needs its own cell; anywhere else a plain wrapper does.
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
