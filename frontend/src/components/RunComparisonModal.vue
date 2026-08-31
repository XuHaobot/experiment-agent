<template>
  <div v-if="visible" class="modal-backdrop" @click.self="$emit('close')">
    <div class="modal-dialog">
      <div class="modal-header">
        <div>
          <h3 class="modal-title">📊 Multi-Run Parameter & Metric Comparison</h3>
          <p class="modal-subtitle">横向对比选定运行的输入自变量、实验指标与因果产物</p>
        </div>
        <button class="btn-close" @click="$emit('close')">✕</button>
      </div>

      <div v-if="loading" class="modal-loading">⏳ 正在生成多运行对比矩阵...</div>
      <div v-else-if="matrixData && matrixData.comparison_matrix" class="modal-body">
        <div class="insights-banner">
          <b>💡 洞察总结:</b> {{ matrixData.insights }}
        </div>

        <div class="table-wrap">
          <table class="compare-table">
            <thead>
              <tr>
                <th>属性 / 运行实例</th>
                <th v-for="col in matrixData.comparison_matrix" :key="col.run_id" :class="{ 'best-col': col.run_id === matrixData.best_run_id }">
                  <div class="th-run-id font-mono">{{ col.run_id }}</div>
                  <span v-if="col.run_id === matrixData.best_run_id" class="best-badge">👑 BEST</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr class="section-row"><td :colspan="matrixData.comparison_matrix.length + 1">⚙️ 实验参数 (Parameters)</td></tr>
              <tr v-for="param in matrixData.param_keys" :key="'p_' + param">
                <td class="key-name font-mono">{{ param }}</td>
                <td v-for="col in matrixData.comparison_matrix" :key="col.run_id + '_' + param" class="val-cell">
                  {{ col.parameters[param] }}
                </td>
              </tr>

              <tr class="section-row"><td :colspan="matrixData.comparison_matrix.length + 1">📈 输出指标 (Metrics)</td></tr>
              <tr v-for="metric in matrixData.metric_keys" :key="'m_' + metric">
                <td class="key-name font-mono">{{ metric }}</td>
                <td v-for="col in matrixData.comparison_matrix" :key="col.run_id + '_' + metric" class="val-cell">
                  <b>{{ typeof col.metrics[metric] === 'number' ? (col.metrics[metric] * (col.metrics[metric] <= 1 ? 100 : 1)).toFixed(2) + (col.metrics[metric] <= 1 ? '%' : '') : col.metrics[metric] }}</b>
                </td>
              </tr>

              <tr class="section-row"><td :colspan="matrixData.comparison_matrix.length + 1">📦 产物与元数据 (Metadata)</td></tr>
              <tr>
                <td class="key-name">状态</td>
                <td v-for="col in matrixData.comparison_matrix" :key="col.run_id + '_status'" class="val-cell">
                  <span class="status-badge" :class="col.status">{{ col.status }}</span>
                </td>
              </tr>
              <tr>
                <td class="key-name">产物数</td>
                <td v-for="col in matrixData.comparison_matrix" :key="col.run_id + '_art'" class="val-cell">
                  {{ col.artifacts_count }} 个
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  runIds: { type: Array, default: () => [] },
})

defineEmits(['close'])

const loading = ref(false)
const matrixData = ref(null)

async function fetchComparison() {
  if (!props.runIds || props.runIds.length === 0) return
  loading.value = true
  try {
    const res = await fetch('/api/runs/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ run_ids: props.runIds }),
    })
    if (res.ok) {
      matrixData.value = await res.json()
    }
  } catch (e) {
    console.error('Run comparison fetch failed:', e)
  } finally {
    loading.value = false
  }
}

watch(() => props.visible, (v) => {
  if (v) fetchComparison()
})
</script>

<style scoped>
.modal-backdrop {
  position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 1000;
  display: flex; align-items: center; justify-content: center; padding: 20px;
}
.modal-dialog {
  background: var(--bg-surface-1, #fff); border-radius: 12px; width: 100%; max-width: 900px;
  max-height: 85vh; display: flex; flex-direction: column; box-shadow: 0 10px 30px rgba(0,0,0,0.2);
}
.modal-header {
  padding: 16px 20px; border-bottom: 1px solid var(--border-default, #e2e8f0);
  display: flex; justify-content: space-between; align-items: flex-start;
}
.modal-title { font-size: 16px; margin: 0 0 4px 0; font-weight: 700; }
.modal-subtitle { font-size: 12px; color: var(--text-secondary, #64748b); margin: 0; }
.btn-close { background: none; border: none; font-size: 16px; cursor: pointer; color: var(--text-muted, #94a3b8); }

.modal-body { padding: 16px 20px; overflow-y: auto; }
.insights-banner {
  background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 10px 14px;
  font-size: 12px; color: #166534; margin-bottom: 16px;
}

.table-wrap { overflow-x: auto; }
.compare-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.compare-table th, .compare-table td { border: 1px solid var(--border-default, #e2e8f0); padding: 8px 12px; text-align: left; }
.compare-table th { background: var(--bg-surface-2, #f8fafc); font-weight: 600; }
.th-run-id { font-size: 12px; }
.best-badge { font-size: 10px; background: #fef08a; color: #854d0e; padding: 1px 4px; border-radius: 3px; font-weight: 700; }
.best-col { background: rgba(254, 240, 138, 0.15); }
.section-row td { background: var(--bg-surface-2, #f1f5f9); font-weight: 700; font-size: 11px; color: var(--text-secondary, #475569); }
.key-name { color: var(--text-secondary, #475569); width: 140px; }
.status-badge { font-size: 10px; padding: 1px 5px; border-radius: 3px; font-weight: 600; text-transform: uppercase; }
.status-badge.completed { background: #dcfce7; color: #166534; }
.status-badge.failed { background: #fee2e2; color: #991b1b; }
.modal-loading { text-align: center; padding: 40px; color: var(--text-muted, #94a3b8); }
</style>
