const BASE = '/api'

async function request(url, options = {}) {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  // Handle 204 No Content and empty bodies
  if (res.status === 204 || res.headers.get('content-length') === '0') {
    return null
  }
  return res.json().catch(() => null)
}

export const api = {
  health() { return request('/health') },

  analyzeFile(file) {
    const form = new FormData()
    form.append('file', file)
    return fetch(`${BASE}/analyze`, { method: 'POST', body: form }).then(r => {
      if (!r.ok) {
        return r.json().catch(() => ({ detail: r.statusText })).then(err => {
          throw new Error(err.detail || 'Upload failed')
        })
      }
      return r.json()
    })
  },

  analyzeText(text, source = 'text-input') {
    return request('/analyze/text', { method: 'POST', body: JSON.stringify({ text, source }) })
  },

  getRecords() { return request('/records') },
  getRecord(id) { return request(`/records/${id}`) },
  getGraphList() { return request('/graph') },
  getGraph(filename) { return request(`/graph/${filename}`) },
  search(query) { return request(`/search?q=${encodeURIComponent(query)}`) },

  ask(question) {
    return request('/ask', { method: 'POST', body: JSON.stringify({ question }) })
  },

  // ============================================================
  // AgentV2 Chat API (Function Calling)
  // ============================================================

  /**
   * 新版对话接口 — 对齐 WorkspaceMain.vue 的调用格式。
   * 前端发送 { message, sessionId, contextExperimentId }
   * 后端期望 { question, session_id }，返回 { answer, agent_trace, total_iterations }
   */
  chatSend(payload) {
    const body = { question: payload.message }
    if (payload.sessionId) body.session_id = payload.sessionId
    return request('/chat', { method: 'POST', body: JSON.stringify(body) })
      .then(res => {
        if (!res) return { reply: '' }
        // 映射后端字段到前端期望的格式
        return {
          reply: res.answer || '',
          agentTrace: res.agent_trace || [],
          totalIterations: res.total_iterations || 0,
        }
      })
  },

  chat(question, sessionId = null) {
    const body = { question }
    if (sessionId) body.session_id = sessionId
    return request('/chat', { method: 'POST', body: JSON.stringify(body) })
  },

  /**
   * SSE 流式对话。返回一个 reader 供调用方逐步读取。
   * @param {string} question
   * @param {string|null} sessionId
   * @param {AbortSignal} [signal] - 用于取消请求的 AbortSignal
   * @returns {Promise<ReadableStreamDefaultReader>}
   */
  async chatStream(question, sessionId = null, signal = undefined) {
    const body = { question }
    if (sessionId) body.session_id = sessionId
    const res = await fetch(`${BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    })
    if (!res.ok) throw new Error('Stream request failed')
    return res.body.getReader()
  },

  // ============================================================
  // Session Management
  // ============================================================

  getSessions() { return request('/sessions') },
  deleteSession(sessionId) {
    return request(`/sessions/${sessionId}`, { method: 'DELETE' })
  },
  getSessionHistory(sessionId) {
    return request(`/sessions/${sessionId}/history`)
  },

  // ============================================================
  // Vector Store
  // ============================================================

  getVectorStoreStats() { return request('/vector-store/stats') },
  rebuildVectorIndex() { return request('/vector-store/rebuild', { method: 'POST' }) },

  // ============================================================
  // Experiment management
  // ============================================================

  getExperiments() { return request('/experiments') },
  createExperiment(name, description, createdAt) {
    return request('/experiments', { method: 'POST', body: JSON.stringify({ name, description, created_at: createdAt || new Date().toISOString() }) })
  },
  deleteExperiment(id) {
    return request(`/experiments/${id}`, { method: 'DELETE' })
  },
  deleteRecord(id) {
    return request(`/records/${id}`, { method: 'DELETE' })
  },
  addRecordToExperiment(recordId, experimentId) {
    return request(`/experiments/${experimentId}/records/${recordId}`, { method: 'POST' })
  },
}
