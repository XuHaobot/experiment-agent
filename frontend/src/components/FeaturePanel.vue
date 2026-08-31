<template>
  <div class="feature-panel">
    <div class="fp-header">
      <div>
        <h2 class="fp-title">功能库</h2>
        <p class="fp-sub">预置科研工具 · 点击即唤起</p>
      </div>
    </div>

    <div class="fp-search">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="15" height="15"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input v-model="query" placeholder="搜索功能，如：对比 / 原型 / 报告" />
    </div>

    <div class="fp-body">
      <section v-for="cat in filtered" :key="cat.key" class="fp-cat">
        <div class="fp-cat-head">
          <span class="fp-cat-ico" v-html="cat.icon"></span>
          <span class="fp-cat-name">{{ cat.name }}</span>
          <span class="fp-cat-count">{{ cat.items.length }}</span>
        </div>
        <div class="fp-grid">
          <button
            v-for="f in cat.items"
            :key="f.id"
            class="fp-card"
            @click="$emit('activate', f)"
          >
            <span class="fp-card-ico" v-html="f.icon"></span>
            <span class="fp-card-name">{{ f.name }}</span>
            <span class="fp-card-desc">{{ f.desc }}</span>
            <span class="fp-card-cmd" v-if="f.cmd">/{{ f.cmd }}</span>
          </button>
        </div>
      </section>
      <div v-if="filtered.length === 0" class="fp-empty">没有匹配「{{ query }}」的功能</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

defineEmits(['activate'])

const query = ref('')

const I = {
  analyze: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="16" height="16"><path d="M3 3v18h18"/><path d="M7 14l3-4 3 3 4-6"/></svg>',
  write: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="16" height="16"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>',
  visual: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="16" height="16"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
  engine: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="16" height="16"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
  compare: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="16" height="16"><path d="M3 3v18h18"/><path d="M7 15l4-5 3 3 5-7"/></svg>',
  anomaly: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="16" height="16"><path d="M12 2l10 18H2z"/><line x1="12" y1="9" x2="12" y2="14"/><circle cx="12" cy="17" r="0.6"/></svg>',
  sensitivity: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="16" height="16"><path d="M3 12h4l3-8 4 16 3-8h4"/></svg>',
  significance: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="16" height="16"><path d="M5 19V5"/><path d="M5 19h14"/><circle cx="9" cy="14" r="2"/><circle cx="15" cy="9" r="2"/></svg>',
  report: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="16" height="16"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="13" y2="17"/></svg>',
  paper: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="16" height="16"><path d="M4 4h11l5 5v11a0 0 0 0 1 0 0H4z"/><line x1="8" y1="12" x2="16" y2="12"/><line x1="8" y1="16" x2="14" y2="16"/></svg>',
  weekly: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="16" height="16"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="16" y1="2" x2="16" y2="6"/></svg>',
  defense: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="16" height="16"><path d="M12 2L4 5v6c0 5 3.5 8.5 8 11 4.5-2.5 8-6 8-11V5z"/></svg>',
  prototype: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="16" height="16"><rect x="3" y="3" width="18" height="14" rx="2"/><line x1="3" y1="8" x2="21" y2="8"/><line x1="8" y1="21" x2="16" y2="21"/></svg>',
  arch: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="16" height="16"><rect x="3" y="3" width="6" height="6" rx="1"/><rect x="15" y="3" width="6" height="6" rx="1"/><rect x="9" y="15" width="6" height="6" rx="1"/><path d="M6 9v3h12V9M12 12v3"/></svg>',
  mindmap: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="16" height="16"><circle cx="12" cy="12" r="2.5"/><circle cx="4" cy="5" r="2"/><circle cx="4" cy="19" r="2"/><circle cx="20" cy="12" r="2"/><path d="M10 10.5 5.5 6M10 13.5 5.5 18M14 12h4"/></svg>',
  chart: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="16" height="16"><path d="M3 3v18h18"/><rect x="7" y="11" width="3" height="7"/><rect x="13" y="7" width="3" height="11"/></svg>',
  explain: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="16" height="16"><circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.8.4-1 .9-1 1.7"/><circle cx="12" cy="17" r="0.6"/></svg>',
  bug: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="16" height="16"><rect x="8" y="6" width="8" height="12" rx="4"/><path d="M8 10H4M8 14H4M16 10h4M16 14h4M9 6l2-3M15 6l-2-3"/></svg>',
  env: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="16" height="16"><path d="M4 17l6-6 4 4 6-7"/><circle cx="4" cy="17" r="1.5"/><circle cx="10" cy="11" r="1.5"/><circle cx="14" cy="15" r="1.5"/><circle cx="20" cy="8" r="1.5"/></svg>',
  log: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="16" height="16"><path d="M4 6h16M4 12h16M4 18h10"/></svg>',
}

