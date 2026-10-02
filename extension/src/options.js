const $ = (id) => document.getElementById(id);

Plume.settings.loadSettings(Plume.api.storage.local).then((s) => {
  $('from').value = s.from;
  $('fromName').value = s.fromName;
  $('mode').value = s.mode;
  $('token').value = s.token;
  $('port').value = s.port;
});

$('save').addEventListener('click', async () => {
  await Plume.settings.saveSettings(Plume.api.storage.local, {
    from: $('from').value.trim(), fromName: $('fromName').value.trim(), mode: $('mode').value, token: $('token').value.trim(), port: Number($('port').value) || 8765,
  });
  $('status').textContent = 'Saved';
  setTimeout(() => ($('status').textContent = ''), 2000);
});
