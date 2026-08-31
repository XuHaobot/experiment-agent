<template>
  <div class="modal-mask" @click.self="$emit('close')">
    <div class="modal-card">
      <div class="modal-header">
        <span class="modal-title">AI & Privacy Gateway 设置</span>
        <button class="btn-x" @click="$emit('close')" title="关闭">✕</button>
      </div>

      <!-- Tab Switch: Local AI vs Privacy Boundary vs Cloud BYOK -->
      <div class="tab-row">
        <button :class="['tab-btn', activeTab === 'local' ? 'active' : '']" @click="activeTab = 'local'">
          🖥️ Local AI (Ollama)
        </button>
        <button :class="['tab-btn', activeTab === 'privacy' ? 'active' : '']" @click="activeTab = 'privacy'">
          🛡️ Privacy Boundary
        </button>
        <button :class="['tab-btn', activeTab === 'cloud' ? 'active' : '']" @click="activeTab = 'cloud'">
          ☁️ Cloud (BYOK)
        </button>
      </div>

      <!-- TAB 1: Local AI (Ollama) -->
      <div v-if="activeTab === 'local'" class="tab-content">
        <p class="modal-tip">
          连接本地离线大模型（Ollama / llama.cpp），<b>所有科研数据 100% 留存本机</b>，不发生任何外网传输。
        </p>

        <div class="provider-status-card" :class="ollamaStatus">
          <div class="status-indicator">
            <span class="status-dot"></span>
            <span class="status-text">
              {{ ollamaStatus === 'connected' ? '已连接本地 Ollama 服务' : ollamaStatus === 'error' ? '连接异常' : '未检测到 Ollama 服务' }}
            </span>
          </div>
          <button class="btn-check" @click="checkOllamaHealth" :disabled="isChecking">
            {{ isChecking ? '检测中...' : '测试连通性' }}
          </button>
        </div>

        <label class="field">
          <span class="field-label">Ollama 服务端点</span>
          <input v-model="ollamaEndpoint" placeholder="http://localhost:11434" spellcheck="false" />
        </label>

        <label class="field">
          <span class="field-label">选择本地模型</span>
          <div class="select-row">
            <select v-model="selectedModel">
              <option v-if="localModels.length === 0" value="qwen2.5:7b">qwen2.5:7b (默认)</option>
              <option v-for="m in localModels" :key="m.name" :value="m.name">
                {{ m.name }} ({{ formatSize(m.size) }})
              </option>
            </select>
            <button class="btn-refresh" @click="fetchLocalModels" title="刷新本地模型清单">🔄</button>
          </div>
        </label>

        <div class="hint-box">
          💡 推荐本地规格：<code>qwen2.5:7b</code> (日常推理 ~5GB 显存) 或 <code>deepseek-coder-v2:16b</code> (复杂代码)。
        </div>
      </div>

      <!-- TAB 2: Privacy Boundary Gateway -->
      <div v-if="activeTab === 'privacy'" class="tab-content">
        <p class="modal-tip">
          配置 ResearchOS 敏感科研数据外发门禁与 AI 路由策略。
        </p>

        <label class="field">
          <span class="field-label">AI 路由策略 (Routing Policy)</span>
          <select v-model="routingPolicy">
            <option value="LOCAL_ONLY">🔒 仅限本地 (LOCAL_ONLY) - 严禁一切云端传输</option>
            <option value="LOCAL_PREFERRED">🛡️ 本地优先 (LOCAL_PREFERRED) - 敏感数据本地处理</option>
            <option value="CLOUD_ALLOWED">☁️ 允许云端 (CLOUD_ALLOWED) - 经授权可发送脱敏摘要</option>
          </select>
        </label>

        <div class="rules-card">
          <div class="rules-title">🛡️ 静态隐私分级控制矩阵</div>
          <div class="rule-item">
            <span class="badge badge-public">PUBLIC</span>
            <span class="rule-desc">公开文献元数据、开源代码模板</span>
            <span class="rule-action allow">ALLOW (自动放行)</span>
          </div>
          <div class="rule-item">
            <span class="badge badge-sensitive">SENSITIVE</span>
            <span class="rule-desc">未发表假说、实验超参、分析草稿</span>
            <span class="rule-action ask">ASK (需人工授权)</span>
          </div>
          <div class="rule-item">
            <span class="badge badge-restricted">RESTRICTED</span>
            <span class="rule-desc">原始 CSV 数据集、本地绝对路径、密钥</span>
            <span class="rule-action deny">DENY (硬性拦截)</span>
          </div>
        </div>
      </div>

      <!-- TAB 3: Cloud BYOK (OpenAI Compatible) -->
      <div v-if="activeTab === 'cloud'" class="tab-content">
        <p class="modal-tip">
          填入你自己的 LLM API Key，费用由你的个人额度承担。随请求使用，不落盘。
        </p>

        <label class="field">
          <span class="field-label">API Key</span>
          <input v-model="form.apiKey" type="password" placeholder="sk-..." autocomplete="off" spellcheck="false" />
        </label>

        <label class="field">
          <span class="field-label">Base URL</span>
          <input v-model="form.baseUrl" placeholder="https://api.deepseek.com/v1" spellcheck="false" />
        </label>

        <label class="field">
          <span class="field-label">Model</span>
          <input v-model="form.model" placeholder="deepseek-chat" spellcheck="false" />
        </label>

        <details class="preset">
          <summary>常见服务商填法</summary>
          <ul>
            <li><b>DeepSeek</b>：Base URL <code>https://api.deepseek.com/v1</code> · Model <code>deepseek-chat</code></li>
            <li><b>通义千问</b>：Base URL <code>https://dashscope.aliyuncs.com/compatible-mode/v1</code> · Model <code>qwen-plus</code></li>
            <li><b>OpenAI</b>：Base URL <code>https://api.openai.com/v1</code> · Model <code>gpt-4o-mini</code></li>
          </ul>
        </details>
      </div>

      <div class="modal-actions">
        <button class="btn-clear" @click="clear">重置默认</button>
        <button class="btn-save" @click="save">应用配置</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import {
  getLlmConfig, saveLlmConfig, clearLlmConfig,
} from '../api/client.js'

