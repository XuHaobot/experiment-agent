<template>
  <div class="dual-panel">
    <div class="panel-left" :style="{ width: graphExpanded ? '100%' : '55%' }">
      <div class="panel-left-header">
        <select v-model="selectedGraph" @change="loadGraph" class="graph-select">
          <option value="">选择图谱...</option>
          <option v-for="g in graphList" :key="g.filename" :value="g.filename">{{ g.filename }}</option>
        </select>
      </div>
      <div class="panel-left-body">
        <div v-if="!graphData && !graphLoading" class="panel-empty">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" width="42" height="42" style="opacity:0.25;margin-bottom:10px">
            <circle cx="17" cy="7" r="3"/><circle cx="7" cy="17" r="3"/><line x1="14.3" y1="9.4" x2="9.7" y2="14.6"/>
          </svg>
          <p>选择图谱后在此处可视化</p>
        </div>
        <div v-if="graphLoading" class="panel-loading">加载图谱...</div>
        <KnowledgeGraph v-if="graphData" :data="graphData" />
      </div>
    </div>

    <div v-show="!graphExpanded" class="panel-divider" @mousedown="startResize"></div>

    <div v-show="!graphExpanded" class="panel-right">
      <div class="panel-right-tabs">
        <button class="right-tab" :class="{ active: rightTab === 'experiments' }" @click="rightTab = 'experiments'">实验管理</button>
        <button class="right-tab" :class="{ active: rightTab === 'upload' }" @click="rightTab = 'upload'">上传分析</button>
        <button class="right-tab" :class="{ active: rightTab === 'detail' }" @click="rightTab = 'detail'">记录详情</button>
      </div>

      <div class="panel-right-body">
        <!-- Experiments management -->
        <div v-if="rightTab === 'experiments'" class="experiments-section">
          <div class="exp-header">
            <h3>实验管理</h3>
            <button class="btn-primary-sm" @click="showNewExp = true">+ 新建实验</button>
          </div>

          <div v-if="showNewExp" class="exp-new-form">
            <input v-model="newExpName" placeholder="实验名称（如：YOLOv8训练调试）" class="exp-input" @keydown.enter="createExperiment" />
            <textarea v-model="newExpDesc" placeholder="实验描述（可选）" class="exp-textarea" rows="2"></textarea>
            <div class="exp-form-actions">
              <button class="btn-primary-sm" @click="createExperiment" :disabled="!newExpName.trim()">创建</button>
              <button class="btn-cancel" @click="showNewExp = false; newExpName = ''; newExpDesc = ''">取消</button>
            </div>
          </div>

          <div v-if="experiments.length === 0" class="exp-empty">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" width="36" height="36" style="opacity:0.25;margin-bottom:10px">
              <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
            </svg>
            <p>暂无实验项目</p>
            <p class="exp-empty-hint">创建实验后将每次分析归类，方便复盘</p>
          </div>

          <div v-for="exp in experiments" :key="exp.id" class="exp-card" :class="{ active: activeExperiment?.id === exp.id }" @click="selectExperiment(exp)">
            <div class="exp-card-header">
              <span class="exp-card-name">{{ exp.name }}</span>
              <span class="exp-card-count">{{ exp.recordCount || 0 }} 条记录</span>
            </div>
            <div v-if="exp.description" class="exp-card-desc">{{ exp.description }}</div>
            <div class="exp-card-meta">
              <span class="exp-date">{{ exp.created_at?.slice(0, 10) || '' }}</span>
              <button class="exp-delete" @click.stop="deleteExperiment(exp)">删除</button>
            </div>
          </div>

          <!-- 选中实验的关联记录 -->
          <div v-if="activeExperiment" class="exp-related-records">
            <div class="exp-related-title">「{{ activeExperiment.name }}」的关联记录</div>
            <div v-if="expRecords.length === 0" class="exp-no-records">暂无记录 — 上传分析会自动关联到此实验</div>
            <div v-for="r in expRecords" :key="r.id" class="exp-record-item" @click="viewExperimentRecord(r.id)">
              <span class="exp-record-task">{{ r.task || r.id }}</span>
              <span class="exp-record-meta">
                <span v-if="r.dataset" class="chip-sm">{{ r.dataset }}</span>
                <span v-if="r.model" class="chip-sm">{{ r.model }}</span>
                <span class="chip-date-sm">{{ r.created_at?.slice(0,10) }}</span>
              </span>
            </div>
          </div>
        </div>

        <!-- Upload view -->
        <div v-else-if="rightTab === 'upload'" class="upload-section">
          <div class="exp-context-bar" v-if="activeExperiment">
            <span class="ctx-label">当前实验：</span>
            <span class="ctx-name">{{ activeExperiment.name }}</span>
            <button class="ctx-clear" @click="$emit('clear-experiment')">✕</button>
          </div>
          <div class="upload-area" :class="{ drag: isDragging }" @dragover.prevent="isDragging = true" @dragleave="isDragging = false" @drop.prevent="onDrop">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="36" height="36" style="opacity:0.4;margin-bottom:10px">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
            </svg>
            <p class="upload-prompt">拖拽文件，或</p>
            <label class="upload-btn-sm"><input type="file" accept=".txt,.md,.json" @change="onFileChange" hidden />选择文件</label>
            <p class="upload-hint">支持 .txt / .md / .json</p>
            <!-- 文件预览 -->
            <div v-if="file" class="file-preview">
              <span class="file-preview-icon">📄</span>
              <div class="file-preview-info">
                <span class="file-preview-name">{{ file.name }}</span>
                <span class="file-preview-size">{{ formatSize(file.size) }}</span>
              </div>
              <button class="file-preview-clear" @click="file = null">✕</button>
            </div>
            <!-- 文本输入预览 -->
            <div v-else-if="textInput.trim()" class="text-preview-badge">
              已输入 {{ textInput.trim().length }} 字符
            </div>
          </div>
          <div class="divider"><span>或粘贴文本</span></div>
          <textarea v-model="textInput" class="text-input" placeholder="粘贴实验聊天记录、终端日志..." rows="8"></textarea>
          <div class="actions">
            <button class="btn-primary" :disabled="analyzing" @click="startAnalysis">
              {{ analyzing ? '分析中...' : activeExperiment ? `上传到「${activeExperiment.name}」` : '开始分析' }}
            </button>
          </div>
          <div v-if="error" class="error-msg">{{ error }}</div>
          <div v-if="analyzing" class="analyzing-hint">
            <div class="progress-track"><div class="progress-fill" :style="{ width: progress + '%' }"></div></div>
          </div>
        </div>

        <!-- Detail view -->
        <div v-else class="detail-section">
          <div v-if="detailError" class="ws-error">{{ detailError }}</div>
          <div v-if="!selectedRecord" class="detail-picker">
            <p class="detail-picker-hint">从下方选择一条记录查看详情</p>
            <div v-if="allRecords.length === 0" class="panel-empty" style="height:auto;padding:30px 0">
              <p>暂无实验记录</p>
            </div>
            <div v-else class="detail-record-list">
              <div
                v-for="r in allRecords"
                :key="r.id"
                class="detail-record-item"
                @click="loadRecordDetail(r.id)"
              >
                <span class="detail-record-task">{{ r.task || r.id }}</span>
                <span class="detail-record-meta">
                  <span v-if="r.dataset" class="chip-sm">{{ r.dataset }}</span>
                  <span v-if="r.model" class="chip-sm">{{ r.model }}</span>
                  <span class="chip-date-sm">{{ r.created_at?.slice(0,10) }}</span>
                </span>
              </div>
            </div>
          </div>
          <div v-else-if="detailLoading" class="panel-loading">加载中...</div>
          <div v-else-if="recordDetail" class="record-detail">
            <div class="detail-back">
              <button class="btn-back" @click="selectedRecord = null; recordDetail = null; rawRecord = null">← 返回列表</button>
            </div>
            <div class="detail-header">
              <h3>{{ recordDetail.task || recordDetail.id }}</h3>
              <div class="detail-meta">
                <span v-if="recordDetail.dataset" class="meta-chip">{{ recordDetail.dataset }}</span>
                <span v-if="recordDetail.model" class="meta-chip">{{ recordDetail.model }}</span>
                <span v-if="recordDetail.experiment" class="meta-chip exp-chip">{{ recordDetail.experiment }}</span>
              </div>
            </div>
            <div class="detail-body">
              <div v-if="recordDetail.commands?.length" class="detail-block">
                <h4>运行命令</h4>
                <code v-for="(c, i) in recordDetail.commands" :key="i" class="cmd-line">{{ typeof c === 'string' ? c : c.message || JSON.stringify(c) }}</code>
              </div>
              <div v-if="recordDetail.errors?.length" class="detail-block">
                <h4>报错</h4>
                <p v-for="(e, i) in recordDetail.errors" :key="i" class="err-text">{{ typeof e === 'string' ? e : e.message || JSON.stringify(e) }}</p>
              </div>
              <div v-if="recordDetail.solutions?.length" class="detail-block">
                <h4>解决方案</h4>
                <p v-for="(s, i) in recordDetail.solutions" :key="i" class="sol-text">{{ typeof s === 'string' ? s : s.message || JSON.stringify(s) }}</p>
              </div>
              <div v-if="recordDetail.conclusion" class="detail-block">
                <h4>结论</h4>
                <p class="conclusion-text">{{ recordDetail.conclusion }}</p>
              </div>
              <!-- 原始记录文档 - 可翻阅 -->
              <div class="detail-block">
                <h4>原始记录</h4>
                <pre class="raw-record"><code>{{ JSON.stringify(rawRecord, null, 2) }}</code></pre>
              </div>
            </div>
            <!-- 点击式交互：链接到图谱 -->
            <div v-if="recordDetail.graph_file" class="detail-actions">
              <button class="btn-sm" @click="openGraphForRecord(recordDetail)">查看知识图谱</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../api/client'
