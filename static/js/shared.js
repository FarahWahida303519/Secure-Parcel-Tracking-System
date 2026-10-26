'use strict';
// Group-owned request and presentation utilities. No module business logic here.
const $ = selector => document.querySelector(selector);
const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
let toastTimer;

function toast(message, error = false) {
  const node = $('#toast');
  node.textContent = message;
  node.className = error ? 'visible error' : 'visible';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { node.className = ''; }, 5000);
}

async function api(path, options = {}) {
  const headers = { 'X-CSRF-Token': csrf, ...options.headers };
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }
  const response = await fetch(path, { ...options, headers });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Please try again.');
  return data;
}

// All forms release their submit button on failure and display a safe text error.
function bindForm(selector, handler) {
  const form = $(selector);
  if (!form) return;
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const button = form.querySelector('button[type="submit"],button:not([type])');
    if (button) button.disabled = true;
    try {
      await handler(form, new FormData(form));
    } catch (error) {
      toast(error.message, true);
    } finally {
      if (button) button.disabled = false;
    }
  });
}
