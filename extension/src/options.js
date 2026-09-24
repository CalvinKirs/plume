const $ = (id) => document.getElementById(id);

Plume.settings.loadSettings(chrome.storage.local).then((s) => {
  $('from').value = s.from;
  $('fromName').value = s.fromName;
  $('mode').value = s.mode;
  $('token').value = s.token;
  $('port').value = s.port;
});

$('save').addEventListener('click', async () => {
  await Plume.settings.saveSettings(chrome.storage.local, {
    from: $('from').value.trim(), fromName: $('fromName').value.trim(), mode: $('mode').value, token: $('token').value.trim(), port: Number($('port').value) || 8765,
  });
  $('status').textContent = 'Saved';
  setTimeout(() => ($('status').textContent = ''), 2000);
});

// Recent sends
function cell(row, text, cls) {
  const td = document.createElement('td');
  td.textContent = text;
  if (cls) td.className = cls;
  row.appendChild(td);
  return td;
}

async function renderHistory() {
  const list = await Plume.history.load(chrome.storage.local);
  const body = $('history').querySelector('tbody');
  body.textContent = '';
  for (const e of list) {
    const row = document.createElement('tr');
    cell(row, new Date(e.at).toLocaleString());
    cell(row, e.ok ? '✓ sent' : '✗ not sent', e.ok ? 'ok' : 'bad');
    const all = [...e.to, ...e.cc.map((a) => 'Cc ' + a), ...e.bcc.map((a) => 'Bcc ' + a)];
    cell(row, all.join(', ') || '-');
    cell(row, e.subject || '(no subject)');
    const relay = e.ok
      ? [e.relayResponse, e.relaySeconds == null ? null : e.relaySeconds + ' s', e.messageId].filter(Boolean).join('\n')
      : e.error;
    const td = cell(row, relay || '', e.ok ? 'dim' : 'bad');
    td.style.whiteSpace = 'pre-line';
    body.appendChild(row);
  }
  $('history').hidden = $('clear').hidden = list.length === 0;
  $('empty').hidden = list.length !== 0;
}

$('clear').addEventListener('click', async () => {
  await Plume.history.clear(chrome.storage.local);
  renderHistory();
});
chrome.storage.onChanged.addListener((changes) => { if (changes.history) renderHistory(); });
renderHistory();