const emit = defineEmits(['close', 'saved'])

const activeTab = ref('local')
const form = reactive({ apiKey: '', baseUrl: '', model: '' })
const ollamaEndpoint = ref('http://localhost:11434')
const selectedModel = ref('qwen2.5:7b')
const localModels = ref([])
const ollamaStatus = ref('checking')
const isChecking = ref(false)
const routingPolicy = ref('LOCAL_PREFERRED')

onMounted(async () => {
  const cfg = getLlmConfig()
  if (cfg) {
    form.apiKey = cfg.api_key || ''
    form.baseUrl = cfg.base_url || ''
    form.model = cfg.model || ''
  }
  await checkOllamaHealth()
  await fetchPrivacyConfig()
})

async function checkOllamaHealth() {
  isChecking.value = true
  try {
    const res = await fetch('/api/llm/providers/ollama/health')
    if (res.ok) {
      const data = await res.json()
      ollamaStatus.value = data.status === 'connected' ? 'connected' : 'error'
      if (data.status === 'connected') {
        await fetchLocalModels()
      }
    } else {
      ollamaStatus.value = 'disconnected'
    }
  } catch {
    ollamaStatus.value = 'disconnected'
  } finally {
    isChecking.value = false
  }
}

async function fetchLocalModels() {
  try {
    const res = await fetch('/api/llm/providers/ollama/models')
    if (res.ok) {
      const data = await res.json()
      localModels.value = data.models || []
      if (localModels.value.length > 0 && !localModels.value.some(m => m.name === selectedModel.value)) {
        selectedModel.value = localModels.value[0].name
      }
    }
  } catch (e) {
    console.debug('Failed to fetch local models:', e)
  }
}

async function fetchPrivacyConfig() {
  try {
    const res = await fetch('/api/privacy/config')
    if (res.ok) {
      const data = await res.json()
      routingPolicy.value = data.routing_policy || 'LOCAL_PREFERRED'
    }
  } catch (e) {
    console.debug('Failed to fetch privacy config:', e)
  }
}

function formatSize(bytes) {
  if (!bytes) return ''
  const gb = bytes / (1024 * 1024 * 1024)
  return `${gb.toFixed(1)} GB`
}

async function save() {
  // 1. Save Cloud config if present
  if (form.apiKey.trim()) {
    saveLlmConfig({
      apiKey: form.apiKey.trim(),
      baseUrl: form.baseUrl.trim(),
      model: form.model.trim(),
    })
  }

  // 2. Select Provider in backend
  const providerName = activeTab.value === 'local' ? 'ollama' : (form.apiKey.trim() ? 'openai_compatible' : 'mock')
  try {
    await fetch('/api/llm/providers/select', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider_name: providerName,
        routing_policy: routingPolicy.value,
      }),
    })
  } catch (e) {
    console.error('Failed to update provider select:', e)
  }

  emit('saved')
  emit('close')
}

function clear() {
  clearLlmConfig()
  form.apiKey = ''
  form.baseUrl = ''
  form.model = ''
  routingPolicy.value = 'LOCAL_PREFERRED'
  emit('saved')
  emit('close')
}
</script>

