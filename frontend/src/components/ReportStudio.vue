<template>
  <div class="report-studio">
    <div class="rs-header">
      <div>
        <h2 class="rs-title">报告工坊</h2>
        <p class="rs-sub">汇总当前对话与实验记录，一键产出报告</p>
      </div>
      <div class="rs-actions">
        <button class="rs-btn ghost" @click="downloadMd">下载 Markdown</button>
        <button class="rs-btn primary" @click="printPdf">打印 / PDF</button>
      </div>
    </div>

    <div class="rs-meta">
      <span class="rs-chip">对话 {{ messages.length }} 条</span>
      <span class="rs-chip">记录 {{ records.length }} 条</span>
      <span v-if="selectedRecord" class="rs-chip accent">{{ selectedRecord.task || selectedRecord.id }}</span>
      <span class="rs-chip">{{ nowText }}</span>
    </div>

    <div class="rs-body">
      <div class="rs-preview" v-html="rendered"></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  records: { type: Array, default: () => [] },
  selectedRecord: { type: Object, default: null },
})

marked.setOptions({ breaks: true, gfm: true })

const nowText = new Date().toLocaleString('zh-CN', { hour12: false })

const md = computed(() => {
  const lines = []
  lines.push('# 实验研究复盘报告')
  lines.push('')
  lines.push(`> 自动生成于 ${nowText}`)
  lines.push('')
  if (props.selectedRecord) {
    const r = props.selectedRecord
    lines.push('## 当前聚焦实验')
    lines.push('')
    lines.push(`- **标识**：${r.task || r.id}`)
    if (r.dataset) lines.push(`- **数据集**：${r.dataset}`)
    if (r.model) lines.push(`- **模型**：${r.model}`)
    lines.push('')
  }
  // 对话问答
  const qa = props.messages.filter(m => m.role === 'user' || m.role === 'assistant')
  if (qa.length) {
    lines.push('## 研究对话纪要')
    lines.push('')
    for (const m of qa) {
      if (m.role === 'user') lines.push(`**Q：${m.content}**`)
      else lines.push(m.content)
      lines.push('')
    }
  }
  // 记录清单
  if (props.records.length) {
    lines.push('## 实验记录清单')
    lines.push('')
    lines.push('| 标识 | 数据集 | 模型 | 时间 |')
    lines.push('| --- | --- | --- | --- |')
    for (const r of props.records.slice(0, 30)) {
      lines.push(`| ${r.task || r.id} | ${r.dataset || '-'} | ${r.model || '-'} | ${r.created_at || '-'} |`)
    }
    lines.push('')
  }
  lines.push('---')
  lines.push('*由 Experiment Agent 报告工坊生成*')
  return lines.join('\n')
})

const rendered = computed(() => marked.parse(md.value))

function downloadMd() {
  const blob = new Blob([md.value], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `实验报告_${Date.now()}.md`
  a.click()
  URL.revokeObjectURL(url)
}

function printPdf() {
  const w = window.open('', '_blank')
  if (!w) return
  w.document.write(`<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
  <title>实验研究复盘报告</title>
  <style>
    body{font-family:system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;max-width:760px;margin:40px auto;padding:0 24px;color:#1a1a1e;line-height:1.7}
    h1{font-size:24px;border-bottom:2px solid #2F6BFF;padding-bottom:8px}
    h2{font-size:18px;margin-top:28px;color:#2F6BFF}
    blockquote{border-left:3px solid #2F6BFF;margin:0;padding:6px 12px;color:#555;background:#f6f7f9}
    table{border-collapse:collapse;width:100%;margin:12px 0;font-size:13px}
    th,td{border:1px solid #eaeae0;padding:6px 9px;text-align:left}
    th{background:#f6f7f9}
    code{background:#f1f2f4;padding:1px 5px;border-radius:4px;font-size:12px}
    pre{background:#0e0e10;color:#f4f4f5;padding:12px;border-radius:8px;overflow:auto}
    @media print{body{margin:0}}
  </style></head><body>${rendered.value}</body></html>`)
  w.document.close()
  setTimeout(() => w.print(), 250)
}
</script>

<style scoped>
.report-studio { display: flex; flex-direction: column; height: 100%; background: var(--panel-bg); }
.rs-header { display: flex; align-items: flex-start; justify-content: space-between; padding: 16px 16px 8px; gap: 10px; }
.rs-title { font-size: 15px; font-weight: 600; color: var(--text-primary); }
.rs-sub { font-size: 11px; color: var(--text-tertiary); margin-top: 2px; }
.rs-actions { display: flex; gap: 7px; flex-shrink: 0; }
.rs-btn { font-size: 12px; padding: 6px 11px; border-radius: 8px; cursor: pointer; border: 1px solid transparent; transition: .15s; }
.rs-btn.primary { background: var(--accent); color: #fff; }
.rs-btn.primary:hover { background: var(--accent-hover); }
.rs-btn.ghost { background: var(--bg-tertiary); color: var(--text-secondary); border-color: var(--border-primary); }
.rs-btn.ghost:hover { border-color: var(--accent); color: var(--accent); }
.rs-meta { display: flex; flex-wrap: wrap; gap: 6px; padding: 0 16px 10px; }
.rs-chip { font-size: 10.5px; color: var(--text-secondary); background: var(--bg-tertiary); border-radius: 6px; padding: 2px 8px; }
.rs-chip.accent { background: rgba(47,107,255,0.10); color: var(--accent); }
.rs-body { flex: 1; overflow-y: auto; padding: 0 16px 24px; }
.rs-preview { font-size: 13px; line-height: 1.7; color: var(--text-secondary); }
.rs-preview :deep(h1) { font-size: 19px; color: var(--text-primary); border-bottom: 2px solid var(--accent); padding-bottom: 6px; }
.rs-preview :deep(h2) { font-size: 15px; color: var(--accent); margin-top: 18px; }
.rs-preview :deep(blockquote) { border-left: 3px solid var(--accent); margin: 10px 0; padding: 6px 12px; background: var(--bg-tertiary); color: var(--text-secondary); }
.rs-preview :deep(table) { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 12px; }
.rs-preview :deep(th), .rs-preview :deep(td) { border: 1px solid var(--border-primary); padding: 5px 8px; text-align: left; }
.rs-preview :deep(code) { background: var(--bg-tertiary); padding: 1px 5px; border-radius: 4px; font-size: 11px; }
.rs-preview :deep(pre) { background: #0e0e10; color: #f4f4f5; padding: 12px; border-radius: 8px; overflow: auto; }
</style>
