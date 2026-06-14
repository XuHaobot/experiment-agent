<template>
  <div class="analysis-page">
    <div class="page-header">
      <button class="back-btn" @click="$router.push('/')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16">
          <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
        返回
      </button>
      <h1 class="page-title">分析结果</h1>
    </div>

    <div v-if="loading" class="loading-state">加载中...</div>

    <template v-if="record">
      <section class="card">
        <h2 class="card-title">LLM 抽取状态</h2>
        <div class="status-row">
          <span class="status-badge" :class="llmUsed ? 'status-ok' : 'status-warn'">
            {{ llmUsed ? 'LLM 增强' : '规则抽取' }}
          </span>
          <span class="status-hint" v-if="!llmUsed">未配置 LLM API，使用规则抽取</span>
        </div>
      </section>

      <section class="card">
        <h2 class="card-title">Agent 分析过程</h2>
        <div v-if="trace.selected_tools?.length" class="tool-chips">
          <span class="tool-chip" v-for="t in trace.selected_tools" :key="t">{{ t }}</span>
        </div>
        <table class="trace-table" v-if="trace.steps?.length">
          <thead>
            <tr><th>步骤</th><th>工具</th><th>状态</th><th>摘要</th></tr>
          </thead>
          <tbody>
            <tr v-for="(step, i) in trace.steps" :key="i">
              <td>{{ i + 1 }}</td>
              <td class="mono">{{ step.tool }}</td>
              <td><span class="step-status" :class="step.status === 'success' ? 'status-ok' : 'status-warn'">{{ step.status }}</span></td>
              <td class="detail">{{ step.detail }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="card">
        <h2 class="card-title">结构化数据</h2>
        <div class="kv-grid">
          <div class="kv-item"><span class="kv-key">任务</span><span class="kv-val">{{ record.task || '-' }}</span></div>
          <div class="kv-item"><span class="kv-key">数据集</span><span class="kv-val">{{ record.dataset || '-' }}</span></div>
          <div class="kv-item"><span class="kv-key">模型</span><span class="kv-val">{{ record.model || '-' }}</span></div>
        </div>

        <h3 class="sub-title">运行命令</h3>
        <div v-if="record.commands?.length" class="cmd-list">
          <div class="cmd-item" v-for="(cmd, i) in record.commands" :key="i">
            <code>{{ typeof cmd === 'string' ? cmd : cmd.message || cmd.raw || JSON.stringify(cmd) }}</code>
          </div>
        </div>
        <p v-else class="empty-hint">-</p>

        <h3 class="sub-title">参数</h3>
        <div v-if="hasParams" class="params-grid">
          <div class="param-col" v-if="record.params.original && Object.keys(record.params.original).length">
            <span class="param-label">original</span>
            <div class="param-pair" v-for="(v, k) in record.params.original" :key="'o'+k"><code>{{ k }} = {{ v }}</code></div>
          </div>
          <div class="param-col" v-if="record.params.adjusted && Object.keys(record.params.adjusted).length">
            <span class="param-label">adjusted</span>
            <div class="param-pair" v-for="(v, k) in record.params.adjusted" :key="'a'+k"><code>{{ k }} = {{ v }}</code></div>
          </div>
          <div class="param-col" v-if="record.params.suggested && Object.keys(record.params.suggested).length">
            <span class="param-label">suggested</span>
            <div class="param-pair" v-for="(v, k) in record.params.suggested" :key="'s'+k"><code>{{ k }} = {{ v }}</code></div>
          </div>
        </div>
        <p v-else class="empty-hint">-</p>

        <h3 class="sub-title">报错与解决方案</h3>
        <div v-if="record.errors?.length || record.solutions?.length" class="error-solution">
          <div v-if="record.errors?.length">
            <span class="param-label">报错</span>
            <div class="error-item" v-for="(e, i) in record.errors" :key="i">{{ typeof e === 'string' ? e : e.message || e.raw || JSON.stringify(e) }}</div>
          </div>
          <div v-if="record.solutions?.length" style="margin-top:8px">
            <span class="param-label">解决方案</span>
            <div class="solution-item" v-for="(s, i) in record.solutions" :key="i">{{ typeof s === 'string' ? s : s.message || s.raw || JSON.stringify(s) }}</div>
          </div>
        </div>
        <p v-else class="empty-hint">-</p>

        <h3 class="sub-title">结论</h3>
        <p class="conclusion-text">{{ record.conclusion || '-' }}</p>

        <h3 class="sub-title">下一步</h3>
        <p class="next-text">{{ record.next_step || '-' }}</p>
      </section>

      <div class="nav-row">
        <button class="btn-secondary" @click="$router.push(`/report/${record.id}`)">查看报告</button>
        <button class="btn-secondary" @click="$router.push(`/graph`)" v-if="graph">查看图谱</button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api/client'

const route = useRoute()
const record = ref(null)
const graph = ref(null)
const loading = ref(true)

const trace = computed(() => record.value?.agent_trace || {})
const llmUsed = computed(() => record.value?.metadata?.llm_used || false)
const hasParams = computed(() => {
  const p = record.value?.params
  if (!p) return false
  const o = Object.keys(p.original || {}).length
  const a = Object.keys(p.adjusted || {}).length
  const s = Object.keys(p.suggested || {}).length
  return o + a + s > 0
})

onMounted(async () => {
  try {
    const id = route.params.recordId
    const result = await api.getRecord(id)
    record.value = result.record
    graph.value = result.graph
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.analysis-page { max-width: 780px; margin: 0 auto; padding: 24px; }
.page-header { display: flex; align-items: center; gap: 16px; margin-bottom: 28px; }
.back-btn { display: flex; align-items: center; gap: 4px; padding: 6px 12px; border: 1px solid var(--border-primary); border-radius: var(--radius-sm); background: var(--bg-primary); font-size: 12px; color: var(--text-secondary); }
.back-btn:hover { background: var(--bg-secondary); }
.page-title { font-family: var(--font-mono); font-size: 20px; font-weight: 600; }
.card { border: 1px solid var(--border-secondary); border-radius: var(--radius-md); padding: 20px 22px; margin-bottom: 16px; background: var(--bg-primary); }
.card-title { font-size: 13px; font-weight: 600; margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid var(--border-secondary); }
.status-row { display: flex; align-items: center; gap: 10px; }
.status-badge { display: inline-block; padding: 3px 10px; border-radius: 4px; font-size: 11px; font-weight: 500; }
.status-ok { background: #e6f7ed; color: #0d6e2c; }
.status-warn { background: #fef9e7; color: #8a6d14; }
.status-hint { font-size: 12px; color: var(--text-tertiary); }
.tool-chips { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 14px; }
.tool-chip { padding: 3px 10px; border: 1px solid var(--border-primary); border-radius: 4px; font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary); }
.trace-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.trace-table th { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border-secondary); color: var(--text-tertiary); font-weight: 500; font-size: 11px; }
.trace-table td { padding: 6px 8px; border-bottom: 1px solid var(--border-secondary); vertical-align: top; }
.mono { font-family: var(--font-mono); font-size: 11px; }
.detail { color: var(--text-secondary); font-size: 11px; max-width: 280px; }
.step-status { font-size: 10px; padding: 1px 6px; border-radius: 3px; }
.kv-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 16px; }
.kv-item { display: flex; flex-direction: column; gap: 2px; }
.kv-key { font-size: 11px; color: var(--text-tertiary); }
.kv-val { font-size: 13px; font-weight: 500; }
.sub-title { font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-top: 16px; margin-bottom: 8px; }
.cmd-list { display: flex; flex-direction: column; gap: 4px; }
.cmd-item code { font-family: var(--font-mono); font-size: 11px; padding: 6px 10px; background: var(--bg-tertiary); border-radius: 4px; display: block; overflow-x: auto; }
.params-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
.param-col { display: flex; flex-direction: column; gap: 4px; }
.param-label { font-size: 10px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px; display: block; }
.param-pair code { font-family: var(--font-mono); font-size: 11px; }
.error-item, .solution-item { font-size: 12px; color: var(--text-secondary); padding: 4px 0; line-height: 1.5; }
.conclusion-text, .next-text { font-size: 13px; color: var(--text-secondary); line-height: 1.6; }
.empty-hint { font-size: 12px; color: var(--text-tertiary); }
.nav-row { display: flex; gap: 10px; margin-top: 8px; }
.btn-secondary { padding: 8px 18px; border: 1px solid var(--border-primary); border-radius: var(--radius-sm); background: var(--bg-primary); font-size: 13px; color: var(--text-primary); }
.btn-secondary:hover { background: var(--bg-secondary); }
.loading-state { text-align: center; padding: 60px 0; color: var(--text-tertiary); font-size: 14px; }
</style>