<style scoped>
.modal-mask {
  position: fixed; inset: 0; background: rgba(0, 0, 0, 0.45);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal-card {
  width: 480px; max-width: 92vw; max-height: 86vh; overflow-y: auto;
  background: var(--card-bg, #fff);
  border: 1px solid var(--border-secondary, #ddd); border-radius: 14px;
  padding: 20px 24px; box-shadow: 0 12px 40px rgba(0, 0, 0, 0.25);
  color: var(--text-primary, #222);
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 12px;
}
.modal-title { font-size: 16px; font-weight: 600; font-family: var(--font-mono, monospace); }
.btn-x {
  border: none; background: transparent; cursor: pointer; font-size: 15px;
  color: var(--text-tertiary, #888); width: 26px; height: 26px; border-radius: 6px;
}
.btn-x:hover { background: var(--bg-tertiary, #f0f0f0); }

.tab-row {
  display: flex; gap: 8px; margin-bottom: 16px; border-bottom: 1px solid var(--border-secondary, #eee);
  padding-bottom: 8px;
}
.tab-btn {
  padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 500;
  border: 1px solid transparent; background: transparent; cursor: pointer; color: var(--text-secondary, #666);
}
.tab-btn.active {
  background: #EEF3FF; color: #3b82f6; border-color: #BFDBFE; font-weight: 600;
}

.modal-tip { font-size: 12px; line-height: 1.6; color: var(--text-secondary, #555); margin: 0 0 14px; }
.modal-tip b { color: var(--text-primary, #222); }

.provider-status-card {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; border-radius: 8px; margin-bottom: 14px; font-size: 13px;
  background: #f9fafb; border: 1px solid #e5e7eb;
}
.provider-status-card.connected { background: #ECFDF5; border-color: #A7F3D0; color: #065F46; }
.provider-status-card.disconnected { background: #FEF2F2; border-color: #FECACA; color: #991B1B; }
.status-indicator { display: flex; align-items: center; gap: 8px; font-weight: 500; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #9ca3af; }
.connected .status-dot { background: #10b981; }
.disconnected .status-dot { background: #ef4444; }

.btn-check {
  padding: 4px 10px; font-size: 12px; border-radius: 4px; border: 1px solid #d1d5db;
  background: #fff; cursor: pointer;
}
.btn-check:hover { background: #f3f4f6; }

.field { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; }
.field-label { font-size: 12px; color: var(--text-secondary, #555); font-weight: 500; }
.field input, .field select {
  padding: 8px 10px; border: 1px solid var(--border-primary, #ccc); border-radius: 6px;
  font-size: 13px; font-family: var(--font-mono, monospace);
  background: var(--bg-primary, #fff); color: var(--text-primary, #222);
}
.field input:focus, .field select:focus { outline: none; border-color: #3b82f6; }

.select-row { display: flex; gap: 6px; }
.select-row select { flex: 1; }
.btn-refresh {
  padding: 0 10px; border-radius: 6px; border: 1px solid #ccc; background: #fff; cursor: pointer;
}

.hint-box {
  padding: 8px 12px; background: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 6px;
  font-size: 11px; color: #475569; margin-bottom: 14px;
}

.rules-card {
  padding: 12px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; margin-bottom: 14px;
}
.rules-title { font-size: 12px; font-weight: 600; margin-bottom: 8px; color: #1E293B; }
.rule-item {
  display: flex; align-items: center; justify-content: space-between; font-size: 11px; padding: 4px 0;
  border-bottom: 1px solid #EDF2F7;
}
.rule-item:last-child { border-bottom: none; }
.badge {
  padding: 2px 6px; border-radius: 4px; font-weight: 600; font-family: var(--font-mono, monospace); font-size: 10px;
}
.badge-public { background: #E0F2FE; color: #0369A1; }
.badge-sensitive { background: #FEF3C7; color: #B45309; }
.badge-restricted { background: #FEE2E2; color: #B91C1C; }

.rule-desc { flex: 1; margin: 0 8px; color: #475569; }
.rule-action { font-weight: 600; }
.rule-action.allow { color: #059669; }
.rule-action.ask { color: #D97706; }
.rule-action.deny { color: #DC2626; }

.preset { font-size: 12px; color: var(--text-secondary, #555); margin-bottom: 16px; }
.preset summary { cursor: pointer; }
.preset ul { margin: 8px 0 0; padding-left: 18px; line-height: 1.8; }
.preset code {
  font-family: var(--font-mono, monospace); font-size: 11px;
  background: var(--bg-tertiary, #f0f0f0); padding: 1px 5px; border-radius: 3px;
}

.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; }
.btn-clear, .btn-save {
  padding: 8px 16px; border-radius: 6px; font-size: 13px; cursor: pointer;
}
.btn-clear {
  border: 1px solid var(--border-primary, #ccc); background: transparent;
  color: var(--text-secondary, #555);
}
.btn-clear:hover { background: var(--bg-tertiary, #f0f0f0); }
.btn-save {
  border: 1px solid #3b82f6; background: #3b82f6; color: #fff; font-weight: 500;
}
.btn-save:hover { background: #2563eb; }
</style>
