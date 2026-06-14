<template>
  <div class="report-page">
    <div class="page-header">
      <button class="back-btn" @click="$router.push(`/analysis/${recordId}`)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16">
          <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
        返回分析
      </button>
      <h1 class="page-title">实验复盘报告</h1>
    </div>

    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="report" class="report-body" v-html="rendered"></div>
    <div v-else class="empty">暂无报告</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { marked } from 'marked'
import { api } from '../api/client'

const route = useRoute()
const recordId = route.params.recordId
const report = ref('')
const loading = ref(true)

const rendered = computed(() => {
  if (!report.value) return ''
  return marked.parse(report.value)
})

onMounted(async () => {
  try {
    const result = await api.getRecord(recordId)
    report.value = result.report || ''
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.report-page { max-width: 780px; margin: 0 auto; padding: 24px; }
.page-header { display: flex; align-items: center; gap: 16px; margin-bottom: 28px; }
.back-btn { display: flex; align-items: center; gap: 4px; padding: 6px 12px; border: 1px solid var(--border-primary); border-radius: var(--radius-sm); background: var(--bg-primary); font-size: 12px; color: var(--text-secondary); cursor: pointer; }
.back-btn:hover { background: var(--bg-secondary); }
.page-title { font-family: var(--font-mono); font-size: 20px; font-weight: 600; }
.report-body { border: 1px solid var(--border-secondary); border-radius: var(--radius-md); padding: 28px 32px; background: var(--bg-primary); line-height: 1.8; font-size: 14px; }
.report-body :deep(h1) { font-size: 20px; margin: 24px 0 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border-secondary); }
.report-body :deep(h2) { font-size: 17px; margin: 20px 0 10px; }
.report-body :deep(h3) { font-size: 14px; margin: 16px 0 8px; color: var(--text-secondary); }
.report-body :deep(code) { font-family: var(--font-mono); font-size: 12px; background: var(--bg-tertiary); padding: 2px 6px; border-radius: 3px; }
.report-body :deep(pre) { background: var(--bg-tertiary); padding: 14px 18px; border-radius: var(--radius-sm); overflow-x: auto; margin: 12px 0; }
.report-body :deep(pre code) { background: none; padding: 0; }
.report-body :deep(ul), .report-body :deep(ol) { padding-left: 20px; margin: 8px 0; }
.report-body :deep(li) { margin: 4px 0; }
.report-body :deep(table) { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }
.report-body :deep(th), .report-body :deep(td) { padding: 8px 12px; border: 1px solid var(--border-secondary); text-align: left; }
.report-body :deep(th) { background: var(--bg-secondary); font-weight: 500; }
.report-body :deep(blockquote) { border-left: 3px solid var(--border-primary); padding-left: 14px; color: var(--text-secondary); margin: 12px 0; }
.report-body :deep(hr) { border: none; border-top: 1px solid var(--border-secondary); margin: 24px 0; }
.loading-state, .empty { text-align: center; padding: 60px 0; color: var(--text-tertiary); font-size: 14px; }
</style>
