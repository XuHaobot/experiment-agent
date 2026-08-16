<script setup>
import { ref } from 'vue'
import { api } from '../api/client'

const props = defineProps({
  show: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const running = ref(false)
const result = ref(null)
const errorMsg = ref('')

async function run() {
  running.value = true
  errorMsg.value = ''
  try {
    const r = await api.runEval()
    result.value = r
  } catch (e) {
    errorMsg.value = e.message || '评测运行失败'
  } finally {
    running.value = false
  }
}

function close() {
  emit('close')
}
</script>

<template>
  <div v-if="show" class="modal-overlay" @click.self="close">
    <div class="modal-box eval-modal">
      <div class="eval-header">
        <h3>🧪 评测集自动化回归</h3>
        <button class="btn-icon" @click="close">✕</button>
      </div>
      <p class="eval-sub">
        基于 LLM-as-Judge + 字段覆盖率，对固化评测集自动打分。
        每次改动模型/提示词后跑一遍，确保关键指标不回退（迭代不降质）。
      </p>

      <div v-if="!result && !running && !errorMsg" class="eval-actions">
        <button class="btn-primary" @click="run">运行评测</button>
        <span class="eval-note">注：会消耗服务端 LLM token，公网只读模式下不可用。</span>
      </div>

      <div v-else-if="running" class="eval-running">评测运行中（逐条分析 + 裁判打分）…</div>

      <div v-else-if="errorMsg" class="eval-error">
        {{ errorMsg }}
        <div v-if="errorMsg.includes('演示模式') || errorMsg.includes('只读')" class="eval-note">
          评测回归需在本地完整实例（已配置 LLM）运行。
        </div>
      </div>

      <div v-else-if="result" class="eval-result">
        <div class="eval-summary">
          <div class="metric">
            <div class="metric-num">{{ (result.pass_rate * 100).toFixed(0) }}%</div>
            <div class="metric-label">通过率</div>
          </div>
          <div class="metric">
            <div class="metric-num">{{ result.passed }}/{{ result.total }}</div>
            <div class="metric-label">通过 / 总数</div>
          </div>
          <div class="metric">
            <div class="metric-num">{{ result.avg_combined }}</div>
            <div class="metric-label">平均分(综合)</div>
          </div>
          <div class="metric">
            <div class="metric-num">{{ result.avg_judge }}</div>
            <div class="metric-label">平均分(裁判)</div>
          </div>
        </div>

        <table class="eval-table">
          <thead>
            <tr><th>样例</th><th>字段</th><th>裁判</th><th>综合</th><th>结果</th><th>备注</th></tr>
          </thead>
          <tbody>
            <tr v-for="c in result.cases" :key="c.id">
              <td class="cell-id">{{ c.id }}</td>
              <td>{{ c.field_score }}</td>
              <td>{{ c.judge_score }}</td>
              <td>{{ c.combined }}</td>
              <td>
                <span :class="c.passed ? 'tag-pass' : 'tag-fail'">
                  {{ c.passed ? '通过' : '未过' }}
                </span>
              </td>
              <td class="cell-note">{{ c.notes.join('；') }}</td>
            </tr>
          </tbody>
        </table>

        <div class="eval-actions">
          <button class="btn-secondary" @click="run">重新运行</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
}
.eval-modal {
  width: 720px;
  max-width: 94vw;
  max-height: 84vh;
  overflow-y: auto;
  background: var(--card-bg, #fff);
  border-radius: 14px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
  padding: 18px 22px;
}
.eval-header { display: flex; align-items: center; justify-content: space-between; }
.eval-header h3 { margin: 0; font-size: 16px; }
.btn-icon {
  border: none; background: transparent; cursor: pointer; font-size: 16px;
  color: var(--text-tertiary, rgba(0, 0, 0, 0.4)); width: 28px; height: 28px;
  border-radius: 6px;
}
.btn-icon:hover { background: var(--bg-secondary, rgba(0, 0, 0, 0.06)); }
.eval-sub { font-size: 12px; color: var(--text-tertiary, rgba(0, 0, 0, 0.4)); margin: 6px 0 14px; line-height: 1.6; }
.eval-actions { display: flex; align-items: center; gap: 12px; margin-top: 8px; }
.eval-note { font-size: 11px; color: var(--text-tertiary, rgba(0, 0, 0, 0.4)); }
.eval-running { font-size: 13px; color: #C2410C; padding: 20px 0; }
.eval-error { font-size: 13px; color: #b91c1c; padding: 16px 0; }

.btn-primary {
  padding: 8px 18px; border: none; border-radius: 8px;
  background: #F3A04C; color: #fff; font-size: 13px; font-weight: 600; cursor: pointer;
}
.btn-primary:hover { opacity: 0.9; }
.btn-secondary {
  padding: 6px 16px; border: 1px solid var(--border-primary, rgba(0, 0, 0, 0.12));
  border-radius: 8px; background: var(--bg-primary, #fff); font-size: 13px; cursor: pointer;
}
.btn-secondary:hover { border-color: #F3A04C; }

.eval-summary { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.metric {
  flex: 1; min-width: 110px; background: var(--bg-secondary, rgba(0, 0, 0, 0.04)); border: 1px solid var(--border-secondary, rgba(0, 0, 0, 0.1));
  border-radius: 10px; padding: 10px 12px; text-align: center;
}
.metric-num { font-size: 22px; font-weight: 700; color: var(--text-primary, rgba(0, 0, 0, 0.8)); }
.metric-label { font-size: 11px; color: var(--text-tertiary, rgba(0, 0, 0, 0.4)); margin-top: 2px; }

.eval-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.eval-table th, .eval-table td { border: 1px solid var(--border-secondary, rgba(0, 0, 0, 0.1)); padding: 6px 8px; text-align: left; }
.eval-table th { background: var(--bg-secondary, rgba(0, 0, 0, 0.04)); color: var(--text-primary, rgba(0, 0, 0, 0.8)); font-weight: 600; }
.cell-id { font-family: monospace; color: var(--text-secondary, rgba(0, 0, 0, 0.5)); }
.cell-note { color: var(--text-tertiary, rgba(0, 0, 0, 0.4)); max-width: 220px; }
.tag-pass { color: #15803d; background: #dcfce7; padding: 1px 8px; border-radius: 999px; font-weight: 600; }
.tag-fail { color: #b91c1c; background: #fee2e2; padding: 1px 8px; border-radius: 999px; font-weight: 600; }
</style>
