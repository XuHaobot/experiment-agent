<template>
  <div class="kg-layout">
    <div class="kg-main" ref="container">
      <div class="kg-toolbar">
        <div class="toolbar-left">
          <span class="toolbar-stat">实体 <strong>{{ stats.entities }}</strong></span>
          <span class="toolbar-stat">关系 <strong>{{ stats.relations }}</strong></span>
        </div>
        <div class="toolbar-right">
          <input v-model="search" placeholder="搜索实体/关系..." class="kg-search" />
          <button class="kg-legend-btn" @click="showLegend = !showLegend">图例</button>
        </div>
      </div>
      <div v-if="showLegend" class="kg-legend">
        <div v-for="g in legendGroups" :key="g.type" class="legend-item">
          <span class="legend-dot" :style="{ background: g.color }"></span>
          <span>{{ g.type }}</span>
        </div>
      </div>
      <div class="kg-svg-wrap" ref="svgWrap">
        <svg ref="svgEl"></svg>
      </div>
    </div>

    <div v-if="selectedNode" class="kg-detail-divider" @mousedown="startDetailResize"></div>

    <!-- 右侧详情面板 -->
    <div v-if="selectedNode" class="kg-detail-panel" ref="detailPanel">
      <div class="detail-header">
        <h3>实体详情</h3>
        <button class="detail-close" @click="selectedNode = null">✕</button>
      </div>
      <div class="detail-type-tag" :style="{ background: colorByType(selectedNode.type) }">
        {{ selectedNode.type }}
      </div>
      <h4 class="detail-name">{{ selectedNode.name }}</h4>
      <div v-if="nodeProperties.length" class="detail-properties">
        <div class="props-title">属性</div>
        <div v-for="p in nodeProperties" :key="p.key" class="detail-prop">
          <span class="dp-key">{{ p.key }}</span>
          <span class="dp-val">{{ p.val }}</span>
        </div>
      </div>
      <div class="detail-relations">
        <div class="props-title">关联关系 ({{ connectedRelations.length }})</div>
        <div v-for="r in connectedRelations" :key="r.id" class="detail-rel">
          <span class="rel-source" @click="focusNode(r.sourceId)">{{ r.sourceName }}</span>
          <span class="rel-type">→ {{ r.type }} →</span>
          <span class="rel-target" @click="focusNode(r.targetId)">{{ r.targetName }}</span>
        </div>
        <div v-if="connectedRelations.length === 0" class="rel-empty">无关联关系</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as d3 from 'd3'

const props = defineProps({ data: { type: Object, required: true } })
const container = ref(null)
const svgEl = ref(null)
const svgWrap = ref(null)
const detailPanel = ref(null)
const search = ref('')
const showLegend = ref(false)
const selectedNode = ref(null)

const stats = computed(() => ({
  entities: props.data?.entities?.length || 0,
  relations: props.data?.relations?.length || 0,
}))

const nodeProperties = computed(() => {
  if (!selectedNode.value?.properties) return []
  return Object.entries(selectedNode.value.properties)
    .filter(([_, v]) => v !== '' && v !== null && v !== undefined)
    .map(([k, v]) => ({ key: k, val: String(v) }))
})

const connectedRelations = computed(() => {
  if (!selectedNode.value || !props.data?.relations) return []
  const nid = selectedNode.value.id
  const nodeMap = new Map((props.data.entities || []).map(e => [e.id, e.name]))
  return props.data.relations
    .filter(r => r.source === nid || r.target === nid)
    .map(r => ({
      id: `${r.source}-${r.target}-${r.type}`,
      sourceId: r.source, targetId: r.target,
      sourceName: nodeMap.get(r.source) || r.source,
      targetName: nodeMap.get(r.target) || r.target,
      type: r.type,
    }))
})

const TYPE_COLORS = {
  Experiment: '#000000', Dataset: '#378ADD', Model: '#534AB7',
  Command: '#D85A30', Parameter: '#1D9E75', Error: '#E24B4A',
  Solution: '#0F6E56', Conclusion: '#993C1D', NextStep: '#639922',
}
const legendGroups = computed(() => {
  const types = new Set((props.data?.entities || []).map(e => e.type))
  return [...types].map(t => ({ type: t, color: TYPE_COLORS[t] || '#888' }))
})
function colorByType(type) { return TYPE_COLORS[type] || '#888' }
function truncate(str, max = 24) { if (!str || str.length <= max) return str; return str.slice(0, max - 1) + '\u2026' }

