<template>
  <div class="workspace">
    <div v-if="props.activeExperiment" class="ws-exp-bar">
      <span class="ws-exp-label">当前实验：</span>
      <span class="ws-exp-name">{{ props.activeExperiment.name }}</span>
      <span class="ws-exp-hint">— 记录已按实验归类，可在「双栏→实验管理」中切换</span>
    </div>
    <div class="ws-main">
      <div class="ws-content" :class="{ 'report-mode': showReport }">
        <!-- 返回按钮 (报告模式下显示) -->
        <div v-if="showReport" class="report-back">
          <button class="btn-back" @click="backToList">← 返回记录列表</button>
        </div>

        <template v-if="!showReport">
          <!-- 记录列表 -->
          <div class="ws-section">
            <div class="section-head">
              <h3>实验记录</h3>
              <span class="count-badge">{{ records.length }}</span>
            </div>
            <div class="record-list">
              <div
                v-for="r in records"
                :key="r.id"
                class="record-item"
                :class="{ selected: selectedRecord?.id === r.id }"
                @click="selectRecord(r)"
              >
                <div class="record-item-main">
                  <div class="record-item-task">{{ r.task || r.id }}</div>
                  <div class="record-item-meta">
                    <span v-if="r.dataset" class="chip">{{ r.dataset }}</span>
                    <span v-if="r.model" class="chip">{{ r.model }}</span>
                    <span class="chip-date">{{ r.created_at?.slice(0,10) }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="records.length === 0" class="ws-empty">暂无实验记录</div>
          </div>

          <!-- 报告预览 -->
          <div v-if="selectedRecord" class="ws-section report-section">
            <div class="section-head">
              <h3>实验报告</h3>
              <button class="btn-sm" @click="openFullReport">📖 全屏复盘</button>
            </div>
            <div v-if="reportLoading" class="ws-loading">加载报告...</div>
            <div v-else-if="reportContent" class="report-body" v-html="renderedReport"></div>
            <div v-else class="ws-empty">无报告数据</div>
          </div>
        </template>

        <!-- 全屏报告模式 -->
        <div v-else class="ws-section full-report">
          <div class="section-head">
            <h3>实验复盘报告 — {{ selectedRecord?.task || selectedRecord?.id }}</h3>
          </div>
          <div v-if="reportLoading" class="ws-loading">加载报告...</div>
          <div v-else-if="reportContent" class="report-body" v-html="renderedReport"></div>
          <div v-else class="ws-empty">无报告数据</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { marked } from 'marked'
import { api } from '../api/client'

const props = defineProps({
  selectedRecordId: { type: String, default: '' },
  activeExperiment: { type: Object, default: null },
})
const emit = defineEmits(['select-record'])

const records = ref([])
const selectedRecord = ref(null)
const reportContent = ref('')
const reportLoading = ref(false)
const showReport = ref(false)

const renderedReport = computed(() => {
  if (!reportContent.value) return ''
  return marked.parse(reportContent.value)
})

async function fetchRecords() {
  try { const res = await api.getRecords(); records.value = res.records || [] } catch (e) { console.error(e) }
}

async function selectRecord(r) {
  selectedRecord.value = r
  reportLoading.value = true
  try {
    const res = await api.getRecord(r.id)
    reportContent.value = res.report || res.analysis || ''
  } catch (e) { console.error(e); reportContent.value = '' }
  finally { reportLoading.value = false }
  showReport.value = true
}

// 监听父组件传来的 selectedRecordId（如图谱节点点击）
watch(() => props.selectedRecordId, (id) => {
  if (!id) return
  const r = records.value.find(x => x.id === id)
  if (r) selectRecord(r)
})

function openFullReport() {
  showReport.value = true
}

function backToList() {
  showReport.value = false
  selectedRecord.value = null
  reportContent.value = ''
}

onMounted(() => fetchRecords())
</script>

<style scoped>
.workspace { display: flex; flex-direction: column; height: 100%; overflow: hidden; }
.ws-exp-bar { display: flex; align-items: center; gap: 6px; padding: 5px 14px; background: var(--bg-tertiary); border-bottom: 1px solid var(--border-secondary); font-size: 12px; flex-shrink: 0; }
.ws-exp-label { color: var(--text-tertiary); }
.ws-exp-name { color: var(--text-primary); font-weight: 600; }
.ws-exp-hint { color: var(--text-tertiary); font-size: 11px; }
.ws-main { flex: 1; display: flex; min-height: 0; overflow: hidden; }
.ws-content { flex: 1; display: flex; flex-direction: column; min-width: 0; overflow: hidden; }
.ws-content.report-mode { overflow-y: auto; }

.ws-section { overflow-y: auto; }
.ws-section:first-child:not(.full-report) { flex: 1; min-height: 0; overflow-y: auto; border-bottom: 1px solid var(--border-secondary); }
.report-section { flex: 1; min-height: 0; }
.full-report { flex: 1; min-height: 0; }

/* Report back button */
.report-back { padding: 8px 14px; border-bottom: 1px solid var(--border-secondary); flex-shrink: 0; }
.btn-back { padding: 5px 12px; border: 1px solid var(--border-primary); border-radius: var(--radius-sm); background: var(--bg-primary); font-size: 13px; color: var(--text-secondary); cursor: pointer; }
.btn-back:hover { background: var(--bg-secondary); color: var(--text-primary); }

.section-head { display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; border-bottom: 1px solid var(--border-secondary); flex-shrink: 0; }
.section-head h3 { font-family: var(--font-mono); font-size: 13px; font-weight: 600; }
.count-badge { font-size: 12px; padding: 2px 8px; border: 1px solid var(--border-primary); border-radius: 9px; color: var(--text-tertiary); }
.btn-sm { padding: 4px 10px; border: 1px solid var(--border-primary); border-radius: var(--radius-sm); background: var(--bg-primary); font-size: 12px; color: var(--text-secondary); }
.btn-sm:hover { background: var(--bg-secondary); }

.record-list { padding: 8px; display: flex; flex-direction: column; gap: 3px; }
.record-item { padding: 8px 12px; border-radius: var(--radius-sm); cursor: pointer; }
.record-item:hover { background: var(--bg-secondary); }
.record-item.selected { background: var(--bg-tertiary); }
.record-item-main { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.record-item-task { font-size: 13px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.record-item-meta { display: flex; gap: 6px; }
.chip, .chip-date { font-size: 12px; padding: 1px 6px; border: 1px solid var(--border-secondary); border-radius: 4px; color: var(--text-tertiary); }

.report-body { padding: 14px 16px; line-height: 1.7; font-size: 13px; overflow-y: auto; }
.report-body :deep(h1) { font-size: 18px; margin: 16px 0 10px; border-bottom: 1px solid var(--border-secondary); padding-bottom: 6px; }
.report-body :deep(h2) { font-size: 15px; margin: 14px 0 8px; }
.report-body :deep(h3) { font-size: 14px; margin: 12px 0 6px; color: var(--text-secondary); }
.report-body :deep(code) { font-family: var(--font-mono); font-size: 13px; background: var(--bg-tertiary); padding: 2px 5px; border-radius: 3px; }
.report-body :deep(pre) { background: var(--bg-tertiary); padding: 10px 12px; border-radius: var(--radius-sm); overflow-x: auto; margin: 8px 0; font-size: 13px; }
.report-body :deep(pre code) { background: none; padding: 0; }
.report-body :deep(ul), .report-body :deep(ol) { padding-left: 20px; margin: 6px 0; }
.report-body :deep(li) { margin: 3px 0; font-size: 13px; }
.report-body :deep(blockquote) { border-left: 3px solid var(--border-primary); padding-left: 12px; color: var(--text-secondary); margin: 8px 0; font-size: 13px; }

.ws-empty, .ws-loading { padding: 20px; text-align: center; color: var(--text-tertiary); font-size: 14px; }
</style>