const categories = [
  {
    key: 'analyze', name: '科研分析', icon: I.analyze,
    items: [
      { id: 'compare', name: '实验对比', desc: '多实验指标并排 + 差异提取', cmd: 'compare', icon: I.compare, action: 'prompt' },
      { id: 'anomaly', name: '异常检测', desc: '自动抓训练异常 epoch/loss', cmd: 'anomaly', icon: I.anomaly, action: 'prompt' },
      { id: 'sensitivity', name: '敏感度分析', desc: '参数敏感性扫描', cmd: 'sensitivity', icon: I.sensitivity, action: 'prompt' },
      { id: 'significance', name: '显著性检验', desc: '统计显著性 p 值', cmd: 'significance', icon: I.significance, action: 'prompt' },
    ]
  },
  {
    key: 'write', name: '知识写作', icon: I.write,
    items: [
      { id: 'report', name: '报告工坊', desc: '对话+指标一键生成报告', icon: I.report, action: 'report' },
      { id: 'paper', name: '文献速读', desc: '贴 arXiv 出方法/贡献/局限', cmd: 'paper', icon: I.paper, action: 'prompt' },
      { id: 'weekly', name: '周报进展', desc: '生成本周实验进展', cmd: 'weekly', icon: I.weekly, action: 'prompt' },
      { id: 'defense', name: '答辩大纲', desc: '从记录生成答辩结构', cmd: 'defense', icon: I.defense, action: 'prompt' },
    ]
  },
  {
    key: 'visual', name: '可视化与原型', icon: I.visual,
    items: [
      { id: 'prototype', name: '画原型图', desc: '文字描述直接出 UI 线框', icon: I.prototype, action: 'prototype' },
      { id: 'arch', name: '架构图', desc: '把系统/流程画成图', cmd: 'arch', icon: I.arch, action: 'prompt' },
      { id: 'mindmap', name: '思维导图', desc: '概念/方案结构梳理', cmd: 'mindmap', icon: I.mindmap, action: 'prompt' },
      { id: 'chart', name: '数据图表', desc: '可编辑图表生成', cmd: 'chart', icon: I.chart, action: 'prompt' },
    ]
  },
  {
    key: 'engine', name: '工程效率', icon: I.engine,
    items: [
      { id: 'explain', name: '代码解释', desc: '逐段讲清代码逻辑', cmd: 'explain', icon: I.explain, action: 'prompt' },
      { id: 'bug', name: 'Bug 诊断', desc: '报错根因与修复建议', cmd: 'bug', icon: I.bug, action: 'prompt' },
      { id: 'env', name: '环境快照', desc: '导出依赖与环境信息', cmd: 'env', icon: I.env, action: 'prompt' },
      { id: 'log', name: '日志摘要', desc: '长日志浓缩为要点', cmd: 'log', icon: I.log, action: 'prompt' },
    ]
  },
]

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return categories
  return categories
    .map(c => ({
      ...c,
      items: c.items.filter(f =>
        f.name.toLowerCase().includes(q) ||
        (f.cmd && f.cmd.includes(q)) ||
        f.desc.toLowerCase().includes(q)
      )
    }))
    .filter(c => c.items.length > 0)
})
</script>

<style scoped>
.feature-panel { display: flex; flex-direction: column; height: 100%; background: var(--panel-bg); }
.fp-header { padding: 16px 16px 8px; }
.fp-title { font-size: 15px; font-weight: 600; color: var(--text-primary); }
.fp-sub { font-size: 11px; color: var(--text-tertiary); margin-top: 2px; }
.fp-search {
  display: flex; align-items: center; gap: 6px;
  margin: 4px 16px 10px; padding: 7px 10px;
  background: var(--bg-tertiary); border-radius: 9px; color: var(--text-tertiary);
}
.fp-search input { border: none; background: transparent; outline: none; flex: 1; font-size: 12.5px; color: var(--text-primary); }
.fp-body { flex: 1; overflow-y: auto; padding: 0 16px 20px; }
.fp-cat { margin-bottom: 16px; }
.fp-cat-head { display: flex; align-items: center; gap: 7px; margin-bottom: 9px; color: var(--text-secondary); }
.fp-cat-name { font-size: 12px; font-weight: 600; }
.fp-cat-ico { display: flex; color: var(--accent); }
.fp-cat-count { font-size: 10px; color: var(--text-tertiary); background: var(--bg-tertiary); border-radius: 6px; padding: 1px 6px; }
.fp-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.fp-card {
  text-align: left; cursor: pointer;
  border: 1px solid var(--border-primary); background: var(--card-bg);
  border-radius: 10px; padding: 10px; display: flex; flex-direction: column; gap: 3px;
  transition: border-color .15s, transform .1s, box-shadow .15s; position: relative;
}
.fp-card:hover { border-color: var(--accent); box-shadow: 0 4px 14px rgba(47,107,255,0.10); transform: translateY(-1px); }
.fp-card-ico { color: var(--accent); display: flex; }
.fp-card-name { font-size: 12.5px; font-weight: 600; color: var(--text-primary); }
.fp-card-desc { font-size: 10.5px; color: var(--text-tertiary); line-height: 1.4; }
.fp-card-cmd { position: absolute; top: 9px; right: 9px; font-size: 10px; color: var(--accent); background: rgba(47,107,255,0.10); border-radius: 5px; padding: 1px 5px; font-family: var(--font-mono); }
.fp-empty { text-align: center; color: var(--text-tertiary); font-size: 12px; padding: 30px 0; }
</style>
