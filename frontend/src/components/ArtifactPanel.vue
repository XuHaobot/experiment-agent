<template>
  <div class="art-panel">
    <div class="art-header">
      <h3 class="art-title">{{ lang === 'en-US' ? 'Research Artifacts' : '科研产物与资产管理（Artifacts）' }}</h3>
      <div class="art-filters">
        <button
          v-for="t in ['all','chart','report','code','analysis','model','protocol']" :key="t"
          class="filter-btn"
          :class="{ active: typeFilter === t }"
          @click="typeFilter = t; load()"
        >{{ filterLabels[t] }}</button>
      </div>
    </div>

    <div v-if="loading" class="art-loading">{{ lang === 'en-US' ? 'Loading artifacts...' : '加载中...' }}</div>
    <div v-else-if="artifacts.length === 0" class="art-empty">{{ lang === 'en-US' ? 'No artifacts registered yet.' : '暂无 Artifact 产物，可在数据分析面板执行分析后保存生成。' }}</div>
    <div v-else class="art-list">
      <div v-for="a in artifacts" :key="a.id" class="art-card">
        <div class="art-card-top">
          <span class="art-icon">{{ typeIcon(a.type) }}</span>
          <div class="art-meta">
            <div class="art-name">{{ a.name }} <span class="art-ver font-mono">v{{ a.version }}</span></div>
            <div class="art-sub font-mono">{{ a.type }} · {{ formatDate(a.created_at) }}</div>
          </div>
          <div class="art-actions">
            <button class="btn-lineage" @click="showLineage(a)" :title="lang === 'en-US' ? 'Lineage Provenance' : '血缘追溯'">🔍 {{ lang === 'en-US' ? 'Lineage' : '血缘' }}</button>
            <button class="btn-delete" @click="deleteArt(a.id)" :title="lang === 'en-US' ? 'Delete' : '删除'">🗑</button>
          </div>
        </div>
        <div v-if="a.source_record_id" class="art-source">{{ lang === 'en-US' ? 'Source Experiment:' : '来源实验：' }} {{ a.source_record_id }}</div>
      </div>
    </div>

    <!-- 血缘追溯面板 -->
    <div v-if="lineage" class="lineage-panel">
      <div class="lineage-header">
        <strong>{{ lang === 'en-US' ? 'Lineage Provenance: ' : '血缘追溯：' }}{{ lineage.artifact?.name }}</strong>
        <button class="btn-close" @click="lineage = null">✕</button>
      </div>
      <div class="lineage-chain">
        <div class="lineage-node art-node">📦 Artifact<br/><small class="font-mono">{{ lineage.artifact?.id }}</small></div>
        <div class="lineage-arrow">↓</div>
        <div v-if="lineage.source_record" class="lineage-node exp-node">
          🧪 实验：{{ lineage.source_record.task || lineage.source_record.id }}
          <br/><small class="font-mono">{{ lineage.source_record.created_at?.slice(0,10) }}</small>
        </div>
        <template v-if="lineage.params">
          <div class="lineage-arrow">↓</div>
          <div class="lineage-node param-node">⚙️ 参数<br/><small class="font-mono">{{ JSON.stringify(lineage.params).slice(0,80) }}</small></div>
        </template>
        <template v-if="lineage.model || lineage.dataset">
          <div class="lineage-arrow">↓</div>
          <div class="lineage-node data-node">🗄️ {{ lineage.model ? 'Model: ' + lineage.model : '' }} {{ lineage.dataset ? 'Dataset: ' + lineage.dataset : '' }}</div>
        </template>
        <div v-if="!lineage.source_record" class="lineage-node empty-node">无来源信息</div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ArtifactPanel',
  props: {
    projectId: { type: String, required: true },
    lang: { type: String, default: 'zh-CN' },
  },
  data() {
    return {
      artifacts: [],
      loading: false,
      typeFilter: 'all',
      lineage: null,
    }
  },
  computed: {
    filterLabels() {
      if (this.lang === 'en-US') {
        return { all: 'All', chart: 'Charts', report: 'Reports', code: 'Code', analysis: 'Analysis', model: 'Models', protocol: 'Protocols' }
      }
      return { all: '全部', chart: '图表', report: '报告', code: '代码', analysis: '分析', model: '模型', protocol: '协议' }
    },
  },
  mounted() {
    this.load()
  },
  methods: {
    async load() {
      this.loading = true
      try {
        const type = this.typeFilter !== 'all' ? `?type=${this.typeFilter}` : ''
        const r = await fetch(`/api/projects/${this.projectId}/artifacts${type}`)
        const data = await r.json()
        this.artifacts = data.artifacts || []
      } catch (e) {
        console.error(e)
      } finally {
        this.loading = false
      }
    },
    async showLineage(artifact) {
      try {
        const r = await fetch(`/api/artifacts/${artifact.id}/lineage`)
        this.lineage = await r.json()
      } catch (e) {
        alert('获取血缘失败：' + e.message)
      }
    },
    async deleteArt(id) {
      if (!confirm(this.lang === 'en-US' ? 'Delete this artifact?' : '确定删除该 Artifact？')) return
      try {
        await fetch(`/api/artifacts/${id}`, { method: 'DELETE' })
        await this.load()
      } catch (e) {
        alert('删除失败：' + e.message)
      }
    },
    typeIcon(type) {
      return { chart: '📊', report: '📄', code: '💻', analysis: '🔬', model: '🤖', dataset: '🗄️', protocol: '📋', other: '📦' }[type] || '📦'
    },
    formatDate(iso) {
      if (!iso) return ''
      return new Date(iso).toLocaleDateString(this.lang === 'en-US' ? 'en-US' : 'zh-CN')
    },
  },
}
</script>