const filteredEntities = computed(() => {
  const entities = props.data?.entities || []
  if (!search.value.trim()) return entities
  const q = search.value.toLowerCase()
  const matchedIds = new Set()
  for (const e of entities) { if (e.name?.toLowerCase().includes(q) || e.type?.toLowerCase().includes(q)) matchedIds.add(e.id) }
  for (const r of (props.data?.relations || [])) { if (r.type?.toLowerCase().includes(q)) { matchedIds.add(r.source); matchedIds.add(r.target) } }
  if (matchedIds.size === 0) return entities
  return entities.filter(e => matchedIds.has(e.id))
})

const filteredRelations = computed(() => {
  const relations = props.data?.relations || []
  if (!search.value.trim()) return relations
  const entityIds = new Set(filteredEntities.value.map(e => e.id))
  return relations.filter(r => entityIds.has(r.source) && entityIds.has(r.target))
})

let simulation = null, resizeObserver = null

function startDetailResize(e) {
  const main = container.value
  const panel = detailPanel.value
  if (!main || !panel) return
  const startX = e.clientX
  const startMain = main.offsetWidth
  const layoutWidth = main.parentElement.offsetWidth
  const startPanel = panel.offsetWidth

  // 拖拽期间禁止文字选中
  document.body.style.userSelect = 'none'
  document.body.style.webkitUserSelect = 'none'

  function onMove(ev) {
    const dx = ev.clientX - startX
    const newMain = Math.max(200, Math.min(layoutWidth - 240, startMain + dx))
    const newPanel = layoutWidth - newMain - 5
    main.style.width = newMain + 'px'
    main.style.flex = 'none'
    panel.style.width = newPanel + 'px'
    panel.style.flex = 'none'
  }
  function onUp() {
    document.body.style.userSelect = ''
    document.body.style.webkitUserSelect = ''
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

// 关闭或切换实体详情面板时重置拖拽产生的内联样式
function resetPanelLayout() {
  const main = container.value
  const panel = detailPanel.value
  if (main) { main.style.width = ''; main.style.flex = '' }
  if (panel) { panel.style.width = ''; panel.style.flex = '' }
}

watch(selectedNode, (nv) => {
  if (!nv) nextTick(resetPanelLayout)
})

function focusNode(nodeId) {
  selectedNode.value = (props.data?.entities || []).find(e => e.id === nodeId) || null
}

function render() {
  if (!svgEl.value || !svgWrap.value || !props.data) return
  const wrap = svgWrap.value
  const width = wrap.clientWidth || 800
  const height = wrap.clientHeight || 500
  if (width < 50 || height < 50) return

  const svg = d3.select(svgEl.value)
  svg.selectAll('*').remove()
  svg.attr('width', width).attr('height', height)

  const entities = filteredEntities.value
  const relations = filteredRelations.value
  if (entities.length === 0) return

  const nameIndex = new Map(entities.map(n => [n.id, n]))
  const links = relations
    .filter(r => nameIndex.has(r.source) && nameIndex.has(r.target))
    .map(r => ({ source: r.source, target: r.target, type: r.type }))

  const nodes = entities.map(n => ({ ...n, radius: 18 + Math.min((n.name || '').length * 0.8, 20) }))

  const g = svg.append('g')
  const zoom = d3.zoom().scaleExtent([0.1, 4]).on('zoom', (event) => { g.attr('transform', event.transform) })
  svg.call(zoom)
  svg.call(zoom.transform, d3.zoomIdentity)

  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(160))
    .force('charge', d3.forceManyBody().strength(-400))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(d => d.radius + 16))
    .alphaDecay(0.02)

  // 关系线
  const link = g.append('g').selectAll('line').data(links).enter().append('line')
    .attr('stroke', '#bbb').attr('stroke-width', 1).attr('stroke-opacity', 0.4)
    .attr('stroke-dasharray', d => d.type?.includes('SOLVED') || d.type?.includes('ADJUSTS') ? '5,3' : null)

  // 关系标签
  const linkLabel = g.append('g').selectAll('text').data(links).enter().append('text')
    .attr('font-size', 10).attr('fill', '#999').attr('text-anchor', 'middle').attr('dy', -6)
    .text(d => truncate(d.type?.replace(/_/g, ' '), 16))

  // 节点组
  const node = g.append('g').selectAll('g').data(nodes).enter().append('g')
    .attr('cursor', 'pointer')
    .on('click', (event, d) => {
      event.stopPropagation()
      selectedNode.value = d
      highlightNode(d)
    })
    .call(d3.drag()
      .on('start', (event, d) => { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y })
      .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y })
      .on('end', (event, d) => { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null }))

  // 节点圆形（小点）
  node.append('circle')
    .attr('r', d => 6 + Math.min((n => n === 'Experiment' ? 4 : 0)(d.type), 4))
    .attr('fill', d => colorByType(d.type))
    .attr('stroke', '#fff').attr('stroke-width', 1.5)
    .attr('class', 'kg-node-circle')

  // 节点文字（圆右侧）
  node.append('text').attr('dx', 10).attr('dy', 4)
    .attr('font-size', 11).attr('font-family', 'ui-sans-serif, system-ui, sans-serif')
    .attr('fill', '#444').attr('font-weight', 500)
    .text(d => truncate(d.name, 20))

  svg.on('click', () => {
    selectedNode.value = null
    clearHighlight()
  })

  /** 高亮选中节点及其关联边 */
  function highlightNode(d) {
    const connectedIds = new Set([d.id])
    links.forEach(l => {
      const sid = typeof l.source === 'object' ? l.source.id : l.source
      const tid = typeof l.target === 'object' ? l.target.id : l.target
      if (sid === d.id) connectedIds.add(tid)
      if (tid === d.id) connectedIds.add(sid)
    })

    // 高亮关联边：红色加粗
    link
      .attr('stroke', l => {
        const sid = typeof l.source === 'object' ? l.source.id : l.source
        const tid = typeof l.target === 'object' ? l.target.id : l.target
        return (sid === d.id || tid === d.id) ? '#E24B4A' : '#ddd'
      })
      .attr('stroke-width', l => {
        const sid = typeof l.source === 'object' ? l.source.id : l.source
        const tid = typeof l.target === 'object' ? l.target.id : l.target
        return (sid === d.id || tid === d.id) ? 2.5 : 0.5
      })
      .attr('stroke-opacity', l => {
        const sid = typeof l.source === 'object' ? l.source.id : l.source
        const tid = typeof l.target === 'object' ? l.target.id : l.target
        return (sid === d.id || tid === d.id) ? 0.9 : 0.15
      })

    // 高亮关联标签
    linkLabel
      .attr('fill', l => {
        const sid = typeof l.source === 'object' ? l.source.id : l.source
        const tid = typeof l.target === 'object' ? l.target.id : l.target
        return (sid === d.id || tid === d.id) ? '#E24B4A' : '#ccc'
      })
      .attr('font-weight', l => {
        const sid = typeof l.source === 'object' ? l.source.id : l.source
        const tid = typeof l.target === 'object' ? l.target.id : l.target
        return (sid === d.id || tid === d.id) ? 600 : 400
      })

    // 节点透明度：非关联节点变淡
    node.select('.kg-node-circle')
      .attr('r', n => {
        const base = 6 + (n.type === 'Experiment' ? 4 : 0)
        return n.id === d.id ? base + 3 : base
      })
      .attr('fill-opacity', n => connectedIds.has(n.id) ? 1 : 0.2)
      .attr('stroke-width', n => n.id === d.id ? 2.5 : 1.5)

    node.selectAll('text')
      .attr('opacity', n => connectedIds.has(n.id) ? 1 : 0.25)
      .attr('font-weight', n => n.id === d.id ? 700 : 500)
  }

  /** 清除高亮 */
  function clearHighlight() {
    link.attr('stroke', '#bbb').attr('stroke-width', 1).attr('stroke-opacity', 0.4)
    linkLabel.attr('fill', '#999').attr('font-weight', 400)
    node.select('.kg-node-circle')
      .attr('r', n => 6 + (n.type === 'Experiment' ? 4 : 0))
      .attr('fill-opacity', 1).attr('stroke-width', 1.5)
    node.selectAll('text').attr('opacity', 1).attr('font-weight', 500)
  }

  // 监听 selectedNode 变化来清除高亮
  const unwatchSelected = watch(selectedNode, (nv) => {
    if (!nv) clearHighlight()
  })

  // 存储 unwatch 以便清理
  if (svgEl.value._unwatchHighlight) svgEl.value._unwatchHighlight()
  svgEl.value._unwatchHighlight = unwatchSelected

  simulation.on('tick', () => {
    link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y)
    linkLabel.attr('x', d => (d.source.x + d.target.x) / 2).attr('y', d => (d.source.y + d.target.y) / 2)
    node.attr('transform', d => `translate(${d.x},${d.y})`)
  })
}

