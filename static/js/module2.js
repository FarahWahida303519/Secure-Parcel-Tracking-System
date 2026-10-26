'use strict';
// YOUR MODULE 2: registration and public tracking.
// M2 SECURITY: dynamic values are rendered with textContent, never innerHTML.
// Search/list/details are server-rendered with Jinja automatic HTML escaping.
bindForm('#parcel-form', async (form, data) => {
  const parcel = await api('/api/parcels', {
    method: 'POST', body: Object.fromEntries(data)
  });
  form.reset();
  const result = $('#registration-result');
  result.replaceChildren();
  const panel = document.createElement('div');
  panel.className = 'registration-success';
  const title = document.createElement('h2');
  title.textContent = 'Your parcel is ready for its journey.';
  const number = document.createElement('strong');
  number.textContent = parcel.tracking;
  const copy = document.createElement('button');
  copy.type = 'button';
  copy.className = 'button secondary';
  copy.textContent = 'Copy tracking number';
  copy.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(parcel.tracking);
      toast('Tracking number copied.');
    } catch { toast('Select the tracking number to copy it.'); }
  });
  const detail = document.createElement('a');
  detail.className = 'button';
  detail.href = '/parcels/' + encodeURIComponent(parcel.id);
  detail.textContent = 'View parcel ↗';
  panel.append(title, number, copy, document.createTextNode(' '), detail);
  result.append(panel);
});

bindForm('#track-form', async (form, data) => {
  const result = $('#tracking-result');
  result.replaceChildren();
  try {
    const response = await api('/api/track?number=' + encodeURIComponent(data.get('number').trim()));
    const list = document.createElement('ol');
    list.className = 'timeline';
    for (const event of response.history) {
      const item = document.createElement('li');
      const status = document.createElement('strong');
      status.textContent = event.status;
      const timestamp = document.createElement('time');
      timestamp.dateTime = event.created;
      timestamp.textContent = new Date(event.created).toLocaleString('en-MY', {
        dateStyle: 'medium', timeStyle: 'short'
      });
      item.append(status, timestamp);
      list.append(item);
    }
    result.append(list);
  } catch (error) {
    const message = document.createElement('p');
    message.className = 'error-inline';
    message.textContent = error.message;
    result.append(message);
  }
});