import KnowledgeGraph from '../components/KnowledgeGraph.vue'

const props = defineProps({
  selectedRecordId: { type: String, default: '' },
  activeExperiment: { type: Object, default: null },
  graphExpanded: { type: Boolean, default: false },
})

const emit = defineEmits(['clear-experiment', 'set-active-experiment'])

// Graph panel
const graphList = ref([])
const selectedGraph = ref('')
const graphData = ref(null)
const graphLoading = ref(false)

// Right panel tabs
const rightTab = ref('upload')

// Upload
const textInput = ref('')
const file = ref(null)
const analyzing = ref(false)
const progress = ref(0)
const isDragging = ref(false)
const error = ref('')

// Detail
const selectedRecord = ref(null)
const recordDetail = ref(null)
const rawRecord = ref(null)
const detailLoading = ref(false)
const detailError = ref('')

// Experiments
const experiments = ref([])
const activeExperiment = ref(props.activeExperiment)
const showNewExp = ref(false)
const newExpName = ref('')
const newExpDesc = ref('')
const allRecords = ref([])

const expRecords = computed(() => {
  if (!activeExperiment.value) return []
  const ids = activeExperiment.value.record_ids || []
  return allRecords.value.filter(r => ids.includes(r.id))
})

async function fetchExperiments() {
  try { const res = await api.getExperiments(); experiments.value = res.experiments || [] } catch (e) { console.error(e) }
}
async function fetchAllRecords() {
  try { const res = await api.getRecords(); allRecords.value = res.records || [] } catch (e) { console.error(e) }
}
async function createExperiment() {
  if (!newExpName.value.trim()) return
  try {
    await api.createExperiment(newExpName.value.trim(), newExpDesc.value.trim())
    newExpName.value = ''; newExpDesc.value = ''; showNewExp.value = false
    await fetchExperiments()
  } catch (e) { console.error(e) }
}
function selectExperiment(exp) {
  activeExperiment.value = exp
  emit('set-active-experiment', exp)
}
async function deleteExperiment(exp) {
  if (!confirm(`确认删除实验「${exp.name}」？记录不会丢失。`)) return
  try {
    await api.deleteExperiment(exp.id)
    if (activeExperiment.value?.id === exp.id) {
      activeExperiment.value = null
      emit('set-active-experiment', null)
    }
    await fetchExperiments()
  } catch (e) { console.error(e) }
}
function viewExperimentRecord(recordId) {
  rightTab.value = 'detail'
  loadRecordDetail(recordId)
}

