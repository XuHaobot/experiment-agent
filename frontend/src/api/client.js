const BASE = '/api'

import { ref } from 'vue'

// ---------------------------------------------------------------------------
// 匿名租户标识：公网多用户隔离用。每个浏览器生成一个稳定 UUID，
// 只随请求发出、不携带任何个人信息；会话/历史都按它隔离，互不可见。
// ---------------------------------------------------------------------------
const TENANT_KEY = 'exp_agent_tenant_id'
const DEMO_KEY = 'exp_agent_demo_readonly'

function getTenantId() {
  let id = localStorage.getItem(TENANT_KEY)
  if (!id) {
    let rand
    try {
      rand = crypto.randomUUID().replace(/-/g, '')
    } catch {
      rand = 'xxxxxxxxxxxx'.replace(/x/g, () => ((Math.random() * 16) | 0).toString(16))
    }
    id = 't-' + rand.slice(0, 20)
    localStorage.setItem(TENANT_KEY, id)
  }
  return id
}

// ---------------------------------------------------------------------------
// 演示模式（只读）开关：由 /api/health 的 demo_readonly 决定。
// 导出为 ref，组件内用 demoReadOnly.value 读取，保持响应式。
// ---------------------------------------------------------------------------
export const demoReadOnly = ref(false)

export async function initDemoMode() {
  try {
    const r = await request('/health')
    demoReadOnly.value = !!r?.demo_readonly
  } catch {
    demoReadOnly.value = false
  }
  return demoReadOnly.value
}

// ---------------------------------------------------------------------------
// BYOK：用户自带 LLM Key，仅存于本浏览器 localStorage，随请求发送，不落服务器
// ---------------------------------------------------------------------------
const LLM_CONFIG_KEY = 'exp_agent_llm_config'

export function getLlmConfig() {
  try {
    const raw = localStorage.getItem(LLM_CONFIG_KEY)
    if (!raw) return null
    const cfg = JSON.parse(raw)
    if (cfg && cfg.apiKey) {
      return { api_key: cfg.apiKey, base_url: cfg.baseUrl || '', model: cfg.model || '' }
    }
    return null
  } catch {
    return null
  }
}

export function saveLlmConfig(cfg) {
  localStorage.setItem(LLM_CONFIG_KEY, JSON.stringify(cfg))
}

export function clearLlmConfig() {
  localStorage.removeItem(LLM_CONFIG_KEY)
}

// ---------------------------------------------------------------------------
// BYOK：用户自带 Embedding Key（语义检索用），同样仅存本浏览器、随请求发送
// ---------------------------------------------------------------------------
const EMBEDDING_CONFIG_KEY = 'exp_agent_embedding_config'

export function getEmbeddingConfig() {
  try {
    const raw = localStorage.getItem(EMBEDDING_CONFIG_KEY)
    if (!raw) return null
    const cfg = JSON.parse(raw)
    if (cfg && cfg.apiKey) {
      return {
        embedding_api_key: cfg.apiKey,
        embedding_base_url: cfg.baseUrl || '',
        embedding_model: cfg.model || '',
        embedding_api_format: cfg.apiFormat || 'dashscope',
      }
    }
    return null
  } catch {
    return null
  }
}

export function saveEmbeddingConfig(cfg) {
  localStorage.setItem(EMBEDDING_CONFIG_KEY, JSON.stringify(cfg))
}

export function clearEmbeddingConfig() {
  localStorage.removeItem(EMBEDDING_CONFIG_KEY)
}

/** 把用户本地的 BYOK 配置（chat + embedding）附加到请求体，无则不加。 */
function attachByok(body) {
  const llm = getLlmConfig()
  if (llm) body.llm_config = llm
  const emb = getEmbeddingConfig()
  if (emb) body.embedding_config = emb
  return body
}

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

  // ============================================================
  // FAQ 知识库（报错沉淀飞轮）
  // ============================================================

  /** 获取 FAQ 概览：领域 FAQ（报错→解决方案）+ 系统常见问题 */
  getFaq() { return request('/faq') },

  /** 按关键词检索领域 FAQ，用于上传失败时展示排查提示 */
  searchFaq(query, topK = 5) {
    return request('/faq/search', { method: 'POST', body: JSON.stringify({ query, top_k: topK }) })
  },

  /** 评测集自动化回归（受只读模式守卫） */
  runEval() { return request('/evaluate/run', { method: 'POST', body: JSON.stringify({}) }) },

  /** 批量分析：以 multipart 字段名 files 提交多个文件到 /api/analyze/batch */
  analyzeFiles(files) {
    const form = new FormData()
    for (const f of files) form.append('files', f)
    return fetch(`${BASE}/analyze/batch`, { method: 'POST', body: form }).then(r => {
      if (!r.ok) {
        return r.json().catch(() => ({ detail: r.statusText })).then(err => {
          throw new Error(err.detail || '批量分析失败')
        })
      }
      return r.json()
    })
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
    body.tenant_id = getTenantId()
    attachByok(body)
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
    body.tenant_id = getTenantId()
    attachByok(body)
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
    body.tenant_id = getTenantId()
    attachByok(body)
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

  getSessions() { return request(`/sessions?tenant_id=${encodeURIComponent(getTenantId())}`) },
  deleteSession(sessionId) {
    return request(`/sessions/${sessionId}?tenant_id=${encodeURIComponent(getTenantId())}`, { method: 'DELETE' })
  },
  getSessionHistory(sessionId) {
    return request(`/sessions/${sessionId}/history?tenant_id=${encodeURIComponent(getTenantId())}`)
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
