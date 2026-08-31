<template>
  <div class="da-panel">
    <div class="da-header">
      <h3 class="da-title">{{ lang === 'en-US' ? 'Python Data Analysis Workbench' : 'Python 数据分析工作台' }}</h3>
      <p class="da-desc">{{ lang === 'en-US' ? 'Run sandboxed Python code to analyze experiment datasets (numpy, pandas, scipy, matplotlib supported).' : '受控沙箱执行 Python 代码，对实验数据进行清洗、统计分析与参数敏感度挖掘（支持 numpy / pandas / scipy / matplotlib）。' }}</p>
    </div>

    <!-- 运行空间与依赖自检条 -->
    <div style="background: var(--bg-surface-1); border: 1px solid var(--border-default); border-radius: 6px; padding: 8px 12px; margin-bottom: 14px; font-size: 11px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
      <div style="display: flex; align-items: center; gap: 8px;">
        <span style="color: var(--accent-science); font-weight: 600;"><i class="fa-solid fa-server"></i> {{ lang === 'en-US' ? 'Local Workspace:' : '本机运行空间:' }}</span>
        <code class="font-mono text-muted" style="max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ sysEnv?.working_directory || 'Local Python Environment' }}</code>
        <span class="badge-status badge-support font-mono">Python {{ sysEnv?.python_version || '3.x' }}</span>
      </div>
      <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
        <span style="color: var(--text-secondary);">{{ lang === 'en-US' ? 'Libraries:' : '依赖库自检:' }}</span>
        <span v-for="(info, pkg) in (sysEnv?.packages || {})" :key="pkg" class="font-mono" :style="{ color: info.installed ? 'var(--accent-success)' : 'var(--accent-warning)', cursor: 'default' }" :title="info.installed ? `${pkg} v${info.version} 已就绪` : `未安装，可在终端执行: ${info.install_cmd}`">
          {{ pkg }} {{ info.installed ? '✓' : '✕' }}
        </span>
      </div>
    </div>

    <!-- 顶部功能切换 -->
    <div style="display: flex; gap: 8px; margin-bottom: 16px;">
      <button class="btn-quick" :class="{ 'btn-action-primary': subTab === 'sandbox' }" @click="subTab = 'sandbox'">
        <i class="fa-brands fa-python"></i> {{ lang === 'en-US' ? 'Python Sandbox' : 'Python 沙箱代码' }}
      </button>
      <button class="btn-quick" :class="{ 'btn-action-primary': subTab === 'wizard' }" @click="subTab = 'wizard'; loadDatasets()">
        <i class="fa-solid fa-wand-magic-sparkles"></i> {{ lang === 'en-US' ? 'Analysis Wizard' : '🧙‍♂️ 统计分析向导' }}
      </button>
      <button class="btn-quick" :class="{ 'btn-action-primary': subTab === 'relationships' }" @click="subTab = 'relationships'; inspectRelationships()">
        <i class="fa-solid fa-diagram-project"></i> {{ lang === 'en-US' ? 'Schema Relations' : '🔗 数据表关系探测' }}
      </button>
    </div>

    <!-- 1. Python 沙箱区 -->
    <div v-if="subTab === 'sandbox'">
      <!-- 会话管理与快捷 EDA -->
      <div class="da-quick">
        <span class="da-quick-label">{{ lang === 'en-US' ? 'Analysis Sessions:' : '分析会话：' }}</span>
        <select v-model="selectedSessionId" @change="loadSession" class="record-select">
          <option value="">{{ lang === 'en-US' ? '-- New / Select Session --' : '-- 新建 / 加载历史分析会话 --' }}</option>
          <option v-for="s in savedSessions" :key="s.id" :value="s.id">{{ s.name }} ({{ s.created_at?.slice(5, 16) }})</option>
        </select>
        <button class="btn-quick" @click="saveAnalysisSession" :disabled="!code.trim()">
          <i class="fa-solid fa-floppy-disk"></i> {{ lang === 'en-US' ? 'Save Session' : '保存分析会话' }}
        </button>

        <span class="da-quick-label" style="margin-left: 12px;">{{ lang === 'en-US' ? 'Quick EDA:' : '快捷分析：' }}</span>
        <select v-model="selectedRecordId" class="record-select">
          <option value="">{{ lang === 'en-US' ? 'Select Experiment Record' : '选择实验方案 / 记录' }}</option>
          <option v-for="r in records" :key="r.id" :value="r.id">{{ r.task || r.id }}</option>
        </select>
        <button class="btn-quick" @click="runEDA" :disabled="!selectedRecordId || loading">
          <i class="fa-solid fa-flask"></i> {{ lang === 'en-US' ? 'Auto EDA' : '自动 EDA' }}
        </button>
      </div>

      <!-- 参数敏感度分析 -->
      <div class="da-section">
        <div class="da-section-header">
          <span>{{ lang === 'en-US' ? 'Parameter Sensitivity Analysis' : '参数敏感度分析 (Sensitivity Analysis)' }}</span>
          <button class="btn-sm" @click="runSensitivity" :disabled="loading">
            {{ lang === 'en-US' ? 'Analyze' : '执行分析' }}
          </button>
        </div>
        <input v-model="targetMetric" :placeholder="lang === 'en-US' ? 'Target Metric (e.g. accuracy)' : '目标评估指标（如 accuracy）'" class="metric-input" />
      </div>

      <!-- 代码编辑器 -->
      <div class="da-editor">
        <div class="editor-header">
          <span><i class="fa-brands fa-python" style="color: var(--accent-science);"></i> {{ lang === 'en-US' ? 'Python Sandbox Script' : 'Python 沙箱代码' }}</span>
          <button class="btn-run" @click="runCode" :disabled="!code.trim() || loading">
            {{ loading ? (lang === 'en-US' ? 'Executing...' : '执行中...') : (lang === 'en-US' ? '▶ Run Script' : '▶ 执行脚本') }}
          </button>
        </div>
        <textarea
          v-model="code"
          class="code-editor"
          rows="10"
          :placeholder="lang === 'en-US' ? '# Available variables: records (list of experiments), np, pd, plt\n# Example:\nfor r in records:\n    print(r.get(\'task\'), r.get(\'params\'))' : '# 可用内置变量：records（实验记录列表）, np, pd, plt\n# 示例：\nfor r in records:\n    print(r.get(\'task\'), r.get(\'params\'))'"
          spellcheck="false"
        ></textarea>
      </div>

      <!-- 结果 -->
      <div v-if="result" class="da-result">
        <div class="result-header">
          <span :class="result.success ? 'badge-ok' : 'badge-err'">
            {{ result.success ? (lang === 'en-US' ? '✓ Execution Succeeded' : '✅ 执行成功') : (lang === 'en-US' ? '✕ Execution Failed' : '❌ 执行失败') }}
          </span>
        </div>
        <pre v-if="result.stdout" class="result-stdout font-mono">{{ result.stdout }}</pre>
        <pre v-if="result.error" class="result-error font-mono">{{ result.error }}</pre>
        <!-- EDA 结构化结果 -->
        <div v-if="result.eda" class="eda-result">
          <div class="eda-item" v-if="result.eda.numeric_params"><strong>{{ lang === 'en-US' ? 'Numeric Params:' : '数值参数：' }}</strong> {{ JSON.stringify(result.eda.numeric_params) }}</div>
          <div class="eda-item" v-if="result.eda.error_count !== undefined"><strong>{{ lang === 'en-US' ? 'Errors Count:' : '异常数：' }}</strong> {{ result.eda.error_count }}</div>
          <div class="eda-item" v-if="result.eda.solution_count !== undefined"><strong>{{ lang === 'en-US' ? 'Solutions Count:' : '解决方案数：' }}</strong> {{ result.eda.solution_count }}</div>
          <div class="eda-item" v-if="result.eda.extracted_metrics && result.eda.extracted_metrics.length"><strong>{{ lang === 'en-US' ? 'Extracted Metrics:' : '提取指标：' }}</strong> {{ result.eda.extracted_metrics.join(', ') }}</div>
        </div>
        <!-- 敏感度结果 -->
        <div v-if="result.correlations" class="sensitivity-result">
          <div class="sens-title">{{ lang === 'en-US' ? `Parameter Correlation with ${result.target_metric} (${result.record_count} records)` : `参数与 ${result.target_metric} 的相关性分析（样本量：${result.record_count} 条）` }}</div>
          <table class="sens-table">
            <thead><tr><th>{{ lang === 'en-US' ? 'Parameter' : '参数项' }}</th><th>{{ lang === 'en-US' ? 'Correlation' : '相关系数' }}</th><th>{{ lang === 'en-US' ? 'Data Points' : '数据点' }}</th><th>{{ lang === 'en-US' ? 'Range' : '参数取值范围' }}</th></tr></thead>
            <tbody>
              <tr v-for="c in result.correlations" :key="c.param">
                <td class="font-mono">{{ c.param }}</td>
                <td :class="Math.abs(c.correlation) > 0.5 ? 'corr-high' : 'corr-low'" class="font-mono">{{ c.correlation }}</td>
                <td class="font-mono">{{ c.data_points }}</td>
                <td class="font-mono">{{ c.param_range && c.param_range.join(' ~ ') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <!-- 图表 -->
        <div v-if="result.charts && result.charts.length" class="charts-area">
          <img v-for="(chart, i) in result.charts" :key="i" :src="'data:image/png;base64,' + chart" class="result-chart" />
        </div>
        <!-- 保存为 Artifact -->
        <div class="result-actions" v-if="result.success">
          <button class="btn-save-art" @click="saveAsArtifact">
            <i class="fa-solid fa-floppy-disk"></i> {{ lang === 'en-US' ? 'Save as Artifact' : '保存为科研产物 (Artifact)' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 2. 统计分析向导 (Analysis Wizard) -->
    <div v-else-if="subTab === 'wizard'">
      <div style="background: var(--bg-surface-1); border: 1px solid var(--border-default); border-radius: 8px; padding: 16px; margin-bottom: 16px;">
        <h4 style="margin: 0 0 12px 0;"><i class="fa-solid fa-wand-magic-sparkles" style="color: var(--accent-science);"></i> 交互式统计分析向导</h4>
        <div style="display: flex; gap: 8px; margin-bottom: 12px;">
          <input v-model="wizardIntent" placeholder="输入分析意图（例如：比较 A/B 两组均值差异、数值相关性矩阵）" class="search-input" style="flex: 1;" />
          <select v-model="wizardDsId" class="source-select">
            <option value="">选择数据集</option>
            <option v-for="ds in projectDatasets" :key="ds.id" :value="ds.id">{{ ds.name }} ({{ ds.row_count }} 行)</option>
          </select>
          <button class="btn-run" :disabled="!wizardIntent.trim() || !wizardDsId || wizardLoading" @click="generateWizardPlan">
            {{ wizardLoading ? '生成中...' : '生成方案' }}
          </button>
        </div>

        <!-- 方案展示 -->
        <div v-if="wizardPlan" style="background: var(--bg-surface-2); border: 1px solid var(--border-default); border-radius: 6px; padding: 14px; margin-top: 12px;">
          <div style="font-weight: 600; font-size: 13px; margin-bottom: 6px; color: var(--accent-science);">📋 推荐分析方案：{{ wizardPlan.description }}</div>
          <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 8px;">推荐 SQL 查询：</div>
          <pre class="result-stdout font-mono" style="margin-bottom: 12px;">{{ wizardPlan.suggested_sql }}</pre>
          <button class="btn-run" :disabled="executingWizard" @click="executeWizardPlan">
            {{ executingWizard ? '执行中...' : '▶ 执行并沉淀为 Artifact' }}
          </button>
        </div>

        <!-- 向导执行结果 -->
        <div v-if="wizardResult" style="margin-top: 16px;">
          <div style="font-weight: 600; font-size: 13px; color: var(--accent-support); margin-bottom: 8px;">✓ 执行成功，已生成 Artifact (耗时: {{ wizardResult.duration_ms }} ms)</div>
          <table class="sens-table" v-if="wizardResult.results?.rows?.length">
            <thead><tr><th v-for="c in wizardResult.results.columns" :key="c">{{ c }}</th></tr></thead>
            <tbody>
              <tr v-for="(row, idx) in wizardResult.results.rows" :key="idx">
                <td v-for="(val, cidx) in row" :key="cidx" class="font-mono">{{ val }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 3. 数据表关系探测 -->
    <div v-else-if="subTab === 'relationships'">
      <div style="background: var(--bg-surface-1); border: 1px solid var(--border-default); border-radius: 8px; padding: 16px;">
        <h4 style="margin: 0 0 8px 0;"><i class="fa-solid fa-diagram-project" style="color: var(--accent-science);"></i> 多数据集 Schema 与外键关联发现</h4>
        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 14px;">自动识别项目内多个数据表的实体键名，推断潜在 JOIN 路径 (标记为 AI Inferred)。</div>
        <div v-if="discoveredRelations.length === 0" class="empty-hint">当前项目数据表中未发现重叠外键，或数据集少于 2 个。</div>
        <div v-else style="display: flex; flex-direction: column; gap: 8px;">
          <div v-for="(rel, i) in discoveredRelations" :key="i" style="padding: 12px; background: var(--bg-surface-2); border: 1px solid var(--border-default); border-radius: 6px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <strong>{{ rel.dataset_a_name }} ⟷ {{ rel.dataset_b_name }}</strong>
              <span class="badge-status badge-active">可信度 {{ Math.round(rel.confidence * 100) }}% ({{ rel.source }})</span>
            </div>
            <div style="font-size: 12px; color: var(--text-secondary);">关联键：<code class="font-mono">{{ rel.join_key }}</code> · {{ rel.description }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DataAnalysisPanel',
  props: {
    projectId: { type: String, required: true },
    records: { type: Array, default: () => [] },
    lang: { type: String, default: 'zh-CN' },
  },
  data() {
    return {
      subTab: 'sandbox',
      code: '',
      selectedRecordId: '',
      selectedSessionId: '',
      savedSessions: [],
      targetMetric: 'accuracy',
      loading: false,
      result: null,
      projectDatasets: [],
      wizardIntent: '比较 A/B 两组均值差异',
      wizardDsId: '',
      wizardLoading: false,
      wizardPlan: null,
      executingWizard: false,
      wizardResult: null,
      discoveredRelations: [],
      sysEnv: null,
    }
  },
  mounted() {
    this.loadSavedSessions()
    this.loadDatasets()
    this.loadSystemEnvironment()
  },
  methods: {
    async loadSystemEnvironment() {
      try {
        const r = await fetch('/api/system/environment')
        if (r.ok) {
          this.sysEnv = await r.json()
        }
      } catch (e) {
        console.error('加载系统环境失败:', e)
      }
    },
    async loadSavedSessions() {
      try {
        const r = await fetch(`/api/projects/${this.projectId}/analyses`)
        if (r.ok) {
          const data = await r.json()
          this.savedSessions = data.analyses || []
        }
      } catch (e) {
        console.error('加载分析会话失败:', e)
      }
    },
    async saveAnalysisSession() {
      const name = prompt(this.lang === 'en-US' ? 'Enter Analysis Session Name:' : '请输入分析会话名称：', 'Parameter Ablation Study')
      if (!name) return
      try {
        const r = await fetch(`/api/projects/${this.projectId}/analyses`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name,
            code: this.code,
            stdout: this.result?.stdout || '',
            charts: this.result?.charts || [],
            insights: this.result?.stdout ? `Executed on ${new Date().toISOString()}` : '',
            experiment_id: this.selectedRecordId || null,
          }),
        })
        if (r.ok) {
          alert(this.lang === 'en-US' ? 'Analysis session saved!' : '分析会话已成功保存！')
          await this.loadSavedSessions()
        }
      } catch (e) {
        alert('保存失败: ' + e.message)
      }
    },
    loadSession() {
      if (!this.selectedSessionId) return
      const s = this.savedSessions.find(x => x.id === this.selectedSessionId)
      if (s) {
        this.code = s.code || ''
        this.result = {
          success: true,
          stdout: s.stdout || '',
          charts: s.charts || [],
          error: null,
        }
      }
    },
    async runCode() {
      if (!this.code.trim()) return
      this.loading = true
      this.result = null
      try {
        const r = await fetch('/api/data/python', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            code: this.code,
            context: {},
          }),
        })
        this.result = await r.json()
      } catch (e) {
        this.result = { success: false, error: e.message }
      } finally {
        this.loading = false
      }
    },
    async runEDA() {
      if (!this.selectedRecordId) return
      this.loading = true
      this.result = null
      try {
        const r = await fetch('/api/data/eda', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ record_id: this.selectedRecordId }),
        })
        this.result = await r.json()
      } catch (e) {
        this.result = { success: false, error: e.message }
      } finally {
        this.loading = false
      }
    },
    async runSensitivity() {
      this.loading = true
      this.result = null
      try {
        const ids = this.records.map(r => r.id)
        const r = await fetch(`/api/projects/${this.projectId}/analyze/sensitivity`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ record_ids: ids, target_metric: this.targetMetric }),
        })
        this.result = await r.json()
      } catch (e) {
        this.result = { success: false, error: e.message }
      } finally {
        this.loading = false
      }
    },
    async saveAsArtifact() {
      const name = prompt(this.lang === 'en-US' ? 'Artifact Name:' : '请输入 Artifact 资产名称：', 'analysis_chart')
      if (!name) return
      try {
        await fetch('/api/artifacts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_id: this.projectId,
            name,
            type: 'analysis',
            content: JSON.stringify(this.result),
            source_record_id: this.selectedRecordId || null,
          }),
        })
        alert(this.lang === 'en-US' ? 'Artifact saved successfully!' : '已成功保存为科研产物！')
        this.$emit('artifact-created')
      } catch (e) {
        alert(this.lang === 'en-US' ? 'Failed to save: ' + e.message : '保存失败：' + e.message)
      }
    },
    async loadDatasets() {
      try {
        const r = await fetch(`/api/projects/${this.projectId}/datasets`)
        if (r.ok) {
          const d = await r.json()
          this.projectDatasets = d.datasets || []
          if (!this.wizardDsId && this.projectDatasets.length > 0) {
            this.wizardDsId = this.projectDatasets[0].id
          }
        }
      } catch (e) {
        console.error(e)
      }
    },
    async generateWizardPlan() {
      if (!this.wizardIntent.trim() || !this.wizardDsId) return
      this.wizardLoading = true
      this.wizardPlan = null
      this.wizardResult = null
      try {
        const r = await fetch(`/api/projects/${this.projectId}/datasets/wizard/plan`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            intent: this.wizardIntent.trim(),
            dataset_ids: [this.wizardDsId],
          }),
        })
        if (r.ok) {
          this.wizardPlan = await r.json()
        }
      } catch (e) {
        alert('生成方案失败: ' + e.message)
      } finally {
        this.wizardLoading = false
      }
    },
    async executeWizardPlan() {
      if (!this.wizardPlan) return
      this.executingWizard = true
      this.wizardResult = null
      try {
        const r = await fetch(`/api/projects/${this.projectId}/datasets/wizard/execute`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: this.wizardPlan.description || 'Statistical Analysis',
            dataset_id: this.wizardDsId,
            sql_query: this.wizardPlan.suggested_sql,
            python_code: this.wizardPlan.suggested_python,
          }),
        })
        if (r.ok) {
          this.wizardResult = await r.json()
          this.$emit('artifact-created')
        }
      } catch (e) {
        alert('执行失败: ' + e.message)
      } finally {
        this.executingWizard = false
      }
    },
    async inspectRelationships() {
      await this.loadDatasets()
      if (this.projectDatasets.length < 2) {
        this.discoveredRelations = []
        return
      }
      try {
        const r = await fetch(`/api/projects/${this.projectId}/datasets/relationships`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            dataset_ids: this.projectDatasets.map(d => d.id),
          }),
        })
        if (r.ok) {
          const res = await r.json()
          this.discoveredRelations = res.relationships || []
        }
      } catch (e) {
        console.error(e)
      }
    },
  },
}
</script>

