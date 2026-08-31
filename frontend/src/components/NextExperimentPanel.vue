<template>
  <div class="next-exp-panel">
    <div class="nep-header">
      <h3>🚀 Next Experiment</h3>
      <p class="nep-desc">基于历史实验，AI 为您推荐最值得尝试的下一轮实验配置</p>
    </div>

    <!-- 操作按钮 -->
    <button class="btn-analyze" @click="loadRecommendations" :disabled="loading">
      {{ loading ? '分析中…' : '🤖 AI 分析并推荐' }}
    </button>

    <!-- 加载中 -->
    <div v-if="loading" class="nep-loading">
      <div class="loading-spinner">⏳</div>
      <p>正在分析历史实验数据，请稍候…</p>
    </div>

    <!-- 分析结果 -->
    <div v-else-if="result">
      <!-- 分析摘要 -->
      <div class="analysis-summary">
        <div class="as-label">📊 分析摘要</div>
        <div class="as-text">{{ result.analysis_summary }}</div>
      </div>

      <!-- 候选实验列表 -->
      <div class="candidates-title">候选实验方案</div>
      <div v-for="c in result.candidates" :key="c.id" class="candidate-card">
        <div class="cc-header">
          <div class="cc-title">{{ c.title }}</div>
          <span class="cc-confidence" :class="'conf-' + c.confidence">
            {{ confidenceLabel(c.confidence) }}
          </span>
        </div>
        <div class="cc-rationale">
          <span class="cc-label">推荐理由</span>
          {{ c.rationale }}
        </div>
        <div v-if="c.suggested_params && Object.keys(c.suggested_params).length > 0" class="cc-params">
          <span class="cc-label">建议参数</span>
          <div class="param-grid">
            <div v-for="(v, k) in c.suggested_params" :key="k" class="param-chip">
              <span class="pk">{{ k }}</span>
              <span class="pv">{{ v }}</span>
            </div>
          </div>
        </div>
        <div class="cc-outcome">
          <span class="cc-label">预期效果</span>
          {{ c.expected_outcome }}
        </div>
        <div class="cc-actions">
          <button
            class="btn-confirm"
            :disabled="creating"
            @click="confirmExperiment(c)"
          >
            ✅ 创建此实验
          </button>
        </div>
      </div>

      <!-- 无候选 -->
      <div v-if="result.candidates?.length === 0" class="empty-hint">
        没有生成候选实验，请确保项目下有足够的历史实验记录
      </div>
    </div>

    <!-- 创建成功提示 -->
    <div v-if="createdRecord" class="created-toast">
      🎉 实验已创建：<strong>{{ createdRecord.task }}</strong>
      <span class="created-id">{{ createdRecord.id }}</span>
    </div>
  </div>
</template>

<script>
export default {
  name: 'NextExperimentPanel',
  props: {
    projectId: { type: String, required: true },
  },
  emits: ['experiment-created'],
  data() {
    return {
      loading: false,
      result: null,
      creating: false,
      createdRecord: null,
    }
  },
  methods: {
    async loadRecommendations() {
      this.loading = true
      this.result = null
      this.createdRecord = null
      try {
        const r = await fetch(`/api/projects/${this.projectId}/next-experiment`)
        const data = await r.json()
        this.result = data
      } catch (e) {
        alert('推荐失败：' + e.message)
      } finally {
        this.loading = false
      }
    },
    async confirmExperiment(candidate) {
      if (!confirm(`确认创建实验「${candidate.title}」？`)) return
      this.creating = true
      try {
        const r = await fetch(`/api/projects/${this.projectId}/next-experiment/confirm`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ candidate }),
        })
        const data = await r.json()
        this.createdRecord = data.record
        this.$emit('experiment-created', data.record)
      } catch (e) {
        alert('创建失败：' + e.message)
      } finally {
        this.creating = false
      }
    },
    confidenceLabel(c) {
      return { high: '高置信度', medium: '中置信度', low: '低置信度' }[c] || c
    },
  },
}
</script>

<style scoped>
.next-exp-panel {}
.nep-header { margin-bottom: 16px; }
.nep-header h3 { margin: 0 0 6px; font-size: 18px; }
.nep-desc { font-size: 13px; color: #6b7280; margin: 0; }
.btn-analyze {
  background: #6366f1; color: #fff; border: none;
  padding: 10px 20px; border-radius: 8px; cursor: pointer; font-size: 14px;
  margin-bottom: 20px;
}
.btn-analyze:disabled { opacity: .5; cursor: not-allowed; }
.nep-loading { text-align: center; padding: 40px 0; }
.loading-spinner { font-size: 32px; animation: spin 2s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }
.analysis-summary {
  background: #fffbeb; border: 1px solid #fde68a;
  border-radius: 10px; padding: 14px; margin-bottom: 20px;
}
.as-label { font-size: 12px; font-weight: 600; color: #92400e; margin-bottom: 8px; }
.as-text { font-size: 14px; color: #78350f; line-height: 1.6; }
.candidates-title { font-size: 15px; font-weight: 600; margin-bottom: 12px; }
.candidate-card {
  background: var(--surface, #fff);
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 12px; padding: 16px; margin-bottom: 14px;
}
.cc-header { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.cc-title { font-size: 15px; font-weight: 600; flex: 1; }
.cc-confidence { font-size: 11px; padding: 2px 8px; border-radius: 999px; font-weight: 600; flex-shrink: 0; }
.conf-high { background: #dcfce7; color: #15803d; }
.conf-medium { background: #fef3c7; color: #92400e; }
.conf-low { background: #f3f4f6; color: #6b7280; }
.cc-label { font-size: 11px; color: #9ca3af; display: block; margin-bottom: 4px; }
.cc-rationale, .cc-params, .cc-outcome { margin-bottom: 10px; font-size: 13px; color: #374151; }
.param-grid { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 4px; }
.param-chip { background: #ede9fe; border-radius: 6px; padding: 3px 10px; font-size: 12px; }
.pk { color: #7c3aed; font-weight: 600; margin-right: 4px; }
.pv { color: #4c1d95; }
.cc-actions { margin-top: 12px; }
.btn-confirm {
  background: #059669; color: #fff; border: none;
  padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px;
}
.btn-confirm:disabled { opacity: .5; cursor: not-allowed; }
.empty-hint { color: #aaa; text-align: center; padding: 40px 0; font-size: 14px; }
.created-toast {
  background: #dcfce7; border: 1px solid #86efac;
  border-radius: 10px; padding: 14px 16px; margin-top: 16px;
  font-size: 14px; color: #065f46;
}
.created-id { margin-left: 8px; font-size: 12px; font-family: monospace; color: #047857; }
</style>