watch(() => props.data, () => nextTick(render), { deep: true })
watch(search, () => nextTick(render))

onMounted(() => {
  nextTick(render)
  if (container.value) {
    resizeObserver = new ResizeObserver(() => nextTick(render))
    resizeObserver.observe(container.value)
  }
})
onBeforeUnmount(() => {
  if (simulation) simulation.stop()
  if (resizeObserver) resizeObserver.disconnect()
})
</script>

<style scoped>
.kg-layout { display: flex; width: 100%; height: 100%; overflow: hidden; }
.kg-main { flex: 1; display: flex; flex-direction: column; min-width: 0; background: var(--bg-primary); }
.kg-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; border-bottom: 1px solid var(--border-secondary); gap: 10px; flex-shrink: 0; }
.toolbar-left { display: flex; gap: 18px; }
.toolbar-stat { font-size: 13px; color: var(--text-secondary); }
.toolbar-stat strong { color: var(--text-primary); font-size: 13px; }
.toolbar-right { display: flex; gap: 8px; align-items: center; }
.kg-search { padding: 5px 8px; border: 1px solid var(--border-primary); border-radius: var(--radius-sm); font-size: 13px; background: var(--bg-primary); color: var(--text-primary); width: 160px; font-family: var(--font-mono); }
.kg-search:focus { outline: none; border-color: var(--accent); }
.kg-legend-btn { padding: 4px 10px; border: 1px solid var(--border-primary); border-radius: var(--radius-sm); background: var(--bg-primary); font-size: 13px; color: var(--text-secondary); cursor: pointer; }
.kg-legend-btn:hover { background: var(--bg-secondary); }
.kg-legend { display: flex; gap: 14px; padding: 8px 14px; border-bottom: 1px solid var(--border-secondary); flex-wrap: wrap; flex-shrink: 0; }
.legend-item { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary); }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.kg-svg-wrap { flex: 1; min-height: 0; overflow: hidden; }
.kg-svg-wrap svg { display: block; width: 100%; height: 100%; }