<style scoped>
.da-panel {
  padding: 0;
  color: var(--text-primary);
}
.da-header { margin-bottom: 20px; }
.da-title { font-size: 18px; margin: 0 0 6px; color: var(--text-primary); font-weight: 600; }
.da-desc { color: var(--text-secondary); font-size: 13px; margin: 0; line-height: 1.5; }
.da-quick { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.da-quick-label { font-size: 12px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; }
.btn-quick { background: var(--bg-surface-2); border: 1px solid var(--border-default); color: var(--text-primary); border-radius: 6px; padding: 5px 12px; cursor: pointer; font-size: 12px; font-weight: 500; transition: all .15s ease; }
.btn-quick:hover { background: var(--bg-hover); border-color: var(--border-active); }
.btn-quick:disabled { opacity: .5; cursor: not-allowed; }
.record-select { background: var(--bg-surface-2); color: var(--text-primary); border: 1px solid var(--border-default); border-radius: 6px; padding: 5px 8px; font-size: 12px; }
.da-section { margin-bottom: 16px; background: var(--bg-surface-1); border: 1px solid var(--border-default); border-radius: 8px; padding: 12px 16px; }
.da-section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; font-size: 12px; font-weight: 600; color: var(--text-primary); }
.metric-input { width: 220px; background: var(--bg-surface-2); color: var(--text-primary); border: 1px solid var(--border-default); border-radius: 6px; padding: 6px 10px; font-size: 12px; outline: none; }
.da-editor { margin-bottom: 20px; border: 1px solid var(--border-default); border-radius: 8px; overflow: hidden; background: var(--bg-surface-1); }
.editor-header { display: flex; align-items: center; justify-content: space-between; padding: 8px 14px; background: var(--bg-surface-2); border-bottom: 1px solid var(--border-default); font-size: 12px; font-weight: 600; color: var(--text-primary); }
.btn-run { background: var(--accent-science); color: #fff; border: none; border-radius: 6px; padding: 5px 14px; cursor: pointer; font-size: 12px; font-weight: 600; transition: opacity .15s; }
.btn-run:hover { opacity: .9; }
.btn-run:disabled { opacity: .5; cursor: not-allowed; }
.code-editor { width: 100%; border: none; padding: 14px; font-family: var(--font-mono); font-size: 12px; resize: vertical; outline: none; background: var(--bg-surface-1); color: var(--text-primary); line-height: 1.6; box-sizing: border-box; }
.da-result { margin-top: 16px; border: 1px solid var(--border-default); border-radius: 8px; overflow: hidden; background: var(--bg-surface-1); }
.result-header { padding: 8px 14px; background: var(--bg-surface-2); border-bottom: 1px solid var(--border-default); }
.badge-ok { color: var(--accent-success); font-size: 12px; font-weight: 600; }
.badge-err { color: var(--accent-danger); font-size: 12px; font-weight: 600; }
.result-stdout { padding: 12px; font-family: var(--font-mono); font-size: 12px; white-space: pre-wrap; word-break: break-all; background: var(--bg-canvas); color: var(--text-primary); margin: 0; border-bottom: 1px solid var(--border-default); }
.result-error { padding: 12px; font-family: var(--font-mono); font-size: 12px; color: var(--accent-danger); white-space: pre-wrap; background: var(--accent-danger-dim); margin: 0; }
.eda-result { padding: 14px; display: flex; flex-direction: column; gap: 8px; background: var(--bg-surface-1); }
.eda-item { font-size: 12px; color: var(--text-secondary); }
.result-chart { max-width: 100%; margin: 14px; border-radius: 6px; border: 1px solid var(--border-default); }
.charts-area { padding: 0 8px 8px; }
.sensitivity-result { padding: 14px; background: var(--bg-surface-1); }
.sens-title { font-size: 12px; font-weight: 600; margin-bottom: 10px; color: var(--text-primary); }
.sens-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.sens-table th, .sens-table td { border: 1px solid var(--border-default); padding: 7px 12px; text-align: left; }
.sens-table th { background: var(--bg-surface-2); color: var(--text-muted); font-weight: 600; }
.corr-high { color: var(--accent-science); font-weight: 700; }
.corr-low { color: var(--text-muted); }
.result-actions { padding: 10px 14px; border-top: 1px solid var(--border-default); background: var(--bg-surface-2); }
.btn-save-art { background: var(--bg-surface-1); border: 1px solid var(--border-default); color: var(--text-primary); border-radius: 6px; padding: 5px 12px; cursor: pointer; font-size: 12px; font-weight: 500; }
.btn-save-art:hover { background: var(--bg-hover); border-color: var(--border-active); }
.btn-sm { font-size: 11px; padding: 3px 10px; border: 1px solid var(--border-default); border-radius: 4px; background: var(--bg-surface-2); color: var(--text-primary); cursor: pointer; }
.btn-sm:hover { background: var(--bg-hover); }
</style>
