// API helpers
(function () {
  const API_BASE = (location.protocol.startsWith('http'))
    ? `${location.protocol}//${location.hostname}:8000`
    : 'http://localhost:8000';

  function api(path) { return `${API_BASE}${path}`; }

  async function getPredictions() {
    const res = await fetch(api('/predictions'));
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  async function postTriage(payload) {
    const res = await fetch(api('/triage'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const text = await res.text().catch(() => '');
    let data;
    try { data = text ? JSON.parse(text) : {}; } catch { data = { detail: text || 'Unexpected response' }; }
    if (!res.ok) {
      const err = new Error((data && data.detail) ? data.detail : 'Request failed');
      err.response = data;
      throw err;
    }
    return data;
  }

  async function postLegacy(payload) {
    const res = await fetch(api('/predict'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  window.SekouAPI = { api, getPredictions, postTriage, postLegacy };
})();
