'use strict';
// MEMBER 3: assignment and delivery status updates only.
bindForm('#assign-form', async (form, data) => {
  await api(`/api/parcels/${form.dataset.parcelId}/assign`, {
    method: 'POST', body: { rider_id: Number(data.get('rider_id')) }
  });
  window.location.reload();
});

bindForm('#status-form', async (form, data) => {
  await api(`/api/parcels/${form.dataset.parcelId}/status`, {
    method: 'POST', body: data
  });
  window.location.reload();
});