// Sync activeExperiment from parent prop
watch(() => props.activeExperiment, (val) => {
  if (val && activeExperiment.value?.id !== val.id) {
    activeExperiment.value = val
  }
})

function formatSize(bytes) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}

// Watch for record selection from outside
watch(() => props.selectedRecordId, async (id) => {
  if (!id) return
  rightTab.value = 'detail'
  await loadRecordDetail(id)
})

async function fetchGraphList() {
  try { const res = await api.getGraphList(); graphList.value = res.graphs || [] } catch (e) { console.error(e) }
}
async function loadGraph() {
  if (!selectedGraph.value) return
  graphLoading.value = true
  try { graphData.value = await api.getGraph(selectedGraph.value) } catch (e) { console.error(e); graphData.value = null } finally { graphLoading.value = false }
}
async function loadRecordDetail(id) {
  detailLoading.value = true; detailError.value = ''
  try { const res = await api.getRecord(id); recordDetail.value = res.record; selectedRecord.value = res.record; rawRecord.value = res.record } catch (e) { detailError.value = '加载详情失败：' + (e.message || '未知错误'); recordDetail.value = null; selectedRecord.value = null; rawRecord.value = null; console.error('[loadRecordDetail]', e) } finally { detailLoading.value = false }
}

function onFileChange(e) {
  file.value = e.target.files[0] || null
  if (file.value) textInput.value = ''
}
function onDrop(e) {
  isDragging.value = false
  const f = e.dataTransfer.files[0]
  if (f) { file.value = f; textInput.value = '' }
}

