<template>
  <div class="explore-panel">
    <div class="explore-header">
      <div>
        <h2 class="explore-title">🧭 Active Exploration Engine (科学探索引擎)</h2>
        <p class="explore-subtitle">
          超越单一预测指标，以「最大化科研信息增益」与「消除认知不确定性」为驱动，生成多范式候选实验组合。
        </p>
      </div>
      <div class="header-actions">
        <button class="btn-secondary" @click="loadData" :disabled="loading">
          🔄 重新评估探索引擎
        </button>
      </div>
    </div>

    <!-- 1. Scientific Exploration Overview: What do we know vs What don't we know? -->
    <div class="overview-grid">
      <div class="overview-card known">
        <div class="card-icon">🧠</div>
        <div class="card-content">
          <h4>我们已知什么 (What We Know)</h4>
          <p v-if="balanceData && balanceData.supporting && balanceData.supporting.length">
            已有 {{ balanceData.supporting.length }} 项正向证据支撑当前主假说，置信充分度为 <b>{{ (balanceData.confidence || 'MEDIUM').toUpperCase() }}</b>。
          </p>
          <p v-else>处于初始基线确立阶段，等待首批实验执行数据。</p>
        </div>
      </div>

      <div class="overview-card unknown">
        <div class="card-icon">❓</div>
        <div class="card-content">
          <h4>未知与矛盾盲区 (What We Don't Know)</h4>
          <p v-if="balanceData && (balanceData.contradicting?.length || balanceData.unknown?.length)">
            发现 {{ balanceData.contradicting?.length || 0 }} 项反面/性能回落运行，存在 {{ balanceData.unknown?.length || 0 }} 个未探索参数盲区。
          </p>
          <p v-else>尚无明显反面矛盾记录。</p>
        </div>
      </div>

      <div class="overview-card strategy">
        <div class="card-icon">⚖️</div>
        <div class="card-content">
          <h4>动态探索-利用建议 (Explore / Exploit)</h4>
          <p v-if="candidatesData && candidatesData.recommended_balance">
            建议策略: <b>{{ candidatesData.recommended_balance.strategy }}</b>
            (探索 {{ Math.round(candidatesData.recommended_balance.explore_weight * 100) }}% / 优化 {{ Math.round(candidatesData.recommended_balance.exploit_weight * 100) }}%)
          </p>
          <p v-else>正在分析探索预算...</p>
        </div>
      </div>
    </div>

    <!-- Tab navigation for Candidates, Discrimination Matrix, and Pruning Advisor -->
    <div class="explore-tabs">
      <button class="tab-btn" :class="{ active: activeSubTab === 'candidates' }" @click="activeSubTab = 'candidates'">
        🎯 候选实验组合 (Candidates Portfolio)
      </button>
      <button class="tab-btn" :class="{ active: activeSubTab === 'discrimination' }" @click="activeSubTab = 'discrimination'">
        🔀 假说区分度矩阵 (Hypothesis Discrimination)
      </button>
      <button class="tab-btn" :class="{ active: activeSubTab === 'pruning' }" @click="activeSubTab = 'pruning'">
        ✂️ 假说认知修剪顾问 (Epistemic Pruning)
      </button>
    </div>

    <!-- Loading / Error states -->
    <div v-if="loading" class="explore-loading">⏳ 探索引擎正在推演全空间参数与假说证据...</div>

    <!-- VIEW 1: Candidate Experiments Portfolio -->
    <div v-else-if="activeSubTab === 'candidates'" class="candidates-list">
      <div v-if="!candidates || candidates.length === 0" class="empty-hint">暂无候选实验推荐。</div>
      <div v-for="cand in candidates" :key="cand.candidate_id" class="candidate-card" :class="cand.candidate_type.toLowerCase()">
        <div class="cand-top">
          <div class="type-tag" :class="cand.candidate_type.toLowerCase()">
            {{ cand.candidate_type }}
          </div>
          <span class="epistemic-badge">Epistemic Value: {{ cand.epistemic_value }}</span>
          <span class="info-gain-badge">Info Gain: {{ cand.expected_information_gain }}</span>
          <span v-if="cand.is_pseudo_exploration" class="pseudo-badge">⚠️ 伪探索警告 (已饱和区间)</span>
        </div>

        <h3 class="cand-title">{{ cand.title }}</h3>
        <p class="cand-uncertainty"><b>🎯 拟消除的不确定性:</b> {{ cand.uncertainty_reduction }}</p>

        <div class="cand-params">
          <span class="param-label">配置参数 (Variables):</span>
          <code>{{ JSON.stringify(cand.variables) }}</code>
        </div>

        <div class="cand-rationale">
          <div class="rationale-col">
            <span class="col-title">✅ 为什么选该实验 (Why this):</span>
            <p>{{ cand.why_this_experiment }}</p>
          </div>
          <div class="rationale-col">
            <span class="col-title">⚖️ 为什么不选其他实验 (Tradeoff):</span>
            <p>{{ cand.why_not_other_experiments }}</p>
          </div>
        </div>

        <div class="cand-footer">
          <div class="cost-tags">
            <span>⏱️ GPU 预计: {{ cand.estimated_cost?.gpu_hours || 1.0 }}h</span>
            <span>⚡ 风险等级: {{ cand.risk_level }}</span>
            <span>💡 新颖度: {{ cand.novelty }}</span>
          </div>
          <button class="btn-approve" @click="handleApprove(cand)" :disabled="approvingId === cand.candidate_id">
            {{ approvingId === cand.candidate_id ? '转化中...' : '✓ 批准并生成正式实验' }}
          </button>
        </div>
      </div>
    </div>

    <!-- VIEW 2: Hypothesis Discrimination Matrix -->
    <div v-else-if="activeSubTab === 'discrimination'" class="matrix-card">
      <h3>🔀 竞争性假说区分度矩阵 (Hypothesis Discrimination Matrix)</h3>
      <p class="matrix-tip">评估各候选实验在不同假说下的预测差异，优先选择能够一次性排除竞争解释的实验。</p>
      
      <div v-if="discriminationData && discriminationData.matrix" class="matrix-table-wrap">
        <table class="matrix-table">
          <thead>
            <tr>
              <th>候选实验 (Candidate)</th>
              <th>类型</th>
              <th v-for="h in discriminationData.hypotheses_evaluated" :key="h">{{ h }}</th>
              <th>区分鉴别力</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in discriminationData.matrix" :key="row.candidate_id">
              <td class="cand-cell"><b>{{ row.candidate_title }}</b></td>
              <td><span class="type-mini-tag">{{ row.candidate_type }}</span></td>
              <td v-for="h in discriminationData.hypotheses_evaluated" :key="h" class="pred-cell">
                {{ row.predictions[h] || '-' }}
              </td>
              <td><span class="disc-power-badge" :class="row.discrimination_power.toLowerCase()">{{ row.discrimination_power }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- VIEW 3: Epistemic Pruning Advisor -->
    <div v-else-if="activeSubTab === 'pruning'" class="pruning-card">
      <h3>✂️ 假说认知修剪顾问 (Epistemic Pruning Advisor)</h3>
      <p class="matrix-tip">基于反面实测证据与探索收益提出资源倾斜建议。<b>系统绝不自动删除任何假说</b>，由科研人员自主决策。</p>

      <div v-if="pruningData && pruningData.pruning_analysis" class="pruning-list">
        <div v-for="p in pruningData.pruning_analysis" :key="p.hypothesis_id" class="prune-item">
          <div class="prune-top">
            <span class="prune-hyp-title font-mono">{{ p.hypothesis_id }}: {{ p.title }}</span>
            <span class="status-tag" :class="p.recommended_status.toLowerCase()">推荐状态: {{ p.recommended_status }}</span>
          </div>
          <div class="prune-stats">
            <span>支持证据: {{ p.supporting_evidence_count }}</span>
            <span>反面证据: {{ p.contradicting_evidence_count }}</span>
          </div>
          <p class="prune-reason">{{ p.reason }}</p>
          <div class="prune-action"><b>💡 建议操作:</b> {{ p.pruning_recommendation }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  projectId: {
    type: String,
    required: true,
  },
})

const activeSubTab = ref('candidates')
const loading = ref(false)
const candidatesData = ref(null)
const candidates = ref([])
const balanceData = ref(null)
const discriminationData = ref(null)
const pruningData = ref(null)
const approvingId = ref(null)

async function loadData() {
  loading.value = true
  try {
    const [r1, r2, r3, r4] = await Promise.all([
      fetch(`/api/projects/${props.projectId}/exploration/candidates`),
      fetch(`/api/projects/${props.projectId}/memory/balance`),
      fetch(`/api/projects/${props.projectId}/exploration/discrimination`),
      fetch(`/api/projects/${props.projectId}/exploration/pruning`),
    ])

    if (r1.ok) {
      candidatesData.value = await r1.json()
      candidates.value = candidatesData.value.candidates || []
    }
    if (r2.ok) balanceData.value = await r2.json()
    if (r3.ok) discriminationData.value = await r3.json()
    if (r4.ok) pruningData.value = await r4.json()
  } catch (e) {
    console.error('Exploration engine load error:', e)
  } finally {
    loading.value = false
  }
}

async function handleApprove(candidate) {
  if (!confirm(`确认批准候选实验 [${candidate.title}] 并生成正式实验草稿？`)) return
  approvingId.value = candidate.candidate_id
  try {
    const res = await fetch(`/api/projects/${props.projectId}/exploration/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        candidate_id: candidate.candidate_id,
        candidate_data: candidate,
      }),
    })
    if (!res.ok) {
      const err = await res.json()
      alert(`批准失败: ${err.detail || '未知错误'}`)
      return
    }
    const data = await res.json()
    alert(`✓ 实验草稿已成功创建！ID: ${data.experiment_id}。你可以在「实验设计」面板中查看并开始执行。`)
    await loadData()
  } catch (e) {
    alert(`请求异常: ${e}`)
  } finally {
    approvingId.value = null
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.explore-panel {
  padding: 20px;
  max-width: 1100px;
  margin: 0 auto;
  color: var(--text-primary, #1e293b);
}
.explore-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}
.explore-title {
  font-size: 20px;
  font-weight: 700;
  margin: 0 0 4px 0;
}
.explore-subtitle {
  font-size: 13px;
  color: var(--text-secondary, #64748b);
  margin: 0;
}
.btn-secondary {
  padding: 8px 14px;
  background: var(--bg-surface-1, #fff);
  border: 1px solid var(--border-default, #cbd5e1);
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
}
.btn-secondary:hover { background: var(--bg-surface-2, #f1f5f9); }

.overview-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}
.overview-card {
  background: var(--bg-surface-1, #fff);
  border: 1px solid var(--border-default, #e2e8f0);
  border-radius: 8px;
  padding: 14px;
  display: flex;
  gap: 12px;
}
.overview-card.known { border-left: 4px solid #10b981; }
.overview-card.unknown { border-left: 4px solid #f59e0b; }
.overview-card.strategy { border-left: 4px solid #3b82f6; }
.card-icon { font-size: 24px; }
.card-content h4 { margin: 0 0 4px 0; font-size: 13px; font-weight: 600; }
.card-content p { margin: 0; font-size: 12px; color: var(--text-secondary, #64748b); line-height: 1.4; }

.explore-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border-default, #e2e8f0);
  padding-bottom: 8px;
}
.tab-btn {
  padding: 8px 14px;
  background: transparent;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary, #64748b);
  cursor: pointer;
}
.tab-btn.active {
  background: rgba(59, 130, 246, 0.1);
  color: #2563eb;
}

.candidates-list { display: flex; flex-direction: column; gap: 14px; }
.candidate-card {
  background: var(--bg-surface-1, #fff);
  border: 1px solid var(--border-default, #e2e8f0);
  border-radius: 10px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.candidate-card.exploit { border-left: 4px solid #10b981; }
.candidate-card.discriminate { border-left: 4px solid #8b5cf6; }
.candidate-card.explore { border-left: 4px solid #3b82f6; }
.candidate-card.replicate { border-left: 4px solid #64748b; }

.cand-top { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.type-tag { font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; }
.type-tag.exploit { background: #dcfce7; color: #166534; }
.type-tag.discriminate { background: #f3e8ff; color: #6b21a8; }
.type-tag.explore { background: #dbeafe; color: #1e40af; }
.type-tag.replicate { background: #f1f5f9; color: #475569; }

.epistemic-badge, .info-gain-badge {
  font-size: 10px; background: var(--bg-surface-2, #f1f5f9); padding: 2px 6px; border-radius: 4px;
}
.pseudo-badge { font-size: 10px; background: #fee2e2; color: #991b1b; padding: 2px 6px; border-radius: 4px; font-weight: 600; }

.cand-title { font-size: 15px; margin: 0 0 6px 0; font-weight: 600; }
.cand-uncertainty { font-size: 12px; color: var(--text-secondary, #475569); margin: 0 0 8px 0; }
.cand-params { font-size: 12px; margin-bottom: 10px; }
.cand-params code { background: var(--bg-surface-2, #f1f5f9); padding: 2px 6px; border-radius: 4px; font-family: monospace; }

.cand-rationale {
  display: grid; grid-template-columns: 1fr 1fr; gap: 10px; background: var(--bg-surface-2, #f8fafc);
  padding: 10px; border-radius: 6px; margin-bottom: 12px; font-size: 11px;
}
.col-title { font-weight: 600; color: var(--text-primary, #334155); }
.rationale-col p { margin: 2px 0 0 0; color: var(--text-secondary, #64748b); line-height: 1.4; }

.cand-footer { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-default, #e2e8f0); padding-top: 10px; }
.cost-tags { display: flex; gap: 10px; font-size: 11px; color: var(--text-muted, #94a3b8); }
.btn-approve {
  padding: 6px 14px; background: #10b981; color: #fff; border: none; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer;
}
.btn-approve:disabled { background: #9ca3af; cursor: not-allowed; }

/* Matrix table */
.matrix-card, .pruning-card {
  background: var(--bg-surface-1, #fff); border: 1px solid var(--border-default, #e2e8f0);
  border-radius: 10px; padding: 18px;
}
.matrix-card h3, .pruning-card h3 { margin: 0 0 4px 0; font-size: 15px; }
.matrix-tip { font-size: 12px; color: var(--text-secondary, #64748b); margin: 0 0 14px 0; }
.matrix-table-wrap { overflow-x: auto; }
.matrix-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.matrix-table th, .matrix-table td { border: 1px solid var(--border-default, #e2e8f0); padding: 8px 10px; text-align: left; }
.matrix-table th { background: var(--bg-surface-2, #f8fafc); font-weight: 600; }
.type-mini-tag { font-size: 10px; padding: 1px 4px; border-radius: 3px; background: #f1f5f9; }
.disc-power-badge { font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 600; }
.disc-power-badge.high { background: #dcfce7; color: #166534; }
.disc-power-badge.medium { background: #e0f2fe; color: #0369a1; }

/* Pruning list */
.pruning-list { display: flex; flex-direction: column; gap: 10px; }
.prune-item { background: var(--bg-surface-2, #f8fafc); border-radius: 8px; padding: 12px; font-size: 12px; }
.prune-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.prune-hyp-title { font-weight: 600; }
.status-tag { font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 600; }
.status-tag.active { background: #dbeafe; color: #1e40af; }
.status-tag.weakened { background: #fee2e2; color: #991b1b; }
.status-tag.supported { background: #dcfce7; color: #166534; }
.status-tag.needs_more_evidence { background: #fef3c7; color: #92400e; }
.prune-stats { display: flex; gap: 12px; font-size: 11px; color: var(--text-secondary, #64748b); margin-bottom: 6px; }
.prune-reason { margin: 0 0 6px 0; color: var(--text-primary, #334155); }
.prune-action { color: #0284c7; }

.explore-loading, .empty-hint { text-align: center; padding: 40px; color: var(--text-muted, #94a3b8); font-size: 13px; }
</style>
