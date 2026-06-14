<template>
  <div v-if="trace && trace.length" class="agent-trace">
    <button class="trace-toggle" @click="expanded = !expanded">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="13" height="13" :class="{ 'rotated': expanded }">
        <polyline points="9 18 15 12 9 6"/>
      </svg>
      <span class="trace-label">Agent 调用了 {{ trace.length }} 个工具</span>
      <span class="trace-iterations">({{ totalIterations }} 轮迭代)</span>
    </button>
    <transition name="trace-expand">
      <div v-if="expanded" class="trace-details">
        <div v-for="(step, i) in trace" :key="i" class="trace-step">
          <div class="step-header">
            <span class="step-num">{{ step.iteration || i + 1 }}</span>
            <span class="step-tool">{{ formatToolName(step.tool) }}</span>
          </div>
          <div class="step-args">
            <span v-for="(val, key) in step.args" :key="key" class="step-arg">
              <span class="arg-key">{{ key }}</span>
              <span class="arg-val">{{ formatArgValue(val) }}</span>
            </span>
          </div>
          <div v-if="step.result_preview" class="step-result">
            {{ truncate(step.result_preview, 200) }}
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  trace: { type: Array, default: () => [] },
  totalIterations: { type: Number, default: 0 },
})

const expanded = ref(false)

const TOOL_LABELS = {
  search_records: '搜索实验记录',
  search_graph: '搜索知识图谱',
  analyze_data: '数据分析',
  generate_report: '生成报告',
  list_records: '列出记录',
}

function formatToolName(name) {
  return TOOL_LABELS[name] || name
}

function formatArgValue(val) {
  if (Array.isArray(val)) {
    return val.length > 3
      ? `[${val.slice(0, 3).join(', ')}, ...共${val.length}项]`
      : `[${val.join(', ')}]`
  }
  const s = String(val)
  return s.length > 60 ? s.slice(0, 57) + '...' : s
}

function truncate(text, maxLen) {
  if (!text) return ''
  return text.length > maxLen ? text.slice(0, maxLen) + '...' : text
}
</script>

<style scoped>
.agent-trace { margin-top: 6px; }

.trace-toggle {
  display: flex; align-items: center; gap: 5px;
  padding: 4px 8px; border: 1px solid var(--border-secondary);
  border-radius: var(--radius-sm); background: var(--bg-tertiary);
  font-size: 12px; color: var(--text-secondary); cursor: pointer; width: 100%;
}
.trace-toggle:hover { border-color: var(--border-primary); color: var(--text-primary); }
.trace-toggle svg { flex-shrink: 0; }
.trace-toggle svg.rotated { transform: rotate(90deg); }
.trace-label { font-weight: 500; }
.trace-iterations { color: var(--text-tertiary); font-size: 11px; }

.trace-expand-enter-active, .trace-expand-leave-active {
  overflow: hidden; max-height: 500px;
}
.trace-expand-enter-from, .trace-expand-leave-to { max-height: 0; opacity: 0; }

.trace-details {
  margin-top: 6px; display: flex; flex-direction: column; gap: 4px;
  border-left: 2px solid var(--border-secondary); padding-left: 10px;
}

.trace-step {
  padding: 6px 8px; border-radius: var(--radius-sm);
  background: var(--bg-secondary); font-size: 12px;
}

.step-header { display: flex; align-items: center; gap: 6px; margin-bottom: 3px; }
.step-num {
  width: 18px; height: 18px; border-radius: 50%; display: flex;
  align-items: center; justify-content: center; font-size: 10px;
  font-weight: 600; background: var(--border-secondary); color: var(--text-secondary); flex-shrink: 0;
}
.step-tool { font-weight: 500; font-family: var(--font-mono); font-size: 12px; }

.step-args { display: flex; flex-wrap: wrap; gap: 4px 8px; margin-bottom: 3px; }
.step-arg { display: flex; gap: 3px; font-size: 11px; }
.arg-key { color: var(--text-tertiary); font-family: var(--font-mono); }
.arg-val { color: var(--text-secondary); font-family: var(--font-mono); }

.step-result {
  font-size: 11px; color: var(--text-tertiary); font-family: var(--font-mono);
  padding: 3px 6px; background: var(--bg-tertiary); border-radius: 3px;
  line-height: 1.4; word-break: break-all; max-height: 80px; overflow-y: auto;
}
</style>
