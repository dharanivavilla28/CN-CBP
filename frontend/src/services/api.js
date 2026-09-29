/**
 * API Client & WebSocket Service
 * Part of: ML-Enhanced SDN Emergency Communication Network
 */

const API_BASE = '/api';

export const api = {
  getStatus: () => fetch(`${API_BASE}/status`).then(r => r.json()),
  getTopology: () => fetch(`${API_BASE}/topology`).then(r => r.json()),
  getNodes: () => fetch(`${API_BASE}/nodes`).then(r => r.json()),
  getLinks: () => fetch(`${API_BASE}/links`).then(r => r.json()),
  getRoutes: () => fetch(`${API_BASE}/routes`).then(r => r.json()),
  getNetworkStats: () => fetch(`${API_BASE}/network-stats`).then(r => r.json()),
  getMLPredictions: () => fetch(`${API_BASE}/ml/prediction`).then(r => r.json()),
  getMLInfo: () => fetch(`${API_BASE}/ml/info`).then(r => r.json()),
  getEvents: (limit = 50) => fetch(`${API_BASE}/events?limit=${limit}`).then(r => r.json()),
  getMessages: (limit = 20) => fetch(`${API_BASE}/messages/history?limit=${limit}`).then(r => r.json()),
  getOpenFlowRules: () => fetch(`${API_BASE}/openflow/rules`).then(r => r.json()),
  getComparison: (source = 'Security', destination = 'Medical') => 
    fetch(`${API_BASE}/routing/compare?source=${encodeURIComponent(source)}&destination=${encodeURIComponent(destination)}`).then(r => r.json()),

  sendMessage: (payload) =>
    fetch(`${API_BASE}/messages/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(r => r.json()),

  failLink: (source, target) =>
    fetch(`${API_BASE}/links/fail`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source, target }),
    }).then(r => r.json()),

  restoreLink: (source, target) =>
    fetch(`${API_BASE}/links/restore`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source, target }),
    }).then(r => r.json()),

  addNode: (node) =>
    fetch(`${API_BASE}/topology/node`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(node),
    }).then(r => r.json()),

  deleteNode: (id) =>
    fetch(`${API_BASE}/topology/node/${id}`, { method: 'DELETE' }).then(r => r.json()),

  addLink: (link) =>
    fetch(`${API_BASE}/topology/link`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(link),
    }).then(r => r.json()),

  deleteLink: (id) =>
    fetch(`${API_BASE}/topology/link/${id}`, { method: 'DELETE' }).then(r => r.json()),

  updateLink: (payload) =>
    fetch(`${API_BASE}/topology/link/update`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(r => r.json()),

  recalculateRoute: (source, destination, mlAdjusted = true) =>
    fetch(`${API_BASE}/routing/recalculate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source, destination, ml_adjusted: mlAdjusted }),
    }).then(r => r.json()),

  runScenario: () =>
    fetch(`${API_BASE}/scenario/run`, { method: 'POST' }).then(r => r.json()),

  setTrafficLevel: (level) =>
    fetch(`${API_BASE}/traffic/set-level`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ level }),
    }).then(r => r.json()),

  resetTopology: () =>
    fetch(`${API_BASE}/topology/reset`, { method: 'POST' }).then(r => r.json()),
};