/* 可拖拽分隔线 */
.kg-detail-divider { width: 5px; cursor: col-resize; background: var(--border-secondary); flex-shrink: 0; }
.kg-detail-divider:hover { background: var(--border-primary); }

/* 右侧详情面板 */
.kg-detail-panel {
  width: 300px; min-width: 240px; border-left: 1px solid var(--border-secondary);
  background: var(--bg-secondary); display: flex; flex-direction: column; overflow-y: auto; flex-shrink: 0;
}
.detail-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; border-bottom: 1px solid var(--border-secondary); }
.detail-header h3 { font-family: var(--font-mono); font-size: 13px; font-weight: 600; }
.detail-close { width: 24px; height: 24px; border: 1px solid var(--border-primary); border-radius: var(--radius-sm); background: var(--bg-primary); font-size: 12px; color: var(--text-secondary); display: flex; align-items: center; justify-content: center; cursor: pointer; }
.detail-close:hover { background: var(--bg-tertiary); }
.detail-type-tag { margin: 12px 14px 6px; padding: 3px 10px; border-radius: 3px; font-size: 12px; font-weight: 600; color: #fff; display: inline-block; align-self: flex-start; }
.detail-name { padding: 0 14px; font-size: 14px; font-weight: 600; line-height: 1.4; margin-bottom: 12px; }
.props-title { font-size: 12px; font-weight: 600; color: var(--text-tertiary); padding: 10px 14px 6px; border-top: 1px solid var(--border-secondary); text-transform: uppercase; letter-spacing: 0.04em; }
.detail-properties { padding: 0 14px 8px; display: flex; flex-direction: column; gap: 4px; }
.detail-prop { display: flex; gap: 8px; font-size: 13px; }
.dp-key { color: var(--text-tertiary); min-width: 55px; flex-shrink: 0; font-family: var(--font-mono); font-size: 12px; }
.dp-val { color: var(--text-primary); word-break: break-all; font-size: 13px; }
.detail-relations { padding: 0 14px 14px; display: flex; flex-direction: column; gap: 6px; }
.detail-rel { display: flex; align-items: center; gap: 6px; font-size: 13px; padding: 4px 0; }
.rel-source, .rel-target { color: var(--text-primary); font-weight: 500; cursor: pointer; text-decoration: underline; text-decoration-color: var(--border-primary); text-underline-offset: 3px; }
.rel-source:hover, .rel-target:hover { color: var(--accent); }
.rel-type { color: var(--text-tertiary); font-size: 12px; flex-shrink: 0; }
.rel-empty { color: var(--text-tertiary); font-size: 12px; font-style: italic; }
</style>
