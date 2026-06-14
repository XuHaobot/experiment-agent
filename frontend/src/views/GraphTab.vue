<template>
  <div class="graph-tab">
    <div class="graph-tab-header">
      <select v-model="selectedGraph" @change="loadGraph" class="graph-select">
        <option value="">选择知识图谱...</option>
        <option v-for="g in graphList" :key="g.filename" :value="g.filename">{{ g.filename }}</option>
      </select>
      <button class="btn-sm" @click="fetchGraphList">刷新</button>
    </div>
    <div class="graph-tab-body">
      <div v-if="!graphData && !loading" class="empty-placeholder">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" width="48" height="48" style="opacity:0.3;margin-bottom:14px">
          <circle cx="17" cy="7" r="3"/><circle cx="7" cy="17" r="3"/><line x1="14.3" y1="9.4" x2="9.7" y2="14.6"/>
        </svg>
        <p>选择一个知识图谱开始浏览</p>
      </div>
      <div v-if="loading" class="loading-state">加载知识图谱...</div>
      <KnowledgeGraph v-if="graphData" :data="graphData" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api/client'
import KnowledgeGraph from '../components/KnowledgeGraph.vue'

const emit = defineEmits(['selectRecord'])
const graphList = ref([])
const selectedGraph = ref('')
const graphData = ref(null)
const loading = ref(false)

async function fetchGraphList() {
  try { const res = await api.getGraphList(); graphList.value = res.graphs || [] } catch (e) { console.error(e) }
}

async function loadGraph() {
  if (!selectedGraph.value) return
  loading.value = true
  try { graphData.value = await api.getGraph(selectedGraph.value) } catch (e) { console.error(e); graphData.value = null } finally { loading.value = false }
}

onMounted(() => fetchGraphList())
</script>

<style scoped>
.graph-tab { display: flex; flex-direction: column; height: 100%; }
.graph-tab-header { display: flex; align-items: center; gap: 8px; padding: 8px 14px; border-bottom: 1px solid var(--border-secondary); flex-shrink: 0; }
.graph-select { padding: 6px 10px; border: 1px solid var(--border-primary); border-radius: var(--radius-sm); background: var(--bg-primary); color: var(--text-primary); font-size: 17px; font-family: var(--font-mono); max-width: 350px; }
.btn-sm { padding: 6px 14px; border: 1px solid var(--border-primary); border-radius: var(--radius-sm); background: var(--bg-primary); font-size: 16px; color: var(--text-secondary); }
.btn-sm:hover { background: var(--bg-secondary); }
.graph-tab-body { flex: 1; min-height: 0; overflow: hidden; }
.empty-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-tertiary); font-size: 18px; }
.loading-state { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-tertiary); font-size: 18px; }
</style>
