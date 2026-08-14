<template>
  <div class="timeline-overlay" @click.self="$emit('close')">
    <div class="timeline-box">
      <div class="timeline-header">
        <div>
          <h2>实验时间线</h2>
          <p class="timeline-sub">按时间顺序回顾全部实验记录，点击任意节点查看详情</p>
        </div>
        <button class="btn-secondary" @click="$emit('close')">关闭</button>
      </div>

      <div v-if="loading" class="timeline-state">加载中...</div>
      <div v-else-if="!groups.length" class="timeline-state">暂无实验记录，上传日志后将在此按时间沉淀</div>

      <div v-else class="timeline-scroll">
        <div v-for="g in groups" :key="g.date" class="tl-day">
          <div class="tl-day-head">
            <span class="tl-day-dot"></span>
            <span class="tl-day-label">{{ g.date }}</span>
            <span class="tl-day-count">{{ g.items.length }} 条</span>
          </div>

          <div class="tl-items">
            <div
              v-for="r in g.items"
              :key="r.id"
              class="tl-item"
              :class="{ selected: r.id === selectedId }"
              @click="$emit('select', r)"
            >
              <span class="tl-item-time">{{ formatTime(r.created_at) }}</span>
              <span class="tl-node"></span>
              <div class="tl-card">
                <div class="tl-card-title">{{ r.task || r.id }}</div>
                <div class="tl-card-meta">
                  <span v-if="r.dataset" class="chip">{{ truncate(r.dataset, 16) }}</span>
                  <span v-if="r.model" class="chip">{{ r.model }}</span>
                  <span v-if="r.filename" class="chip chip-src">{{ truncate(r.filename, 20) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api/client'

const props = defineProps({ selectedId: { type: String, default: '' } })
const emit = defineEmits(['close', 'select'])

const loading = ref(true)
const records = ref([])

function truncate(s, n) {
  if (!s) return ''
  return s.length > n ? s.slice(0, n) + '…' : s
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const groups = computed(() => {
  const sorted = [...records.value].sort((a, b) => (a.created_at || '').localeCompare(b.created_at || ''))
  const map = new Map()
  for (const r of sorted) {
    const d = new Date(r.created_at)
    const date = isNaN(d.getTime())
      ? '未知日期'
      : d.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'short' })
    if (!map.has(date)) map.set(date, [])
    map.get(date).push(r)
  }
  return Array.from(map.entries()).map(([date, items]) => ({ date, items: items.reverse() }))
})

onMounted(async () => {
  try {
    const res = await api.getRecords()
    records.value = res?.records || []
  } catch (e) {
    records.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.timeline-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
}
.timeline-box {
  width: 720px;
  max-width: 92vw;
  height: 82vh;
  max-height: 82vh;
  background: var(--card-bg, #fff);
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
}
.timeline-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid var(--border-secondary, rgba(0, 0, 0, 0.08));
}
.timeline-header h2 {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: -0.02em;
}
.timeline-sub {
  font-size: 12px;
  color: var(--text-tertiary, rgba(0, 0, 0, 0.4));
  margin-top: 4px;
}
.timeline-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary, rgba(0, 0, 0, 0.4));
  font-size: 13px;
  padding: 24px;
  text-align: center;
}
.timeline-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 8px 22px 22px;
}
.tl-day { margin-top: 18px; }
.tl-day-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.tl-day-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #F3A04C;
  flex-shrink: 0;
}
.tl-day-label { font-size: 13px; font-weight: 600; color: var(--text-primary, rgba(0, 0, 0, 0.8)); }
.tl-day-count {
  font-size: 11px;
  color: var(--text-tertiary, rgba(0, 0, 0, 0.4));
  background: var(--bg-secondary, rgba(0, 0, 0, 0.05));
  padding: 1px 8px;
  border-radius: 10px;
}
.tl-items { position: relative; padding-left: 4px; }
.tl-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 8px 10px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s;
  position: relative;
}
.tl-item:hover { background: var(--bg-secondary, rgba(0, 0, 0, 0.04)); }
.tl-item.selected { background: color-mix(in srgb, #F3A04C 12%, transparent); }
/* 连接竖线 */
.tl-item::before {
  content: '';
  position: absolute;
  left: 58px;
  top: 26px;
  bottom: -8px;
  width: 1.5px;
  background: var(--border-secondary, rgba(0, 0, 0, 0.1));
}
.tl-item:last-child::before { display: none; }
.tl-item-time {
  width: 44px;
  flex-shrink: 0;
  font-size: 11px;
  color: var(--text-tertiary, rgba(0, 0, 0, 0.4));
  padding-top: 4px;
  text-align: right;
}
.tl-node {
  width: 10px;
  height: 10px;
  margin-top: 6px;
  border-radius: 50%;
  background: var(--card-bg, #fff);
  border: 2px solid #F3A04C;
  flex-shrink: 0;
  z-index: 1;
}
.tl-item.selected .tl-node { background: #F3A04C; }
.tl-card { flex: 1; min-width: 0; }
.tl-card-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary, rgba(0, 0, 0, 0.8));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tl-card-meta { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 5px; }
.chip {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 8px;
  background: var(--bg-secondary, rgba(0, 0, 0, 0.05));
  color: var(--text-secondary, rgba(0, 0, 0, 0.5));
}
.chip-src { color: var(--text-tertiary, rgba(0, 0, 0, 0.4)); }
.btn-secondary {
  padding: 6px 16px;
  border: 1px solid var(--border-primary, rgba(0, 0, 0, 0.12));
  border-radius: 8px;
  background: var(--bg-primary, #fff);
  font-size: 13px;
  cursor: pointer;
}
.btn-secondary:hover { border-color: #F3A04C; }
</style>
