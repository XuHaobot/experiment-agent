/**
 * Project API — Research Project / Question / Hypothesis / Next Experiment
 */

const BASE = '/api'

async function request(url, options = {}) {
  const r = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!r.ok) {
    const text = await r.text()
    throw new Error(text || r.statusText)
  }
  return r.json()
}

export const projectApi = {
  // === Project CRUD ===
  list: () => request(`${BASE}/projects`),
  get: (id) => request(`${BASE}/projects/${id}`),
  create: (body) => request(`${BASE}/projects`, { method: 'POST', body: JSON.stringify(body) }),
  update: (id, body) => request(`${BASE}/projects/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  delete: (id) => request(`${BASE}/projects/${id}`, { method: 'DELETE' }),

  // === Experiment 关联 ===
  addExperiment: (projectId, recordId) =>
    request(`${BASE}/projects/${projectId}/experiments/${recordId}`, { method: 'POST' }),
  removeExperiment: (projectId, recordId) =>
    request(`${BASE}/projects/${projectId}/experiments/${recordId}`, { method: 'DELETE' }),

  // === Research Question ===
  addQuestion: (projectId, text) =>
    request(`${BASE}/projects/${projectId}/questions`, { method: 'POST', body: JSON.stringify({ text }) }),
  deleteQuestion: (projectId, questionId) =>
    request(`${BASE}/projects/${projectId}/questions/${questionId}`, { method: 'DELETE' }),

  // === Hypothesis 建议 ===
  suggestHypotheses: (projectId, questionText) =>
    request(`${BASE}/projects/${projectId}/hypotheses/suggest`, {
      method: 'POST',
      body: JSON.stringify({ question_text: questionText }),
    }),

  // === Next Experiment ===
  getNextExperiment: (projectId, maxCandidates = 3) =>
    request(`${BASE}/projects/${projectId}/next-experiment?max_candidates=${maxCandidates}`),
  confirmNextExperiment: (projectId, candidate) =>
    request(`${BASE}/projects/${projectId}/next-experiment/confirm`, {
      method: 'POST',
      body: JSON.stringify({ candidate }),
    }),

  // === Research Graph V2 ===
  getGraph: (projectId) => request(`${BASE}/projects/${projectId}/graph`),
}

export const literatureApi = {
  search: (q, source = 'openalex', limit = 8) =>
    request(`${BASE}/literature/search?q=${encodeURIComponent(q)}&source=${source}&limit=${limit}`),
  getPaper: (paperId, source = 'openalex') =>
    request(`${BASE}/literature/paper/${paperId}?source=${source}`),
}