async function startAnalysis() {
  if (!file.value && !textInput.value.trim()) { error.value = '请上传文件或粘贴文本'; return }
  analyzing.value = true; error.value = ''; progress.value = 10
  try {
    let result
    if (file.value) { progress.value = 50; result = await api.analyzeFile(file.value) }
    else { progress.value = 50; result = await api.analyzeText(textInput.value) }
    progress.value = 100
    const recordId = result.record.id
    // 关联到当前实验
    if (activeExperiment.value) {
      try { await api.addRecordToExperiment(recordId, activeExperiment.value.id) } catch (e) { console.error('Failed to associate experiment:', e) }
    }
    rightTab.value = 'detail'
    await loadRecordDetail(recordId)
    // 清空输入
    file.value = null; textInput.value = ''
  } catch (e) {
    error.value = e.message || '分析失败，请重试'
    console.error('[startAnalysis]', e)
  } finally {
    analyzing.value = false
    setTimeout(() => { progress.value = 0 }, 600)
  }
}

function openGraphForRecord(record) {
  // Try to find and load corresponding graph
  const pattern = record.id?.replace(/record-/, 'graph-') || ''
  for (const g of graphList.value) {
    if (g.filename.includes(pattern) || g.filename.includes(record.id?.slice(0, 8))) {
      selectedGraph.value = g.filename
      loadGraph()
      return
    }
  }
  // Fallback: load first graph
  if (graphList.value.length > 0) {
    selectedGraph.value = graphList.value[0].filename
    loadGraph()
  }
}

