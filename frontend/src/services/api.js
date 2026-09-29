/**
 * API Client & WebSocket Service
 * Part of: ML-Enhanced SDN Emergency Communication Network
 */

const API_BASE = '/api';

/**
 * Fetch helper that throws on non-2xx responses with the backend error detail.
 */
async function fetchJSON(url, options) {
  const r = await fetch(url, options);
  if (!r.ok) {
    let detail = `HTTP ${r.status}`;
    try {
      const body = await r.json();
      detail = body.detail || JSON.stringify(body);
    } catch (_) {}
    const err = new Error(detail);
    err.status = r.status;
    throw err;
  }
  return r.json();
}

export const api = {
  getStatus: () => fetchJSON(`${API_BASE}/status`),
  getTopology: () => fetchJSON(`${API_BASE}/topology`),
  getNodes: () => fetchJSON(`${API_BASE}/nodes`),
  getLinks: () => fetchJSON(`${API_BASE}/links`),
  getRoutes: () => fetchJSON(`${API_BASE}/routes`),
  getNetworkStats: () => fetchJSON(`${API_BASE}/network-stats`),
  getMLPredictions: () => fetchJSON(`${API_BASE}/ml/prediction`),
  getMLInfo: () => fetchJSON(`${API_BASE}/ml/info`),
  getEvents: (limit = 50) => fetchJSON(`${API_BASE}/events?limit=${limit}`),
  getMessages: (limit = 20) => fetchJSON(`${API_BASE}/messages/history?limit=${limit}`),
  getOpenFlowRules: () => fetchJSON(`${API_BASE}/openflow/rules`),
  getComparison: (source = 'Security', destination = 'Medical') =>
    fetchJSON(`${API_BASE}/routing/compare?source=${encodeURIComponent(source)}&destination=${encodeURIComponent(destination)}`),

  sendMessage: (payload) =>
    fetchJSON(`${API_BASE}/messages/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  failLink: (source, target) =>
    fetchJSON(`${API_BASE}/links/fail`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source, target }),
    }),

  restoreLink: (source, target) =>
    fetchJSON(`${API_BASE}/links/restore`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source, target }),
    }),

  addNode: (node) =>
    fetchJSON(`${API_BASE}/topology/node`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(node),
    }),

  deleteNode: (id) =>
    fetchJSON(`${API_BASE}/topology/node/${id}`, { method: 'DELETE' }),

  addLink: (link) =>
    fetchJSON(`${API_BASE}/topology/link`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(link),
    }),

  deleteLink: (id) =>
    fetchJSON(`${API_BASE}/topology/link/${id}`, { method: 'DELETE' }),

  updateLink: (payload) =>
    fetchJSON(`${API_BASE}/topology/link/update`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  recalculateRoute: (source, destination, mlAdjusted = true) =>
    fetchJSON(`${API_BASE}/routing/recalculate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source, destination, ml_adjusted: mlAdjusted }),
    }),

  runScenario: () =>
    fetchJSON(`${API_BASE}/scenario/run`, { method: 'POST' }),

  setTrafficLevel: (level) =>
    fetchJSON(`${API_BASE}/traffic/set-level`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ level }),
    }),

  resetTopology: () =>
    fetchJSON(`${API_BASE}/topology/reset`, { method: 'POST' }),
};
