<template>
  <div class="graph-page">
    <div class="page-header">
      <h1 class="page-title">知识图谱</h1>
      <div class="graph-controls">
        <select v-model="selectedGraph" @change="loadGraph" class="graph-select">
          <option value="">选择图谱...</option>
          <option v-for="g in graphList" :key="g.filename" :value="g.filename">{{ g.filename }}</option>
        </select>
        <button class="btn-secondary" @click="fetchGraphList">刷新</button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">加载知识图谱...</div>

    <div v-if="graphData" class="graph-container">
      <KnowledgeGraph :data="graphData" />
    </div>

    <div v-if="!graphData && !loading" class="empty-hint">
      选择一个知识图谱来可视化，或在分析实验记录后自动生成。
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api/client'
import KnowledgeGraph from '../components/KnowledgeGraph.vue'

const route = useRoute()
const graphList = ref([])
const selectedGraph = ref(route.params.graphFile || '')
const graphData = ref(null)
const loading = ref(false)

async function fetchGraphList() {
  try {
    const res = await api.getGraphList()
    graphList.value = res.graphs || []
  } catch (e) {
    console.error(e)
  }
}

async function loadGraph() {
  if (!selectedGraph.value) return
  loading.value = true
  try {
    graphData.value = await api.getGraph(selectedGraph.value)
  } catch (e) {
    console.error(e)
    graphData.value = null
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await fetchGraphList()
  if (selectedGraph.value) {
    await loadGraph()
  }
})
</script>

<style scoped>
.graph-page { max-width: 1100px; margin: 0 auto; padding: 24px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; flex-wrap: wrap; gap: 12px; }
.page-title { font-family: var(--font-mono); font-size: 20px; font-weight: 600; }
.graph-controls { display: flex; gap: 8px; align-items: center; }
.graph-select { padding: 7px 12px; border: 1px solid var(--border-primary); border-radius: var(--radius-sm); background: var(--bg-primary); color: var(--text-primary); font-size: 12px; font-family: var(--font-mono); max-width: 280px; }
.btn-secondary { padding: 7px 14px; border: 1px solid var(--border-primary); border-radius: var(--radius-sm); background: var(--bg-primary); font-size: 12px; color: var(--text-primary); cursor: pointer; }
.btn-secondary:hover { background: var(--bg-secondary); }
.graph-container { border: 1px solid var(--border-secondary); border-radius: var(--radius-md); overflow: hidden; height: calc(100vh - 140px); min-height: 500px; }
.loading-state, .empty-hint { text-align: center; padding: 60px 0; color: var(--text-tertiary); font-size: 14px; }
</style>
