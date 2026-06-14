<template>
  <div class="upload-page">
    <div class="page-header">
      <h1 class="page-title">上传实验记录</h1>
      <p class="page-desc">上传聊天记录、日志文件或直接粘贴文本，Agent 自动提取结构化信息</p>
    </div>

    <div class="upload-area" :class="{ drag: isDragging }" @dragover.prevent="isDragging = true" @dragleave="isDragging = false" @drop.prevent="onDrop">
      <div class="upload-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="40" height="40">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
        </svg>
      </div>
      <p class="upload-prompt">拖拽文件到此处，或</p>
      <label class="upload-btn">
        <input type="file" accept=".txt,.md,.json" @change="onFileChange" hidden />
        选择文件
      </label>
      <p class="upload-hint">支持 .txt / .md / .json</p>
    </div>

    <div class="divider">
      <span>或直接粘贴文本</span>
    </div>

    <textarea v-model="textInput" class="text-input" placeholder="粘贴实验聊天记录、终端日志、训练命令..." rows="12"></textarea>

    <div class="actions">
      <button class="btn-primary" :disabled="analyzing" @click="startAnalysis">
        <span v-if="!analyzing">开始分析</span>
        <span v-else><span class="spinner"></span> 分析中...</span>
      </button>
    </div>

    <div v-if="error" class="error-msg">{{ error }}</div>

    <div v-if="analyzing" class="analyzing-hint">
      <p>Agent 正在分析中...</p>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: progress + '%' }"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api/client'

const router = useRouter()
const textInput = ref('')
const file = ref(null)
const analyzing = ref(false)
const progress = ref(0)
const isDragging = ref(false)
const error = ref('')

function onFileChange(e) {
  file.value = e.target.files[0]
  if (file.value) {
    textInput.value = ''
  }
}

function onDrop(e) {
  isDragging.value = false
  const f = e.dataTransfer.files[0]
  if (f) {
    file.value = f
    textInput.value = ''
  }
}

async function startAnalysis() {
  if (!file.value && !textInput.value.trim()) {
    error.value = '请上传文件或粘贴文本内容'
    return
  }

  analyzing.value = true
  error.value = ''
  progress.value = 30

  try {
    let result
    if (file.value) {
      progress.value = 50
      result = await api.analyzeFile(file.value)
    } else {
      progress.value = 50
      result = await api.analyzeText(textInput.value)
    }
    progress.value = 100

    const recordId = result.record.id
    setTimeout(() => {
      router.push(`/analysis/${recordId}`)
    }, 400)
  } catch (e) {
    error.value = e.message || '分析失败'
    analyzing.value = false
    progress.value = 0
  }
}
</script>

<style scoped>
.upload-page {
  max-width: 640px;
  margin: 0 auto;
  padding: 40px 24px;
}

.page-header {
  margin-bottom: 32px;
}

.page-title {
  font-family: var(--font-mono);
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.03em;
  margin-bottom: 6px;
}

.page-desc {
  font-size: 13px;
  color: var(--text-tertiary);
  line-height: 1.6;
}

.upload-area {
  border: 1.5px dashed var(--border-primary);
  border-radius: var(--radius-lg);
  padding: 48px 24px;
  text-align: center;
  transition: border-color 0.2s, background 0.2s;
  background: var(--bg-secondary);
}

.upload-area.drag {
  border-color: var(--accent);
  background: var(--bg-tertiary);
}

.upload-icon {
  color: var(--text-tertiary);
  margin-bottom: 16px;
}

.upload-prompt {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.upload-btn {
  display: inline-block;
  padding: 8px 20px;
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
  background: var(--bg-primary);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.upload-btn:hover {
  border-color: var(--accent);
  background: var(--bg-secondary);
}

.upload-hint {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 12px;
}

.divider {
  display: flex;
  align-items: center;
  margin: 28px 0;
  color: var(--text-tertiary);
  font-size: 12px;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border-secondary);
}

.divider span {
  padding: 0 14px;
}

.text-input {
  width: 100%;
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.6;
  resize: vertical;
  background: var(--bg-primary);
  color: var(--text-primary);
  transition: border-color 0.15s;
}

.text-input:focus {
  outline: none;
  border-color: var(--accent);
}

.text-input::placeholder {
  color: var(--text-tertiary);
}

.actions {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 28px;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--accent);
  color: var(--bg-primary);
  font-size: 14px;
  font-weight: 500;
  transition: opacity 0.15s;
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.85;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-msg {
  margin-top: 16px;
  padding: 12px 16px;
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
  border-radius: var(--radius-sm);
  font-size: 13px;
}

.analyzing-hint {
  margin-top: 28px;
  text-align: center;
}

.analyzing-hint p {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.progress-track {
  height: 3px;
  background: var(--border-secondary);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--accent);
  transition: width 0.4s ease;
}

.spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid var(--bg-primary);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