<style scoped>
.art-panel { padding: 0; color: var(--text-primary); }
.art-header { margin-bottom: 20px; }
.art-title { font-size: 18px; margin: 0 0 10px; color: var(--text-primary); font-weight: 600; }
.art-filters { display: flex; gap: 6px; flex-wrap: wrap; }
.filter-btn { font-size: 12px; padding: 4px 12px; border: 1px solid var(--border-default); border-radius: 999px; background: var(--bg-surface-2); color: var(--text-secondary); cursor: pointer; transition: all .15s; }
.filter-btn:hover { background: var(--bg-hover); color: var(--text-primary); }
.filter-btn.active { background: var(--accent-science); color: #fff; border-color: var(--accent-science); font-weight: 600; }
.art-loading, .art-empty { text-align: center; padding: 40px; color: var(--text-muted); font-size: 13px; }
.art-list { display: flex; flex-direction: column; gap: 10px; }
.art-card { border: 1px solid var(--border-default); border-radius: 8px; padding: 12px 16px; background: var(--bg-surface-1); }
.art-card-top { display: flex; align-items: flex-start; gap: 12px; }
.art-icon { font-size: 24px; flex-shrink: 0; }
.art-meta { flex: 1; min-width: 0; }
.art-name { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.art-ver { font-size: 10px; background: var(--accent-science-dim); color: var(--accent-science); border-radius: 4px; padding: 1px 5px; margin-left: 4px; }
.art-sub { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.art-source { font-size: 12px; color: var(--text-secondary); margin-top: 6px; padding-left: 36px; }
.art-actions { display: flex; gap: 6px; flex-shrink: 0; }
.btn-lineage, .btn-delete { font-size: 12px; padding: 4px 10px; border: 1px solid var(--border-default); border-radius: 6px; background: var(--bg-surface-2); color: var(--text-primary); cursor: pointer; }
.btn-lineage:hover { background: var(--bg-hover); }
.btn-delete:hover { background: var(--accent-danger-dim); color: var(--accent-danger); border-color: var(--accent-danger); }
.lineage-panel { margin-top: 20px; border: 1px solid var(--border-active); border-radius: 8px; padding: 16px; background: var(--bg-surface-2); }
.lineage-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; font-size: 13px; color: var(--text-primary); }
.btn-close { background: none; border: none; font-size: 14px; cursor: pointer; color: var(--text-muted); }
.lineage-chain { display: flex; flex-direction: column; align-items: flex-start; gap: 4px; }
.lineage-node { padding: 8px 14px; border-radius: 6px; font-size: 12px; min-width: 220px; border: 1px solid var(--border-default); background: var(--bg-surface-1); color: var(--text-primary); }
.art-node { border-left: 4px solid var(--accent-science); }
.exp-node { border-left: 4px solid var(--accent-success); }
.param-node { border-left: 4px solid var(--accent-warning); }
.data-node { border-left: 4px solid var(--text-muted); }
.empty-node { color: var(--text-muted); font-style: italic; }
.lineage-arrow { font-size: 14px; color: var(--text-muted); padding-left: 14px; line-height: 1; }
</style>