// Resizer
function startResize(e) {
  const left = document.querySelector('.panel-left')
  const right = document.querySelector('.panel-right')
  const startX = e.clientX
  const startLeft = left.offsetWidth
  function onMove(ev) {
    const dx = ev.clientX - startX
    const newLeft = Math.max(280, Math.min(window.innerWidth - 360, startLeft + dx))
    left.style.width = newLeft + 'px'
    right.style.width = (window.innerWidth - newLeft - 6) + 'px'
  }
  function onUp() {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

onMounted(() => {
  fetchGraphList()
  fetchExperiments()
  fetchAllRecords()
  if (props.selectedRecordId) {
    rightTab.value = 'detail'
    loadRecordDetail(props.selectedRecordId)
  }
})
</script>

<style scoped>
.dual-panel { display: flex; height: 100%; overflow: hidden; }
.panel-left { min-width: 280px; display: flex; flex-direction: column; border-right: 1px solid var(--border-secondary); }
.panel-left-header { display: flex; align-items: center; gap: 6px; padding: 8px 12px; border-bottom: 1px solid var(--border-secondary); flex-shrink: 0; }
.graph-select { padding: 5px 8px; border: 1px solid var(--border-primary); border-radius: var(--radius-sm); background: var(--bg-primary); color: var(--text-primary); font-size: 13px; font-family: var(--font-mono); max-width: 250px; }
.panel-left-body { flex: 1; min-height: 0; overflow: hidden; }
.panel-empty, .panel-loading { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-tertiary); font-size: 14px; }

.panel-divider { width: 5px; cursor: col-resize; background: var(--border-secondary); flex-shrink: 0; }
.panel-divider:hover { background: var(--border-primary); }

.panel-right { flex: 1; min-width: 300px; display: flex; flex-direction: column; overflow: hidden; }
.panel-right-tabs { display: flex; border-bottom: 1px solid var(--border-secondary); flex-shrink: 0; }
.right-tab { flex: 1; padding: 8px 12px; border: none; background: transparent; font-size: 13px; font-weight: 500; color: var(--text-secondary); border-bottom: 2px solid transparent; transition: none; }
.right-tab:hover { color: var(--text-primary); background: var(--bg-secondary); }
.right-tab.active { color: var(--text-primary); border-bottom-color: var(--accent); font-weight: 600; }
.panel-right-body { flex: 1; overflow-y: auto; min-height: 0; }

/* Upload */
.upload-section { padding: 16px; }
.exp-context-bar { display: flex; align-items: center; gap: 6px; padding: 6px 10px; background: var(--bg-tertiary); border-radius: var(--radius-sm); margin-bottom: 14px; font-size: 12px; }
.ctx-label { color: var(--text-tertiary); }
.ctx-name { color: var(--text-primary); font-weight: 600; }
.ctx-clear { width: 20px; height: 20px; border: 1px solid var(--border-primary); border-radius: 4px; background: transparent; font-size: 11px; color: var(--text-tertiary); cursor: pointer; margin-left: auto; }
.ctx-clear:hover { color: var(--text-primary); }
.upload-area { border: 1.5px dashed var(--border-primary); border-radius: var(--radius-md); padding: 24px 16px; text-align: center; background: var(--bg-secondary); }
.upload-area.drag { border-color: var(--accent); background: var(--bg-tertiary); }
.upload-prompt { font-size: 14px; color: var(--text-secondary); margin-bottom: 10px; }
.upload-btn-sm { display: inline-block; padding: 5px 14px; border: 1px solid var(--border-primary); border-radius: var(--radius-sm); font-size: 13px; font-weight: 500; background: var(--bg-primary); cursor: pointer; }
.upload-btn-sm:hover { border-color: var(--accent); }
.upload-hint { font-size: 12px; color: var(--text-tertiary); margin-top: 8px; }
/* File preview */
.file-preview { display: flex; align-items: center; gap: 10px; margin-top: 14px; padding: 8px 12px; background: var(--bg-primary); border: 1px solid var(--border-secondary); border-radius: var(--radius-sm); }
.file-preview-icon { font-size: 20px; }
.file-preview-info { display: flex; flex-direction: column; gap: 2px; }
.file-preview-name { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.file-preview-size { font-size: 11px; color: var(--text-tertiary); }
.file-preview-clear { width: 22px; height: 22px; border: 1px solid var(--border-primary); border-radius: 4px; background: transparent; font-size: 12px; color: var(--text-tertiary); cursor: pointer; margin-left: auto; flex-shrink: 0; }
.file-preview-clear:hover { color: #dc2626; border-color: #fecaca; }
.text-preview-badge { margin-top: 14px; padding: 6px 12px; background: var(--bg-tertiary); border-radius: var(--radius-sm); font-size: 12px; color: var(--text-secondary); }
.divider { display: flex; align-items: center; margin: 18px 0; color: var(--text-tertiary); font-size: 13px; }
.divider::before, .divider::after { content: ''; flex: 1; height: 1px; background: var(--border-secondary); }
.divider span { padding: 0 10px; }
.text-input { width: 100%; border: 1px solid var(--border-primary); border-radius: var(--radius-sm); padding: 10px 12px; font-family: var(--font-mono); font-size: 13px; line-height: 1.5; resize: vertical; background: var(--bg-primary); color: var(--text-primary); }
.text-input:focus { outline: none; border-color: var(--accent); }
.text-input::placeholder { color: var(--text-tertiary); }
.actions { margin-top: 14px; display: flex; justify-content: flex-end; }
.btn-primary { padding: 7px 22px; border: none; border-radius: var(--radius-sm); background: var(--accent); color: var(--bg-primary); font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover:not(:disabled) { opacity: 0.85; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.error-msg { margin-top: 12px; padding: 8px 12px; background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; border-radius: var(--radius-sm); font-size: 13px; }
.analyzing-hint { margin-top: 16px; }
.progress-track { height: 4px; background: var(--border-secondary); border-radius: 2px; overflow: hidden; }
.progress-fill { height: 100%; background: var(--accent); transition: width 0.4s ease; }

/* Detail */
.detail-section { padding: 14px; height: 100%; overflow-y: auto; }
.ws-error { margin: 10px 14px; padding: 8px 12px; background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; border-radius: var(--radius-sm); font-size: 13px; }
.detail-picker { padding: 10px 0; }
.detail-picker-hint { font-size: 13px; color: var(--text-tertiary); margin-bottom: 14px; text-align: center; }
.detail-record-list { display: flex; flex-direction: column; gap: 5px; }
.detail-record-item { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border: 1px solid var(--border-secondary); border-radius: var(--radius-sm); cursor: pointer; }
.detail-record-item:hover { border-color: var(--border-primary); background: var(--bg-secondary); }
.detail-record-task { font-size: 13px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 55%; }
.detail-record-meta { display: flex; gap: 6px; }
.record-detail { display: flex; flex-direction: column; gap: 0; }
.detail-back { margin-bottom: 8px; }
.btn-back { padding: 4px 10px; border: 1px solid var(--border-primary); border-radius: var(--radius-sm); background: var(--bg-primary); font-size: 12px; color: var(--text-secondary); cursor: pointer; }
.btn-back:hover { background: var(--bg-secondary); color: var(--text-primary); }
.raw-record { font-family: var(--font-mono); font-size: 12px; line-height: 1.5; background: var(--bg-tertiary); border: 1px solid var(--border-secondary); border-radius: var(--radius-sm); padding: 12px; overflow: auto; max-height: 320px; white-space: pre-wrap; word-break: break-all; color: var(--text-secondary); }
.detail-header { margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid var(--border-secondary); }
.detail-header h3 { font-family: var(--font-mono); font-size: 14px; font-weight: 600; margin-bottom: 6px; }
.detail-meta { display: flex; gap: 8px; flex-wrap: wrap; }
.meta-chip { font-size: 12px; padding: 2px 7px; border: 1px solid var(--border-secondary); border-radius: 4px; color: var(--text-tertiary); }
.exp-chip { background: var(--bg-tertiary); color: var(--text-secondary); font-weight: 500; }
.detail-block { margin-bottom: 14px; }
.detail-block h4 { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px; }
.cmd-line { display: block; font-family: var(--font-mono); font-size: 13px; padding: 4px 8px; background: var(--bg-tertiary); border-radius: 4px; margin-bottom: 4px; overflow-x: auto; }
.err-text, .sol-text, .conclusion-text { font-size: 13px; color: var(--text-secondary); line-height: 1.6; }
.detail-actions { margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--border-secondary); }
.btn-sm { padding: 4px 12px; border: 1px solid var(--border-primary); border-radius: var(--radius-sm); background: var(--bg-primary); font-size: 12px; color: var(--text-secondary); cursor: pointer; }
.btn-sm:hover { background: var(--bg-secondary); }

/* Experiments */
.experiments-section { padding: 14px; height: 100%; overflow-y: auto; }
.exp-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.exp-header h3 { font-family: var(--font-mono); font-size: 14px; font-weight: 600; }
.btn-primary-sm { padding: 5px 14px; border: none; border-radius: var(--radius-sm); background: var(--accent); color: var(--bg-primary); font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary-sm:hover { opacity: 0.85; }
.btn-primary-sm:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-cancel { padding: 5px 14px; border: 1px solid var(--border-primary); border-radius: var(--radius-sm); background: var(--bg-primary); font-size: 13px; color: var(--text-secondary); cursor: pointer; margin-left: 8px; }
.exp-new-form { display: flex; flex-direction: column; gap: 8px; margin-bottom: 14px; padding: 12px; background: var(--bg-secondary); border: 1px solid var(--border-secondary); border-radius: var(--radius-md); }
.exp-input { padding: 6px 10px; border: 1px solid var(--border-primary); border-radius: var(--radius-sm); font-size: 13px; font-family: var(--font-sans); background: var(--bg-primary); color: var(--text-primary); }
.exp-input:focus { outline: none; border-color: var(--accent); }
.exp-textarea { padding: 6px 10px; border: 1px solid var(--border-primary); border-radius: var(--radius-sm); font-size: 13px; font-family: var(--font-sans); resize: vertical; background: var(--bg-primary); color: var(--text-primary); }
.exp-form-actions { display: flex; }
.exp-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 30px 20px; text-align: center; }
.exp-empty p { font-size: 14px; color: var(--text-tertiary); }
.exp-empty-hint { font-size: 12px !important; margin-top: 6px; }
.exp-card { padding: 11px 14px; border-bottom: 1px solid var(--border-secondary); cursor: pointer; }
.exp-card.active { background: var(--bg-secondary); border-left: 3px solid var(--accent); padding-left: 11px; }
.exp-card:hover { background: var(--bg-secondary); }
.exp-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.exp-card-name { font-size: 13px; font-weight: 600; }
.exp-card-count { font-size: 12px; color: var(--text-tertiary); }
.exp-card-desc { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }
.exp-card-meta { display: flex; justify-content: space-between; align-items: center; margin-top: 6px; }
.exp-date { font-size: 11px; color: var(--text-tertiary); }
.exp-delete { padding: 2px 8px; border: 1px solid var(--border-secondary); border-radius: var(--radius-sm); background: transparent; font-size: 12px; color: var(--text-tertiary); cursor: pointer; }
.exp-delete:hover { border-color: #fecaca; color: #dc2626; }
.exp-related-records { margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border-secondary); }
.exp-related-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 10px; }
.exp-no-records { font-size: 12px; color: var(--text-tertiary); font-style: italic; padding: 12px 0; }
.exp-record-item { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border: 1px solid var(--border-secondary); border-radius: var(--radius-sm); margin-bottom: 5px; cursor: pointer; }
.exp-record-item:hover { border-color: var(--border-primary); background: var(--bg-secondary); }
.exp-record-task { font-size: 13px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 55%; }
.exp-record-meta { display: flex; gap: 6px; }
.chip-sm, .chip-date-sm { font-size: 11px; padding: 1px 6px; border: 1px solid var(--border-secondary); border-radius: 4px; color: var(--text-tertiary); }
</style>
