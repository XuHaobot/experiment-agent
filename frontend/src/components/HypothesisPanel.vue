<template>
  <div class="hypothesis-panel">
    <div class="hp-header">
      <h3 class="hp-title">{{ lang === 'en-US' ? 'Scientific Hypotheses' : '科学假说管理（Hypotheses）' }}</h3>
      <button class="btn-primary" @click="showCreate = true">+ {{ lang === 'en-US' ? 'New Hypothesis' : '新建假说' }}</button>
    </div>

    <!-- 新建假设弹窗 -->
    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
      <div class="modal-box">
        <h3>{{ lang === 'en-US' ? 'Create Hypothesis' : '新建科学假说' }}</h3>
        <input v-model="newTitle" :placeholder="lang === 'en-US' ? 'Hypothesis statement (one sentence)' : '假设标题（一句话科学陈述）'" class="modal-input" />
        <textarea v-model="newDesc" :placeholder="lang === 'en-US' ? 'Detailed rationale and theoretical backing (optional)' : '详细描述和理论依据（可选）'" class="modal-textarea" rows="3"></textarea>
        <div class="modal-actions">
          <button class="btn-primary" :disabled="!newTitle.trim()" @click="createHypothesis">{{ lang === 'en-US' ? 'Create' : '创建' }}</button>
          <button class="btn-secondary" @click="showCreate = false">{{ lang === 'en-US' ? 'Cancel' : '取消' }}</button>
        </div>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="empty-hint">{{ lang === 'en-US' ? 'Loading hypotheses...' : '加载中…' }}</div>

    <!-- 空状态 -->
    <div v-else-if="hypotheses.length === 0" class="empty-hint">
      {{ lang === 'en-US' ? 'No hypotheses yet. Click "+ New Hypothesis" to begin.' : '暂无假说，点击「新建假说」开始。' }}
    </div>

    <!-- 假设卡片列表 -->
    <div v-else class="hyp-list">
      <div v-for="h in hypotheses" :key="h.id" class="hyp-card">
        <div class="hc-top">
          <span class="hc-status" :class="'status-' + h.status">{{ statusLabel(h.status) }}</span>
          <button class="hc-delete" @click="deleteHypothesis(h.id)">✕</button>
        </div>
        <div class="hc-title">{{ h.title }}</div>
        <div class="hc-desc" v-if="h.description">{{ h.description }}</div>

        <!-- 状态操作 -->
        <div class="hc-actions">
          <button
            v-for="s in ['pending','testing','supported','refuted']"
            :key="s"
            class="btn-status"
            :class="{ active: h.status === s }"
            @click="updateStatus(h.id, s)"
          >{{ statusLabel(s) }}</button>
        </div>

        <!-- 证据列表 -->
        <div class="hc-evidence" v-if="h.evidence && h.evidence.length">
          <div class="ev-title">{{ lang === 'en-US' ? 'Evidence Ledger' : '证据支撑' }}</div>
          <div v-for="ev in h.evidence" :key="ev.id" class="ev-item" :class="ev.supports ? 'ev-support' : 'ev-refute'">
            <span class="ev-icon">{{ ev.supports ? '✅' : '❌' }}</span>
            <span>{{ ev.text }}</span>
            <span class="ev-source font-mono" v-if="ev.source">— {{ ev.source }}</span>
          </div>
        </div>

        <!-- 添加证据表单 -->
        <div class="add-evidence-section">
          <button
            class="btn-add-ev"
            @click="activeEvidenceForm = activeEvidenceForm === h.id ? null : h.id"
          >
            {{ activeEvidenceForm === h.id ? (lang === 'en-US' ? 'Close' : '收起') : (lang === 'en-US' ? '+ Add Evidence' : '+ 添加证据') }}
          </button>

          <div v-if="activeEvidenceForm === h.id" class="ev-form">
            <input v-model="evidenceText" :placeholder="lang === 'en-US' ? 'Evidence statement (e.g. Accuracy +5% under noise)' : '证据描述（例如：添加动态边后在噪声环境下准确率提升 5%）'" class="modal-input" />
            <input v-model="evidenceSource" :placeholder="lang === 'en-US' ? 'Source (e.g. Run #03, Paper #08)' : '来源（如 Run #03、Paper #08）'" class="modal-input font-mono" />
            <div class="ev-form-row">
              <label class="ev-label">
                <input type="checkbox" v-model="evidenceSupports" />
                {{ evidenceSupports ? (lang === 'en-US' ? 'Supports Hypothesis' : '支持该假设') : (lang === 'en-US' ? 'Refutes Hypothesis' : '反驳该假设') }}
              </label>
              <button class="btn-primary btn-sm" :disabled="!evidenceText.trim()" @click="addEvidence(h.id)">
                {{ lang === 'en-US' ? 'Save Evidence' : '保存证据' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { projectApi } from '../api/project.js'

export default {
  name: 'HypothesisPanel',
  props: {
    projectId: { type: String, required: true },
    lang: { type: String, default: 'zh-CN' },
  },
  data() {
    return {
      hypotheses: [],
      loading: false,
      showCreate: false,
      newTitle: '',
      newDesc: '',
      activeEvidenceForm: null,
      evidenceText: '',
      evidenceSource: '',
      evidenceSupports: true,
    }
  },
  mounted() {
    this.load()
  },
  methods: {
    statusLabel(status) {
      if (this.lang === 'en-US') {
        return { pending: 'PENDING', testing: 'TESTING', supported: 'SUPPORTED', refuted: 'REFUTED' }[status] || status
      }
      return { pending: '待验证', testing: '验证中', supported: '已证实', refuted: '已推翻' }[status] || status
    },
    async load() {
      this.loading = true
      try {
        const data = await projectApi.getHypotheses(this.projectId)
        this.hypotheses = data.hypotheses || []
        this.$emit('count-updated', this.hypotheses.length)
      } catch (e) {
        console.error(e)
      } finally {
        this.loading = false
      }
    },
    async createHypothesis() {
      if (!this.newTitle.trim()) return
      try {
        await projectApi.createHypothesis(this.projectId, {
          title: this.newTitle.trim(),
          description: this.newDesc.trim(),
        })
        this.newTitle = ''
        this.newDesc = ''
        this.showCreate = false
        await this.load()
        this.$emit('refresh')
      } catch (e) {
        alert('创建失败：' + e.message)
      }
    },
    async updateStatus(hypothesisId, status) {
      try {
        await projectApi.updateHypothesisStatus(hypothesisId, status)
        await this.load()
      } catch (e) {
        alert('更新失败：' + e.message)
      }
    },
    async addEvidence(hypothesisId) {
      if (!this.evidenceText.trim()) return
      try {
        await projectApi.addEvidence(hypothesisId, {
          text: this.evidenceText.trim(),
          source: this.evidenceSource.trim(),
          supports: this.evidenceSupports,
        })
        this.evidenceText = ''
        this.evidenceSource = ''
        this.evidenceSupports = true
        this.activeEvidenceForm = null
        await this.load()
      } catch (e) {
        alert('添加失败：' + e.message)
      }
    },
    async deleteHypothesis(hypothesisId) {
      if (!confirm('确定删除该假设？')) return
      try {
        await projectApi.deleteHypothesis(hypothesisId)
        await this.load()
        this.$emit('refresh')
      } catch (e) {
        alert('删除失败：' + e.message)
      }
    },
  },
}
</script>

<style scoped>
.hypothesis-panel { padding: 0; color: var(--text-primary); }
.hp-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.hp-title { font-size: 18px; margin: 0; font-weight: 600; color: var(--text-primary); }
.btn-primary { background: var(--accent-science); color: #fff; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; }
.btn-secondary { background: var(--bg-surface-2); border: 1px solid var(--border-default); color: var(--text-primary); padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 12px; }
.btn-sm { padding: 4px 10px; font-size: 12px; }
.empty-hint { color: var(--text-muted); font-size: 13px; text-align: center; padding: 40px 0; }
.hyp-list { display: flex; flex-direction: column; gap: 14px; }
.hyp-card { background: var(--bg-surface-1); border: 1px solid var(--border-default); border-radius: 8px; padding: 16px 18px; }
.hc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.hc-status { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px; font-family: var(--font-mono); text-transform: uppercase; }
.status-pending { background: var(--accent-warning-dim); color: var(--accent-warning); border: 1px solid var(--accent-warning); }
.status-testing { background: var(--accent-science-dim); color: var(--accent-science); border: 1px solid var(--accent-science); }
.status-supported { background: var(--accent-success-dim); color: var(--accent-success); border: 1px solid var(--accent-success); }
.status-refuted { background: var(--accent-danger-dim); color: var(--accent-danger); border: 1px solid var(--accent-danger); }
.hc-delete { background: none; border: none; cursor: pointer; color: var(--text-muted); font-size: 13px; }
.hc-delete:hover { color: var(--accent-danger); }
.hc-title { font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px; line-height: 1.5; }
.hc-desc { font-size: 12px; color: var(--text-secondary); margin-bottom: 12px; line-height: 1.5; }
.hc-actions { display: flex; gap: 6px; margin-bottom: 12px; }
.btn-status { font-size: 11px; padding: 2px 8px; border: 1px solid var(--border-default); border-radius: 4px; background: var(--bg-surface-2); color: var(--text-muted); cursor: pointer; }
.btn-status.active { background: var(--accent-science); color: #fff; border-color: var(--accent-science); font-weight: 600; }
.hc-evidence { margin-bottom: 12px; background: var(--bg-surface-2); border-radius: 6px; padding: 10px 12px; }
.ev-title { font-size: 11px; font-weight: 600; color: var(--text-muted); margin-bottom: 6px; text-transform: uppercase; }
.ev-item { display: flex; align-items: flex-start; gap: 6px; font-size: 12px; padding: 4px 0; }
.ev-support { color: var(--text-primary); }
.ev-refute { color: var(--accent-danger); }
.ev-source { color: var(--text-muted); font-size: 11px; }
.btn-add-ev { background: none; border: none; color: var(--accent-science); font-size: 12px; cursor: pointer; padding: 0; }
.ev-form { margin-top: 8px; display: flex; flex-direction: column; gap: 6px; background: var(--bg-surface-2); padding: 10px; border-radius: 6px; border: 1px solid var(--border-default); }
.ev-form-row { display: flex; align-items: center; justify-content: space-between; }
.ev-label { font-size: 12px; color: var(--text-secondary); display: flex; align-items: center; gap: 6px; cursor: pointer; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 200; backdrop-filter: blur(2px); }
.modal-box { background: var(--bg-surface-1); border: 1px solid var(--border-active); border-radius: 8px; padding: 24px; width: 440px; }
.modal-box h3 { margin: 0 0 16px; font-size: 16px; color: var(--text-primary); }
.modal-input, .modal-textarea { width: 100%; box-sizing: border-box; padding: 8px 12px; border: 1px solid var(--border-default); border-radius: 6px; font-size: 12px; margin-bottom: 12px; background: var(--bg-surface-2); color: var(--text-primary); outline: none; }
.modal-textarea { resize: vertical; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; }
</style>
