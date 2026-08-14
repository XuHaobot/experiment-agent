<template>
  <div class="modal-mask" @click.self="$emit('close')">
    <div class="modal-card">
      <div class="modal-header">
        <span class="modal-title">模型设置（BYOK · 自带密钥）</span>
        <button class="btn-x" @click="$emit('close')" title="关闭">✕</button>
      </div>

      <p class="modal-tip">
        填入你自己的 LLM API Key，即可在本站完整体验 Agent 能力，<b>费用由你的额度承担</b>。
        本站服务器<b>不存储</b>你的 Key——它只在此次请求内使用，随请求发送给模型服务，不落盘、不打日志、不回显。
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
        <summary>常见服务商填法（对话）</summary>
        <ul>
          <li><b>DeepSeek</b>：Base URL <code>https://api.deepseek.com/v1</code> · Model <code>deepseek-chat</code></li>
          <li><b>通义千问</b>：Base URL <code>https://dashscope.aliyuncs.com/compatible-mode/v1</code> · Model <code>qwen-plus</code></li>
          <li><b>OpenAI</b>：Base URL <code>https://api.openai.com/v1</code> · Model <code>gpt-4o-mini</code></li>
        </ul>
      </details>

      <hr class="sep" />

      <div class="section-title">语义检索 Embedding（可选）</div>
      <p class="modal-tip">
        填入你自己的 Embedding Key 后，才能使用<b>语义搜索</b>（理解语义而非仅关键词匹配）。
        不填则自动降级为<b>关键词搜索</b>，对话照常可用。Embedding 同样仅存本浏览器、不落服务器。
      </p>

      <label class="field">
        <span class="field-label">Embedding API Key</span>
        <input v-model="embForm.apiKey" type="password" placeholder="sk-..." autocomplete="off" spellcheck="false" />
      </label>

      <label class="field">
        <span class="field-label">接口格式</span>
        <select v-model="embForm.apiFormat">
          <option value="dashscope">DashScope / 通义（text-embedding-v2）</option>
          <option value="openai">OpenAI 兼容（/embeddings）</option>
        </select>
      </label>

      <label class="field">
        <span class="field-label">Base URL（可选，留空用默认值）</span>
        <input v-model="embForm.baseUrl" :placeholder="embForm.apiFormat === 'openai' ? 'https://api.openai.com/v1' : 'DashScope 默认地址'" spellcheck="false" />
      </label>

      <label class="field">
        <span class="field-label">Model（可选，留空用默认值）</span>
        <input v-model="embForm.model" :placeholder="embForm.apiFormat === 'openai' ? 'text-embedding-3-small' : 'text-embedding-v2'" spellcheck="false" />
      </label>

      <details class="preset">
        <summary>Embedding 服务商填法</summary>
        <ul>
          <li><b>通义 / DashScope</b>：格式选 <code>dashscope</code> · Key 即百炼 API Key（Model 默认 text-embedding-v2）</li>
          <li><b>OpenAI</b>：格式选 <code>openai</code> · Model <code>text-embedding-3-small</code></li>
          <li><b>DeepSeek</b>：<span class="warn">不提供 Embedding API</span>，请勿在此填写，将自动降级关键词搜索</li>
        </ul>
      </details>

      <div class="modal-actions">
        <button class="btn-clear" @click="clear">清除全部</button>
        <button class="btn-save" @click="save">保存</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, onMounted } from 'vue'
import {
  getLlmConfig, saveLlmConfig, clearLlmConfig,
  getEmbeddingConfig, saveEmbeddingConfig, clearEmbeddingConfig,
} from '../api/client.js'

const emit = defineEmits(['close', 'saved'])

const form = reactive({ apiKey: '', baseUrl: '', model: '' })
const embForm = reactive({ apiKey: '', baseUrl: '', model: '', apiFormat: 'dashscope' })

onMounted(() => {
  const cfg = getLlmConfig()
  if (cfg) {
    form.apiKey = cfg.api_key || ''
    form.baseUrl = cfg.base_url || ''
    form.model = cfg.model || ''
  }
  const emb = getEmbeddingConfig()
  if (emb) {
    embForm.apiKey = emb.embedding_api_key || ''
    embForm.baseUrl = emb.embedding_base_url || ''
    embForm.model = emb.embedding_model || ''
    embForm.apiFormat = emb.embedding_api_format || 'dashscope'
  }
})

