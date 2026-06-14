<template>
  <div class="history-page">
    <div class="page-header">
      <h1 class="page-title">实验记忆</h1>
      <div class="search-box">
        <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="15" height="15">
          <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
        </svg>
        <input v-model="query" @input="doSearch" placeholder="搜索 task / dataset / model / errors..." />
      </div>
    </div>

    <div v-if="!query" class="records-section">
      <div class="section-head">
        <span>全部实验记录</span>
        <span class="count-badge">{{ records.length }}</span>
      </div>

      <div v-if="loading" class="loading-state">加载中...</div>

      <div v-if="!loading && records.length === 0" class="empty-state">
        <p>还没有实验记录</p>
        <button class="btn-secondary" @click="$router.push('/')">上传第一份记录</button>
      </div>

      <div class="record-list">
        <div class="record-card" v-for="r in records" :key="r.id" @click="$router.push(`/analysis/${r.id}`)">
          <div class="record-main">
            <div class="record-task">{{ r.task || r.id }}</div>
            <div class="record-meta">
              <span v-if="r.dataset" class="meta-chip">{{ r.dataset }}</span>
              <span v-if="r.model" class="meta-chip">{{ r.model }}</span>
              <span class="meta-date">{{ formatDate(r.created_at) }}</span>
            </div>
          </div>
          <svg class="record-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16">
            <path d="M9 18l6-6-6-6"/>
          </svg>
        </div>
      </div>
    </div>

    <div v-else>
      <div class="section-head">
        <span>搜索结果</span>
        <span class="count-badge">{{ searchResults.length }}</span>
      </div>

      <div v-if="searchResults.length === 0" class="empty-state">
        <p>没有找到匹配 "{{ query }}" 的结果</p>
      </div>

      <div class="record-list">
        <div class="record-card" v-for="r in searchResults" :key="r.filename" @click="$router.push(`/analysis/${r.filename?.replace('.json', '')}`)">
          <div class="record-main">
            <div class="record-task">{{ r.filename || r.id }}</div>
            <div class="record-meta">
              <span v-if="r.dataset" class="meta-chip">{{ r.dataset }}</span>
              <span v-if="r.model" class="meta-chip">{{ r.model }}</span>
              <span v-if="r.matched_fields?.length" class="meta-chip highlight">命中: {{ r.matched_fields.join(', ') }}</span>
            </div>
          </div>
          <svg class="record-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16">
            <path d="M9 18l6-6-6-6"/>
          </svg>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

const records = ref([])
const query = ref('')
const searchResults = ref([])
const loading = ref(true)

function formatDate(d) {
  if (!d) return ''
  try {
    return new Date(d).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch {
    return String(d).slice(0, 16)
  }
}

async function doSearch() {
  if (!query.value.trim()) {
    searchResults.value = []
    return
  }
  try {
    const res = await api.search(query.value)
    searchResults.value = res.records || []
  } catch (e) {
    console.error(e)
    searchResults.value = []
  }
}

onMounted(async () => {
  try {
    const res = await api.getRecords()
    records.value = res.records || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.history-page { max-width: 860px; margin: 0 auto; padding: 24px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 28px; flex-wrap: wrap; gap: 14px; }
.page-title { font-family: var(--font-mono); font-size: 20px; font-weight: 600; }
.search-box { display: flex; align-items: center; gap: 8px; padding: 8px 14px; border: 1px solid var(--border-primary); border-radius: var(--radius-sm); background: var(--bg-primary); width: 280px; }
.search-box input { border: none; outline: none; font-size: 13px; font-family: inherit; background: transparent; color: var(--text-primary); width: 100%; }
.search-box input::placeholder { color: var(--text-tertiary); }
.search-icon { color: var(--text-tertiary); flex-shrink: 0; }
.section-head { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; font-size: 13px; font-weight: 500; color: var(--text-secondary); }
.count-badge { font-size: 11px; padding: 1px 7px; border: 1px solid var(--border-primary); border-radius: 10px; color: var(--text-tertiary); }
.record-list { display: flex; flex-direction: column; gap: 6px; }
.record-card { display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; border: 1px solid var(--border-secondary); border-radius: var(--radius-sm); cursor: pointer; transition: border-color 0.15s, background 0.15s; background: var(--bg-primary); }
.record-card:hover { border-color: var(--border-primary); background: var(--bg-secondary); }
.record-main { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.record-task { font-size: 14px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.record-meta { display: flex; gap: 6px; flex-wrap: wrap; }
.meta-chip { font-size: 11px; padding: 1px 7px; border: 1px solid var(--border-secondary); border-radius: 3px; color: var(--text-tertiary); }
.meta-chip.highlight { border-color: var(--accent); color: var(--text-primary); background: var(--bg-tertiary); }
.meta-date { font-size: 11px; color: var(--text-tertiary); }
.record-arrow { color: var(--text-tertiary); flex-shrink: 0; }
.loading-state, .empty-state { text-align: center; padding: 60px 0; color: var(--text-tertiary); font-size: 14px; }
.empty-state { display: flex; flex-direction: column; align-items: center; gap: 14px; }
.btn-secondary { padding: 8px 18px; border: 1px solid var(--border-primary); border-radius: var(--radius-sm); background: var(--bg-primary); font-size: 13px; color: var(--text-primary); cursor: pointer; }
.btn-secondary:hover { background: var(--bg-secondary); }
</style>
