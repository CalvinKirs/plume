const recent = document.getElementById('recent');
const empty = document.getElementById('empty');

Plume.history.load(Plume.api.storage.local).then((entries) => {
  for (const entry of entries.slice(0, 5)) {
    const item = document.createElement('li');
    const row = document.createElement('div');
    row.className = 'row';
    const subject = document.createElement('span');
    subject.className = 'subject';
    subject.textContent = entry.subject || '(no subject)';
    const status = document.createElement('span');
    status.className = `status ${entry.ok ? 'ok' : 'bad'}`;
    status.textContent = entry.ok ? '✓ sent' : '✗ not sent';
    row.append(subject, status);
    const details = document.createElement('div');
    details.className = 'details';
    const recipients = [
      ...(entry.to || []),
      ...(entry.cc || []).map((address) => `Cc ${address}`),
      ...(entry.bcc || []).map((address) => `Bcc ${address}`),
    ];
    details.textContent = `${new Date(entry.at).toLocaleString()} · ${recipients.join(', ') || '-'}`;
    item.append(row, details);
    recent.appendChild(item);
  }
  empty.hidden = entries.length !== 0;
});

document.getElementById('settings').addEventListener('click', () => Plume.api.runtime.openOptionsPage());