function save() {
  if (!form.apiKey.trim()) {
    alert('对话 API Key 不能为空')
    return
  }
  saveLlmConfig({
    apiKey: form.apiKey.trim(),
    baseUrl: form.baseUrl.trim(),
    model: form.model.trim(),
  })
  // Embedding 为可选：有填才保存，没填则清除（保持降级）
  if (embForm.apiKey.trim()) {
    saveEmbeddingConfig({
      apiKey: embForm.apiKey.trim(),
      baseUrl: embForm.baseUrl.trim(),
      model: embForm.model.trim(),
      apiFormat: embForm.apiFormat,
    })
  } else {
    clearEmbeddingConfig()
  }
  emit('saved')
  emit('close')
}

function clear() {
  clearLlmConfig()
  clearEmbeddingConfig()
  form.apiKey = ''
  form.baseUrl = ''
  form.model = ''
  embForm.apiKey = ''
  embForm.baseUrl = ''
  embForm.model = ''
  embForm.apiFormat = 'dashscope'
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
  width: 420px; max-width: 92vw; background: var(--bg-primary, #fff);
  border: 1px solid var(--border-secondary, #ddd); border-radius: 10px;
  padding: 18px 20px; box-shadow: 0 12px 40px rgba(0, 0, 0, 0.25);
  color: var(--text-primary, #222);
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 10px;
}
.modal-title { font-size: 15px; font-weight: 600; font-family: var(--font-mono, monospace); }
.btn-x {
  border: none; background: transparent; cursor: pointer; font-size: 15px;
  color: var(--text-tertiary, #888); width: 26px; height: 26px; border-radius: 6px;
}
.btn-x:hover { background: var(--bg-tertiary, #f0f0f0); }
.modal-tip { font-size: 12px; line-height: 1.6; color: var(--text-secondary, #555); margin: 0 0 14px; }
.modal-tip b { color: var(--text-primary, #222); }

.field { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; }
.field-label { font-size: 12px; color: var(--text-secondary, #555); }
.field input {
  padding: 8px 10px; border: 1px solid var(--border-primary, #ccc); border-radius: 6px;
  font-size: 13px; font-family: var(--font-mono, monospace);
  background: var(--bg-primary, #fff); color: var(--text-primary, #222);
}
.field input:focus { outline: none; border-color: var(--accent, #4a7cff); }
.field select {
  padding: 8px 10px; border: 1px solid var(--border-primary, #ccc); border-radius: 6px;
  font-size: 13px; background: var(--bg-primary, #fff); color: var(--text-primary, #222);
}
.field select:focus { outline: none; border-color: var(--accent, #4a7cff); }

.sep { border: none; border-top: 1px dashed var(--border-secondary, #ddd); margin: 6px 0 14px; }
.section-title {
  font-size: 13px; font-weight: 600; margin-bottom: 6px;
  color: var(--text-primary, #222); font-family: var(--font-mono, monospace);
}
.warn { color: #c0392b; font-weight: 600; }

.preset { font-size: 12px; color: var(--text-secondary, #555); margin-bottom: 16px; }
.preset summary { cursor: pointer; }
.preset ul { margin: 8px 0 0; padding-left: 18px; line-height: 1.8; }
.preset code {
  font-family: var(--font-mono, monospace); font-size: 11px;
  background: var(--bg-tertiary, #f0f0f0); padding: 1px 5px; border-radius: 3px;
}

.modal-actions { display: flex; justify-content: flex-end; gap: 10px; }
.btn-clear, .btn-save {
  padding: 8px 16px; border-radius: 6px; font-size: 13px; cursor: pointer;
}
.btn-clear {
  border: 1px solid var(--border-primary, #ccc); background: transparent;
  color: var(--text-secondary, #555);
}
.btn-clear:hover { background: var(--bg-tertiary, #f0f0f0); }
.btn-save {
  border: 1px solid var(--accent, #4a7cff); background: var(--accent, #4a7cff); color: #fff;
}
.btn-save:hover { opacity: 0.9; }
</style>
