<template>
  <div class="conc-panel">
    <div class="conc-header">
      <div>
        <h3 class="conc-title">{{ lang === 'en-US' ? 'Scientific Conclusions & Evidence Balance' : '科研结论与认知记忆天平 (Evidence Balance)' }}</h3>
        <p class="conc-subtitle">
          {{ lang === 'en-US' ? 'Ground findings with supporting vs contradicting empirical evidence. Prevent AI epistemic lock-in.' : '基于双向正反证据严密支撑结论，显式呈现竞争性假说与未探索盲区，防止 AI 认知固化。' }}
        </p>
      </div>
      <button class="btn-create" @click="showCreate = true">+ {{ lang === 'en-US' ? 'New Conclusion' : '沉淀结论' }}</button>
    </div>

    <!-- 认知防固化概览天平卡片 (Evidence Balance & Anti-Lock-in Banner) -->
    <div v-if="balanceData" class="balance-card">
      <div class="balance-header">
        <span class="balance-title">⚖️ 认识论认知天平 (Epistemic Balance)</span>
        <span class="conf-badge" :class="'conf-' + (balanceData.confidence || 'medium')">
          置信充分度: {{ (balanceData.confidence || 'medium').toUpperCase() }}
        </span>
      </div>
      
      <div class="balance-grid">
        <div class="balance-box support">
          <span class="box-num">{{ balanceData.supporting ? balanceData.supporting.length : 0 }}</span>
          <span class="box-label">✓ 支持性证据 (Supporting)</span>
        </div>
        <div class="balance-box contradict">
          <span class="box-num">{{ balanceData.contradicting ? balanceData.contradicting.length : 0 }}</span>
          <span class="box-label">! 反面/异常证据 (Contradicting)</span>
        </div>
        <div class="balance-box unknown">
          <span class="box-num">{{ balanceData.unknown ? balanceData.unknown.length : 0 }}</span>
          <span class="box-label">? 未探索盲区 (Unexplored)</span>
        </div>
      </div>

      <!-- 竞争性假说 (Alternative Hypotheses) -->
      <div v-if="alternatives && alternatives.length" class="alternatives-section">
        <div class="section-title">🔀 竞争性机制假说 (Alternative Hypotheses / AI Suggestions)</div>
        <div class="alt-list">
          <div v-for="(alt, idx) in alternatives" :key="idx" class="alt-item">
            <span class="ai-badge">AI SUGGESTION</span>
            <span class="alt-title">{{ alt.hypothesis }}</span>
            <p class="alt-desc">{{ alt.explanation }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 新建表单 -->
    <div v-if="showCreate" class="create-form">
      <textarea v-model="newText" :placeholder="lang === 'en-US' ? 'Conclusion statement (supported by evidence)...' : '结论陈述内容（有实验/文献数据支撑）...'" class="form-textarea" rows="3"></textarea>
      <div class="form-row">
        <select v-model="newConfidence" class="form-select">
          <option value="high">{{ lang === 'en-US' ? 'High Confidence' : '高置信度 (High)' }}</option>
          <option value="medium">{{ lang === 'en-US' ? 'Medium Confidence' : '中置信度 (Medium)' }}</option>
          <option value="low">{{ lang === 'en-US' ? 'Low Confidence' : '低置信度 (Low)' }}</option>
        </select>
        <input v-model="newHypothesisId" :placeholder="lang === 'en-US' ? 'Target Hypothesis ID (optional, e.g. H2)' : '关联假设 ID（可选，例如 H2）'" class="form-input" />
      </div>
      <div class="form-actions">
        <button class="btn-save" @click="createConclusion" :disabled="!newText.trim()">{{ lang === 'en-US' ? 'Save' : '保存结论' }}</button>
        <button class="btn-cancel" @click="showCreate = false">{{ lang === 'en-US' ? 'Cancel' : '取消' }}</button>
      </div>
    </div>

    <div v-if="loading" class="conc-loading">{{ lang === 'en-US' ? 'Loading conclusions...' : '加载中...' }}</div>
    <div v-else-if="conclusions.length === 0 && !showCreate" class="conc-empty">{{ lang === 'en-US' ? 'No conclusions yet.' : '暂无沉淀结论，可结合实验证据进行提炼与保存。' }}</div>

    <div class="conc-list">
      <div v-for="c in conclusions" :key="c.id" class="conc-card">
        <div class="conc-top">
          <span class="conf-badge" :class="'conf-' + c.confidence">{{ confLabel(c.confidence) }}</span>
          <span class="conc-source" v-if="c.source === 'agent'">🤖 {{ lang === 'en-US' ? 'AI Proposed' : 'AI 生成' }}</span>
          <button class="btn-del-conc" @click="deleteConclusion(c.id)">✕</button>
        </div>
        <div class="conc-text">{{ c.text }}</div>
        <div v-if="c.hypothesis_id" class="conc-hyp font-mono">{{ lang === 'en-US' ? 'Target Hypothesis:' : '关联假设：' }} {{ c.hypothesis_id }}</div>
        <!-- 证据引用 -->
        <div v-if="c.evidence_refs && c.evidence_refs.length" class="conc-evidence">
          <div class="ev-title">{{ lang === 'en-US' ? 'Supporting Evidence' : '证据来源' }}</div>
          <div v-for="ev in c.evidence_refs" :key="ev.id" class="ev-ref">
            <span class="ev-type-badge">{{ ev.type }}</span>
            <span class="ev-id font-mono">{{ ev.id }}</span>
            <span v-if="ev.snippet" class="ev-snippet">{{ ev.snippet }}</span>
          </div>
        </div>
        <!-- 添加证据 -->
        <div class="add-evidence">
          <button class="btn-add-ev" @click="toggleEvForm(c.id)">+ {{ lang === 'en-US' ? 'Attach Evidence' : '关联支撑证据' }}</button>
          <div v-if="evForms[c.id]" class="ev-form">
            <select v-model="evForms[c.id].type" class="ev-select">
              <option value="experiment">实验 (Experiment)</option>
              <option value="paper">论文 (Paper)</option>
              <option value="dataset">数据集 (Dataset)</option>
              <option value="analysis">分析 (Analysis)</option>
              <option value="artifact">产物 (Artifact)</option>
            </select>
            <input v-model="evForms[c.id].id" placeholder="ID" class="ev-input font-mono" />
            <input v-model="evForms[c.id].snippet" placeholder="引文片段（可选）" class="ev-input" />
            <button class="btn-ev-save" @click="addEvidence(c.id)">{{ lang === 'en-US' ? 'Add' : '添加' }}</button>
          </div>
        </div>
        <div class="conc-date font-mono">{{ formatDate(c.created_at) }}</div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ConclusionPanel',
  props: {
    projectId: { type: String, required: true },
    lang: { type: String, default: 'zh-CN' },
  },
  data() {
    return {
      conclusions: [],
      balanceData: null,
      alternatives: [],
      loading: false,
      showCreate: false,
      newText: '',
      newConfidence: 'medium',
      newHypothesisId: '',
      evForms: {},
    }
  },
  mounted() {
    this.load()
    this.loadBalance()
  },
  methods: {
    confLabel(conf) {
      if (this.lang === 'en-US') {
        return { high: 'HIGH CONFIDENCE', medium: 'MODERATE', low: 'LOW CONFIDENCE' }[conf] || 'MODERATE'
      }
      return { high: '高置信度', medium: '中置信度', low: '低置信度' }[conf] || '中置信度'
    },
    async loadBalance() {
      try {
        const r1 = await fetch(`/api/projects/${this.projectId}/memory/balance`)
        if (r1.ok) this.balanceData = await r1.json()

        const r2 = await fetch(`/api/projects/${this.projectId}/memory/alternatives`)
        if (r2.ok) {
          const d2 = await r2.json()
          this.alternatives = d2.alternative_hypotheses || []
        }
      } catch (e) {
        console.warn('Memory balance load error:', e)
      }
    },
    async load() {
      this.loading = true
      try {
        const r = await fetch(`/api/projects/${this.projectId}/conclusions`)
        const data = await r.json()
        this.conclusions = data.conclusions || []
      } catch (e) {
        console.error(e)
      } finally {
        this.loading = false
      }
    },
    async createConclusion() {
      if (!this.newText.trim()) return
      try {
        await fetch(`/api/projects/${this.projectId}/conclusions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: this.newText.trim(),
            confidence: this.newConfidence,
            hypothesis_id: this.newHypothesisId || null,
            evidence_refs: [],
            source: 'user',
          }),
        })
        this.newText = ''
        this.newHypothesisId = ''
        this.showCreate = false
        await this.load()
        await this.loadBalance()
      } catch (e) {
        alert('保存失败：' + e.message)
      }
    },
    async deleteConclusion(id) {
      if (!confirm('确定删除该结论？')) return
      try {
        await fetch(`/api/conclusions/${id}`, { method: 'DELETE' })
        await this.load()
        await this.loadBalance()
      } catch (e) {
        alert('删除失败：' + e.message)
      }
    },
    toggleEvForm(id) {
      if (this.evForms[id]) {
        const f = { ...this.evForms }
        delete f[id]
        this.evForms = f
      } else {
        this.evForms = { ...this.evForms, [id]: { type: 'experiment', id: '', snippet: '' } }
      }
    },
    async addEvidence(conclusionId) {
      const form = this.evForms[conclusionId]
      if (!form?.id?.trim()) return
      try {
        await fetch(`/api/conclusions/${conclusionId}/evidence`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ type: form.type, id: form.id.trim(), snippet: form.snippet?.trim() }),
        })
        const f = { ...this.evForms }
        delete f[conclusionId]
        this.evForms = f
        await this.load()
        await this.loadBalance()
      } catch (e) {
        alert('添加失败：' + e.message)
      }
    },
    formatDate(iso) {
      if (!iso) return ''
      return new Date(iso).toLocaleDateString(this.lang === 'en-US' ? 'en-US' : 'zh-CN')
    },
  },
}
</script>

<style scoped>
.conc-panel { padding: 0; color: var(--text-primary); }
.conc-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 16px; }
.conc-title { font-size: 18px; margin: 0 0 4px 0; color: var(--text-primary); font-weight: 600; }
.conc-subtitle { font-size: 12px; color: var(--text-muted); margin: 0; }
.btn-create { background: var(--accent-science); color: #fff; border: none; border-radius: 6px; padding: 6px 14px; cursor: pointer; font-size: 12px; font-weight: 600; }

.balance-card {
  background: var(--bg-surface-1);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 18px;
}
.balance-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.balance-title { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.balance-grid { display: flex; gap: 10px; margin-bottom: 12px; }
.balance-box {
  flex: 1; padding: 10px; border-radius: 6px; display: flex; flex-direction: column; align-items: center;
}
.balance-box.support { background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); }
.balance-box.contradict { background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); }
.balance-box.unknown { background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.2); }
.box-num { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.box-label { font-size: 11px; color: var(--text-secondary); margin-top: 2px; }

.alternatives-section { border-top: 1px dashed var(--border-default); padding-top: 10px; margin-top: 10px; }
.section-title { font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 8px; }
.alt-list { display: flex; flex-direction: column; gap: 6px; }
.alt-item { background: var(--bg-surface-2); padding: 8px 10px; border-radius: 6px; font-size: 12px; }
.ai-badge { background: #fef3c7; color: #b45309; padding: 1px 5px; border-radius: 4px; font-size: 10px; font-weight: 700; margin-right: 6px; }
.alt-title { font-weight: 600; color: var(--text-primary); }
.alt-desc { margin: 4px 0 0 0; color: var(--text-secondary); font-size: 11px; line-height: 1.4; }

.create-form { border: 1px solid var(--border-default); border-radius: 8px; padding: 16px; margin-bottom: 16px; background: var(--bg-surface-1); }
.form-textarea { width: 100%; border: 1px solid var(--border-default); border-radius: 6px; padding: 10px; font-size: 12px; resize: vertical; font-family: inherit; margin-bottom: 10px; background: var(--bg-surface-2); color: var(--text-primary); box-sizing: border-box; }
.form-row { display: flex; gap: 10px; margin-bottom: 10px; }
.form-select, .form-input { border: 1px solid var(--border-default); border-radius: 6px; padding: 6px 10px; font-size: 12px; flex: 1; background: var(--bg-surface-2); color: var(--text-primary); }
.form-actions { display: flex; gap: 8px; }
.btn-save { background: var(--accent-science); color: #fff; border: none; border-radius: 6px; padding: 6px 16px; cursor: pointer; font-size: 12px; font-weight: 600; }
.btn-save:disabled { opacity: .5; cursor: not-allowed; }
.btn-cancel { background: var(--bg-surface-2); border: 1px solid var(--border-default); color: var(--text-primary); border-radius: 6px; padding: 6px 16px; cursor: pointer; font-size: 12px; }
.conc-loading, .conc-empty { text-align: center; padding: 40px; color: var(--text-muted); font-size: 13px; }
.conc-list { display: flex; flex-direction: column; gap: 12px; }
.conc-card { border: 1px solid var(--border-default); border-radius: 8px; padding: 14px 16px; background: var(--bg-surface-1); }
.conc-top { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.conf-badge { font-size: 10px; padding: 2px 8px; border-radius: 4px; font-weight: 600; }
.conf-high { background: var(--accent-success-dim); color: var(--accent-success); border: 1px solid var(--accent-success); }
.conf-medium { background: var(--accent-warning-dim); color: var(--accent-warning); border: 1px solid var(--accent-warning); }
.conf-low { background: var(--accent-danger-dim); color: var(--accent-danger); border: 1px solid var(--accent-danger); }
.conc-source { font-size: 11px; color: var(--text-muted); }
.btn-del-conc { margin-left: auto; background: none; border: none; cursor: pointer; font-size: 13px; color: var(--text-muted); }
.btn-del-conc:hover { color: var(--accent-danger); }
.conc-text { font-size: 13px; line-height: 1.6; margin-bottom: 6px; color: var(--text-primary); }
.conc-hyp { font-size: 11px; color: var(--accent-science); margin-bottom: 8px; }
.conc-evidence { margin: 8px 0; background: var(--bg-surface-2); padding: 8px 12px; border-radius: 6px; }
.ev-title { font-size: 11px; font-weight: 600; color: var(--text-muted); margin-bottom: 4px; text-transform: uppercase; }
.ev-ref { display: flex; align-items: center; gap: 6px; font-size: 12px; margin-bottom: 3px; }
.ev-type-badge { background: var(--accent-science-dim); color: var(--accent-science); border-radius: 4px; padding: 1px 6px; font-size: 10px; font-weight: 600; }
.ev-id { color: var(--text-primary); font-size: 11px; }
.ev-snippet { color: var(--text-secondary); font-style: italic; }
.add-evidence { margin-top: 8px; }
.btn-add-ev { font-size: 11px; color: var(--accent-science); background: none; border: none; cursor: pointer; padding: 0; }
.ev-form { display: flex; gap: 6px; margin-top: 6px; flex-wrap: wrap; }
.ev-select { border: 1px solid var(--border-default); border-radius: 6px; padding: 4px 8px; font-size: 12px; background: var(--bg-surface-2); color: var(--text-primary); }
.ev-input { border: 1px solid var(--border-default); border-radius: 6px; padding: 4px 8px; font-size: 12px; flex: 1; min-width: 100px; background: var(--bg-surface-2); color: var(--text-primary); }
.btn-ev-save { background: var(--accent-science); color: #fff; border: none; border-radius: 6px; padding: 4px 10px; cursor: pointer; font-size: 12px; }
.conc-date { font-size: 11px; color: var(--text-muted); margin-top: 8px; }
</style>
