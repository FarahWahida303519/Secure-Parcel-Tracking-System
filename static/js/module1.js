'use strict';
// MEMBER 1: authentication and user management only.
bindForm('#login-form', async (form, data) => {
  await api('/api/login', { method: 'POST', body: Object.fromEntries(data) });
  window.location.assign('/');
});

bindForm('#register-form', async (form, data) => {
  await api('/api/register', { method: 'POST', body: Object.fromEntries(data) });
  window.location.assign('/login');
});

bindForm('#password-form', async (form, data) => {
  await api('/api/password', { method: 'POST', body: Object.fromEntries(data) });
  window.location.assign('/login');
});

bindForm('#rider-form', async (form, data) => {
  await api('/api/users', { method: 'POST', body: Object.fromEntries(data) });
  window.location.reload();
});

$('#logout')?.addEventListener('click', async () => {
  try {
    await api('/api/logout', { method: 'POST' });
    window.location.assign('/');
  } catch (error) { toast(error.message, true); }
});

document.querySelectorAll('[data-toggle]').forEach(button => {
  button.addEventListener('click', async () => {
    button.disabled = true;
    try {
      await api(`/api/users/${button.dataset.toggle}/toggle`, { method: 'POST' });
      window.location.reload();
    } catch (error) { toast(error.message, true); button.disabled = false; }
  });
});
