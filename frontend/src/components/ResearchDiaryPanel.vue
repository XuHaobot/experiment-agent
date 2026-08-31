<template>
  <div class="diary-panel">
    <div class="diary-header">
      <div>
        <h3 class="diary-title">📔 Research Diary (科研日志与反思)</h3>
        <p class="diary-subtitle">记录科研人员每日直觉、随手灵感与非正式观察 (USER_BELIEF)。AI 不得自动修改或伪造。</p>
      </div>
      <button class="btn-new-entry" @click="showCreate = true">+ 记录今日反思</button>
    </div>

    <!-- 新建日志表单 -->
    <div v-if="showCreate" class="create-form">
      <div class="form-row">
        <input v-model="newTitle" placeholder="日志标题（如：关于 k=20 拐点过平滑机制的直觉猜测）" class="form-input" />
        <input v-model="newDate" type="date" class="form-date" />
      </div>
      <textarea v-model="newContent" placeholder="记录今天观察到的现象、个人想法或下一步想做的事情..." class="form-textarea" rows="4"></textarea>
      <div class="form-row">
        <input v-model="newTags" placeholder="标签 (逗号分隔，如：over-smoothing, graph, intuition)" class="form-input" />
      </div>
      <div class="form-actions">
        <button class="btn-save" @click="saveEntry" :disabled="!newTitle.trim() || !newContent.trim()">保存日志</button>
        <button class="btn-cancel" @click="showCreate = false">取消</button>
      </div>
    </div>

    <div v-if="loading" class="diary-loading">⏳ 正在加载科研日记...</div>
    <div v-else-if="entries.length === 0 && !showCreate" class="diary-empty">
      <div class="empty-icon">📝</div>
      <h4>暂无科研日志记录</h4>
      <p>写下你对当前实验结果的第一直觉、灵感或未证实的猜想，沉淀真实的科研心路历程。</p>
      <button class="btn-new-entry" @click="showCreate = true">+ 记录第一篇反思</button>
    </div>

    <div v-else class="diary-list">
      <div v-for="e in entries" :key="e.id" class="diary-card">
        <div class="diary-card-top">
          <span class="diary-date font-mono">{{ e.date }}</span>
          <span class="epistemic-badge">USER_BELIEF</span>
          <button class="btn-del" @click="deleteEntry(e.id)">✕</button>
        </div>
        <h4 class="diary-card-title">{{ e.title }}</h4>
        <div class="diary-card-content">{{ e.content }}</div>
        <div v-if="e.tags && e.tags.length" class="diary-tags">
          <span v-for="tag in e.tags" :key="tag" class="diary-tag">#{{ tag }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  projectId: {
    type: String,
    required: true,
  },
})

const entries = ref([])
const loading = ref(false)
const showCreate = ref(false)
const newTitle = ref('')
const newContent = ref('')
const newDate = ref(new Date().toISOString().substring(0, 10))
const newTags = ref('')

async function loadEntries() {
  loading.value = true
  try {
    const res = await fetch(`/api/projects/${props.projectId}/diary`)
    if (res.ok) {
      const data = await res.json()
      entries.value = data.entries || []
    }
  } catch (e) {
    console.error('Failed to load diary:', e)
  } finally {
    loading.value = false
  }
}

async function saveEntry() {
  if (!newTitle.value.trim() || !newContent.value.trim()) return
  const tagList = newTags.value.split(',').map(t => t.trim()).filter(Boolean)
  try {
    const res = await fetch(`/api/projects/${props.projectId}/diary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: newTitle.value.trim(),
        content: newContent.value.trim(),
        entry_date: newDate.value,
        tags: tagList,
      }),
    })
    if (res.ok) {
      newTitle.value = ''
      newContent.value = ''
      newTags.value = ''
      showCreate.value = false
      await loadEntries()
    }
  } catch (e) {
    alert('保存失败: ' + e)
  }
}

async function deleteEntry(id) {
  if (!confirm('确定删除该篇科研日志？')) return
  try {
    const res = await fetch(`/api/projects/${props.projectId}/diary/${id}`, { method: 'DELETE' })
    if (res.ok) await loadEntries()
  } catch (e) {
    alert('删除失败: ' + e)
  }
}

onMounted(() => {
  loadEntries()
})
</script>

<style scoped>
.diary-panel { padding: 0; color: var(--text-primary, #1e293b); }
.diary-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.diary-title { font-size: 18px; margin: 0 0 4px 0; font-weight: 600; }
.diary-subtitle { font-size: 12px; color: var(--text-secondary, #64748b); margin: 0; }
.btn-new-entry { background: #3b82f6; color: #fff; border: none; border-radius: 6px; padding: 6px 14px; font-size: 12px; font-weight: 600; cursor: pointer; }

.create-form { background: var(--bg-surface-1, #fff); border: 1px solid var(--border-default, #e2e8f0); border-radius: 8px; padding: 16px; margin-bottom: 20px; }
.form-row { display: flex; gap: 10px; margin-bottom: 10px; }
.form-input { flex: 1; border: 1px solid var(--border-default, #cbd5e1); border-radius: 6px; padding: 8px 10px; font-size: 13px; background: var(--bg-surface-2, #f8fafc); }
.form-date { border: 1px solid var(--border-default, #cbd5e1); border-radius: 6px; padding: 8px 10px; font-size: 13px; background: var(--bg-surface-2, #f8fafc); }
.form-textarea { width: 100%; border: 1px solid var(--border-default, #cbd5e1); border-radius: 6px; padding: 10px; font-size: 13px; box-sizing: border-box; background: var(--bg-surface-2, #f8fafc); margin-bottom: 10px; resize: vertical; }
.form-actions { display: flex; gap: 8px; }
.btn-save { background: #10b981; color: #fff; border: none; border-radius: 6px; padding: 6px 16px; font-size: 12px; font-weight: 600; cursor: pointer; }
.btn-save:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-cancel { background: transparent; border: 1px solid var(--border-default, #cbd5e1); border-radius: 6px; padding: 6px 14px; font-size: 12px; cursor: pointer; }

.diary-list { display: flex; flex-direction: column; gap: 12px; }
.diary-card { background: var(--bg-surface-1, #fff); border: 1px solid var(--border-default, #e2e8f0); border-radius: 8px; padding: 14px 16px; }
.diary-card-top { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.diary-date { font-size: 12px; color: var(--text-secondary, #64748b); font-weight: 600; }
.epistemic-badge { font-size: 10px; background: #fef3c7; color: #b45309; padding: 1px 6px; border-radius: 4px; font-weight: 700; }
.btn-del { margin-left: auto; background: none; border: none; color: var(--text-muted, #94a3b8); cursor: pointer; font-size: 12px; }
.btn-del:hover { color: #ef4444; }
.diary-card-title { font-size: 14px; font-weight: 600; margin: 0 0 6px 0; }
.diary-card-content { font-size: 13px; line-height: 1.6; color: var(--text-primary, #334155); white-space: pre-wrap; margin-bottom: 8px; }
.diary-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.diary-tag { font-size: 11px; background: var(--bg-surface-2, #f1f5f9); color: var(--text-secondary, #475569); padding: 1px 6px; border-radius: 4px; }

.diary-loading, .diary-empty { text-align: center; padding: 40px; color: var(--text-muted, #94a3b8); }
.empty-icon { font-size: 32px; margin-bottom: 8px; }
.diary-empty h4 { margin: 0 0 6px 0; font-size: 14px; color: var(--text-primary, #334155); }
.diary-empty p { font-size: 12px; max-width: 400px; margin: 0 auto 16px auto; }
</style>
