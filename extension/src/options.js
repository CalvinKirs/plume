const $ = (id) => document.getElementById(id);

Plume.settings.loadSettings(chrome.storage.local).then((s) => {
  $('from').value = s.from;
  $('mode').value = s.mode;
  $('token').value = s.token;
  $('port').value = s.port;
});

$('save').addEventListener('click', async () => {
  await Plume.settings.saveSettings(chrome.storage.local, {
    from: $('from').value.trim(), mode: $('mode').value, token: $('token').value.trim(), port: Number($('port').value) || 8765,
  });
  $('status').textContent = 'Saved';
  setTimeout(() => ($('status').textContent = ''), 2000);
});
