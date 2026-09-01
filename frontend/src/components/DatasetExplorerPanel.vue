<template>
  <div class="dataset-panel">
    <div class="ds-header">
      <h3 class="ds-title">{{ lang === 'en-US' ? 'Scientific Dataset Explorer & DuckDB Engine' : '科研数据集检索与本地 SQL 分析引擎' }}</h3>
      <p class="ds-desc">{{ lang === 'en-US' ? 'Discover Hugging Face & Papers With Code datasets, import local CSVs, and run fast in-memory DuckDB SQL queries.' : '检索 Hugging Face 与 Papers With Code 公开数据集，导入本地数据并通过 DuckDB 执行秒级 SQL 聚合分析。' }}</p>
    </div>

    <!-- 顶部选项卡 -->
    <div style="display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;">
      <button class="btn-secondary" :class="{ 'btn-action-primary': activeTab === 'search' }" @click="activeTab = 'search'">
        <i class="fa-solid fa-magnifying-glass"></i> {{ lang === 'en-US' ? 'Search Online Datasets' : '在线检索公共数据集' }}
      </button>
      <button class="btn-secondary" :class="{ 'btn-action-primary': activeTab === 'saved' }" @click="activeTab = 'saved'; loadSavedDatasets()">
        <i class="fa-solid fa-database"></i> {{ lang === 'en-US' ? 'Project Datasets' : '课题关联的数据集' }} ({{ savedDatasets.length }})
      </button>
      <button class="btn-secondary" :class="{ 'btn-action-primary': activeTab === 'upload' }" @click="activeTab = 'upload'">
        <i class="fa-solid fa-file-csv"></i> {{ lang === 'en-US' ? 'Create / Upload Local CSV' : '创建/上传本地数据集' }}
      </button>
    </div>

    <!-- 1. 在线检索公开数据集 -->
    <div v-if="activeTab === 'search'">
      <div class="search-box">
        <input
          v-model="searchQuery"
          :placeholder="lang === 'en-US' ? 'Search datasets (e.g. mnist, glue, squad, pointcloud)...' : '输入数据集关键词（例如：squad, cifar, dynamic graph, medical）...'"
          class="search-input"
          @keyup.enter="handleSearch"
        />
        <select v-model="searchSource" class="source-select">
          <option value="huggingface">🤗 Hugging Face Hub (百万开源数据集)</option>
          <option value="papers_with_code">📊 Papers With Code (学术基准)</option>
        </select>
        <button class="btn-search" :disabled="!searchQuery.trim() || searching" @click="handleSearch">
          {{ searching ? (lang === 'en-US' ? 'Searching...' : '检索中...') : (lang === 'en-US' ? 'Search Datasets' : '检索数据集') }}
        </button>
      </div>

      <!-- 搜索状态 -->
      <div v-if="searching" class="empty-hint">{{ lang === 'en-US' ? 'Querying dataset repositories...' : '正在检索公开数据集仓库…' }}</div>
      <div v-else-if="searched && searchResults.length === 0" class="empty-hint">
        {{ lang === 'en-US' ? 'No related datasets found. Try adjusting keywords.' : '未检索到相关数据集，请尝试调整关键词' }}
      </div>

      <!-- 数据集列表 -->
      <div v-else class="dataset-list">
        <div v-for="ds in searchResults" :key="ds.dataset_id || ds.id" class="dataset-card">
          <div class="ds-card-header">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="badge-status badge-support">{{ ds.source?.toUpperCase() }}</span>
              <a :href="ds.url" target="_blank" class="ds-card-title">{{ ds.name }}</a>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
              <span v-if="ds.downloads" class="font-mono text-muted" style="font-size: 11px;">
                <i class="fa-solid fa-download"></i> {{ ds.downloads.toLocaleString() }}
              </span>
              <span v-if="ds.likes" class="font-mono text-muted" style="font-size: 11px;">
                <i class="fa-solid fa-heart" style="color: #f43f5e;"></i> {{ ds.likes }}
              </span>
              <span v-if="ds.papers_count" class="font-mono text-muted" style="font-size: 11px;">
                <i class="fa-solid fa-book"></i> {{ ds.papers_count }} 篇引用论文
              </span>
              <button class="btn-action-primary" style="font-size: 11px; padding: 4px 10px;" @click="saveOnlineDataset(ds)">
                <i class="fa-solid fa-plus"></i> {{ lang === 'en-US' ? 'Save to Project' : '★ 沉淀至课题' }}
              </button>
            </div>
          </div>

          <div class="ds-card-desc">{{ ds.description }}</div>

          <!-- 标签与任务 -->
          <div class="ds-tags-row">
            <span v-if="ds.license" class="ds-tag license"><i class="fa-solid fa-scale-balanced"></i> {{ ds.license }}</span>
            <span v-for="t in (ds.tasks || []).slice(0, 4)" :key="t" class="ds-tag task">{{ t }}</span>
            <span v-for="m in (ds.modalities || []).slice(0, 3)" :key="m" class="ds-tag modality">{{ m }}</span>
          </div>

          <!-- 代码载入片段 -->
          <div v-if="ds.load_code" class="code-snippet-box">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <span class="font-mono text-muted" style="font-size: 10px;">{{ lang === 'en-US' ? 'PYTHON LOADER:' : 'Python 载入代码:' }}</span>
              <button class="btn-copy-code" @click="copyCode(ds.load_code)">{{ lang === 'en-US' ? 'Copy Code' : '复制' }}</button>
            </div>
            <pre class="code-content">{{ ds.load_code }}</pre>
          </div>
        </div>
      </div>
    </div>

    <!-- 2. 课题关联的数据集列表 & DuckDB SQL 查询 -->
    <div v-if="activeTab === 'saved'">
      <div v-if="!savedDatasets.length" class="empty-hint">
        {{ lang === 'en-US' ? 'No datasets associated with this project yet. Search online or upload a local CSV.' : '当前课题暂未沉淀数据集。点击上方「在线检索公共数据集」或「创建/上传本地数据集」开始。' }}
      </div>

      <div v-else style="display: flex; flex-direction: column; gap: 16px;">
        <div v-for="d in savedDatasets" :key="d.id || d.dataset_id" class="card" style="background: var(--bg-surface-1); border: 1px solid var(--border-default); border-radius: 10px; padding: 16px;">
          <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-default); padding-bottom: 10px; margin-bottom: 10px;">
            <div style="display: flex; align-items: center; gap: 10px;">
              <span class="badge-status badge-support">{{ d.format === 'csv' ? 'LOCAL CSV' : 'ONLINE' }}</span>
              <strong class="text-primary" style="font-size: 14px;">{{ d.name }}</strong>
              <span class="font-mono text-muted" style="font-size: 11px;">{{ d.id }}</span>
            </div>
            <div style="display: flex; gap: 8px;">
              <button v-if="d.format === 'csv'" class="btn-secondary" style="font-size: 11px;" @click="openSqlWorkbench(d)">
                <i class="fa-solid fa-terminal"></i> {{ lang === 'en-US' ? 'DuckDB SQL Workbench' : '🦆 DuckDB SQL 分析' }}
              </button>
              <button class="btn-secondary" style="font-size: 11px; color: #ef4444;" @click="deleteDataset(d.id)">
                <i class="fa-solid fa-trash-can"></i>
              </button>
            </div>
          </div>

          <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;">{{ d.description || 'No description provided.' }}</div>

          <div style="display: flex; gap: 16px; font-size: 11px;" class="font-mono text-muted">
            <span v-if="d.row_count !== undefined"><i class="fa-solid fa-table-cells"></i> {{ d.row_count }} 行</span>
            <span v-if="d.columns?.length"><i class="fa-solid fa-table-columns"></i> 字段: {{ d.columns.join(', ') }}</span>
            <span v-if="d.url"><a :href="d.url" target="_blank" style="color: var(--accent-science); text-decoration: none;"><i class="fa-solid fa-arrow-up-right-from-square"></i> 访问数据集主页</a></span>
          </div>

          <!-- Python loader for online datasets -->
          <div v-if="d.load_code" class="code-snippet-box" style="margin-top: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <span class="font-mono text-muted" style="font-size: 10px;">Python 加载指令:</span>
              <button class="btn-copy-code" @click="copyCode(d.load_code)">复制</button>
            </div>
            <pre class="code-content">{{ d.load_code }}</pre>
          </div>
        </div>
      </div>

      <!-- DuckDB SQL 交互式分析模态框 -->
      <div v-if="activeSqlDataset" class="modal-mask" @click.self="activeSqlDataset = null">
        <div class="modal-card" style="width: 720px;">
          <div class="modal-header">
            <h3>🦆 DuckDB 本地 SQL 极速聚合分析 ({{ activeSqlDataset.name }})</h3>
            <button class="btn-close" @click="activeSqlDataset = null"><i class="fa-solid fa-xmark"></i></button>
          </div>

          <div style="display: flex; flex-direction: column; gap: 12px; flex: 1; overflow-y: auto;">
            <div style="font-size: 12px; color: var(--text-secondary);">
              可使用 <code>dataset</code> 或 <code>df</code> 作为表名进行 DuckDB SQL 结构化统计查询：
            </div>

            <div style="display: flex; gap: 8px;">
              <input
                v-model="sqlQuery"
                class="search-input"
                style="font-family: var(--font-mono, monospace); font-size: 12px;"
                placeholder="例如: SELECT * FROM dataset WHERE lr > 0.001 ORDER BY accuracy DESC LIMIT 10"
                @keyup.enter="executeSql"
              />
              <button class="btn-action-primary" :disabled="!sqlQuery.trim() || sqlRunning" @click="executeSql">
                {{ sqlRunning ? '执行中...' : '运行 SQL' }}
              </button>
            </div>

            <!-- SQL 结果表格 -->
            <div v-if="sqlResult" style="margin-top: 10px;">
              <div v-if="!sqlResult.success" style="color: #ef4444; font-size: 12px; padding: 10px; background: rgba(239,68,68,0.1); border-radius: 6px;">
                SQL 错误: {{ sqlResult.error }}
              </div>
              <div v-else style="max-height: 280px; overflow: auto; border: 1px solid var(--border-default); border-radius: 6px;">
                <table class="sql-table">
                  <thead>
                    <tr>
                      <th v-for="col in sqlResult.columns" :key="col">{{ col }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, ri) in sqlResult.rows" :key="ri">
                      <td v-for="col in sqlResult.columns" :key="col">{{ row[col] }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 3. 创建/上传本地 CSV 数据集 -->
    <div v-if="activeTab === 'upload'" class="card" style="padding: 20px; background: var(--bg-surface-1); border: 1px solid var(--border-default); border-radius: 10px;">
      <div style="margin-bottom: 16px;">
        <h4 style="margin: 0; font-size: 14px; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
          <i class="fa-solid fa-cloud-arrow-up" style="color: var(--accent-science);"></i>
          <span>{{ lang === 'en-US' ? 'Create Local Dataset from CSV' : '创建/上传本地 CSV 数据集' }}</span>
        </h4>
        <p style="margin: 4px 0 0; font-size: 12px; color: var(--text-secondary);">
          {{ lang === 'en-US' ? 'Paste raw CSV text or upload a CSV file to register as a queryable local dataset.' : '在此粘贴 CSV 文本或选择本地 CSV 文件，系统将自动建立结构化数据模式并开启 DuckDB 极速分析。' }}
        </p>
      </div>

      <div class="form-group" style="margin-bottom: 12px;">
        <label class="form-label">数据集名称</label>
        <input v-model="newDatasetForm.name" placeholder="例如：facial_landmarks_noise_benchmark.csv" class="modal-input" />
      </div>

      <div class="form-group" style="margin-bottom: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <label class="form-label" style="margin-bottom: 0;">CSV 数据内容</label>
          <button class="btn-secondary" style="font-size: 11px;" @click="fillSampleCsv">填入示例科研数据</button>
        </div>
        <textarea
          v-model="newDatasetForm.csvContent"
          placeholder="epoch,learning_rate,k_neighbors,accuracy,loss&#10;1,0.001,8,0.72,0.65&#10;2,0.001,16,0.83,0.42"
          rows="8"
          class="modal-textarea"
          style="font-family: var(--font-mono, monospace); font-size: 12px;"
        ></textarea>
      </div>

      <div style="display: flex; justify-content: flex-end;">
        <button
          class="btn-action-primary"
          :disabled="!newDatasetForm.name.trim() || !newDatasetForm.csvContent.trim() || uploading"
          @click="handleCreateCsvDataset"
          style="padding: 8px 18px;"
        >
          <i class="fa-solid fa-plus"></i>
          <span>{{ uploading ? '创建中...' : '确认创建并沉淀' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DatasetExplorerPanel',
  props: {
    projectId: { type: String, required: true },
    lang: { type: String, default: 'zh-CN' },
  },
  data() {
    return {
      activeTab: 'search',
      searchQuery: '',
      searchSource: 'huggingface',
      searchResults: [],
      searching: false,
      searched: false,
      savedDatasets: [],
      newDatasetForm: {
        name: '',
        csvContent: '',
      },
      uploading: false,
      activeSqlDataset: null,
      sqlQuery: 'SELECT * FROM dataset LIMIT 20',
      sqlResult: null,
      sqlRunning: false,
    }
  },
  mounted() {
    this.loadSavedDatasets()
  },
  methods: {
    async loadSavedDatasets() {
      try {
        const resp = await fetch(`/api/projects/${this.projectId}/datasets`)
        if (resp.ok) {
          const data = await resp.json()
          this.savedDatasets = data.datasets || []
        }
      } catch (e) {
        console.error('加载数据集列表失败:', e)
      }
    },
    async handleSearch() {
      if (!this.searchQuery.trim()) return
      this.searching = true
      this.searched = true
      try {
        const resp = await fetch(`/api/datasets/search?query=${encodeURIComponent(this.searchQuery)}&source=${this.searchSource}&limit=12`)
        if (resp.ok) {
          const data = await resp.json()
          this.searchResults = data.datasets || []
        } else {
          alert('检索失败')
        }
      } catch (e) {
        alert('检索请求失败: ' + e.message)
      } finally {
        this.searching = false
      }
    },
    async saveOnlineDataset(dataset) {
      try {
        const resp = await fetch(`/api/projects/${this.projectId}/datasets/import-online`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ dataset }),
        })
        if (resp.ok) {
          alert(this.lang === 'en-US' ? 'Dataset saved to project!' : '数据集已成功沉淀至课题！')
          await this.loadSavedDatasets()
          this.$emit('refresh')
        } else {
          alert('保存失败')
        }
      } catch (e) {
        alert('保存错误: ' + e.message)
      }
    },
    async deleteDataset(datasetId) {
      if (!confirm('确定删除该数据集？')) return
      try {
        await fetch(`/api/datasets/${datasetId}`, { method: 'DELETE' })
        await this.loadSavedDatasets()
        this.$emit('refresh')
      } catch (e) {
        alert('删除失败: ' + e.message)
      }
    },
    fillSampleCsv() {
      this.newDatasetForm.name = 'graph_topological_noise_benchmark.csv'
      this.newDatasetForm.csvContent = `epoch,k_neighbors,learning_rate,accuracy,loss,f1_score\n1,8,0.001,0.724,0.612,0.710\n2,12,0.001,0.781,0.510,0.774\n3,16,0.0005,0.832,0.380,0.829\n4,20,0.0005,0.865,0.312,0.860\n5,24,0.0002,0.871,0.289,0.868`
    },
    async handleCreateCsvDataset() {
      if (!this.newDatasetForm.name.trim() || !this.newDatasetForm.csvContent.trim()) return
      this.uploading = true
      try {
        const resp = await fetch(`/api/projects/${this.projectId}/datasets`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: this.newDatasetForm.name,
            csv_content: this.newDatasetForm.csvContent,
          }),
        })
        if (resp.ok) {
          alert('数据集创建并沉淀成功！')
          this.newDatasetForm.name = ''
          this.newDatasetForm.csvContent = ''
          this.activeTab = 'saved'
          await this.loadSavedDatasets()
          this.$emit('refresh')
        } else {
          alert('创建失败')
        }
      } catch (e) {
        alert('创建错误: ' + e.message)
      } finally {
        this.uploading = false
      }
    },
    openSqlWorkbench(dataset) {
      this.activeSqlDataset = dataset
      this.sqlQuery = 'SELECT * FROM dataset LIMIT 20'
      this.sqlResult = null
      this.executeSql()
    },
    async executeSql() {
      if (!this.activeSqlDataset || !this.sqlQuery.trim()) return
      this.sqlRunning = true
      try {
        const resp = await fetch(`/api/datasets/${this.activeSqlDataset.id}/query`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sql: this.sqlQuery, limit: 50 }),
        })
        if (resp.ok) {
          this.sqlResult = await resp.json()
        }
      } catch (e) {
        this.sqlResult = { success: false, error: e.message }
      } finally {
        this.sqlRunning = false
      }
    },
    copyCode(code) {
      navigator.clipboard.writeText(code)
      alert('已复制到剪贴板！')
    },
  },
}
</script>

<style scoped>
.dataset-panel {
  display: flex;
  flex-direction: column;
}
.ds-header {
  margin-bottom: 20px;
}
.ds-title {
  font-size: 16px;
  font-weight: 700;
  margin: 0 0 6px 0;
  color: var(--text-primary);
}
.ds-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0;
}
.search-box {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}
.search-input {
  flex: 1;
  padding: 8px 12px;
  background: var(--bg-surface-1);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
}
.source-select {
  padding: 8px 12px;
  background: var(--bg-surface-1);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
}
.btn-search {
  padding: 8px 16px;
  background: var(--accent-science);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
}
.btn-search:disabled { opacity: 0.6; cursor: not-allowed; }
.empty-hint {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
  font-size: 13px;
  font-style: italic;
}
.dataset-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.dataset-card {
  background: var(--bg-surface-1);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ds-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.ds-card-title {
  font-weight: 700;
  font-size: 14px;
  color: var(--accent-science);
  text-decoration: none;
}
.ds-card-title:hover { text-decoration: underline; }
.ds-card-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}
.ds-tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.ds-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}
.ds-tag.license { background: rgba(59, 130, 246, 0.15); color: #60a5fa; }
.ds-tag.task { background: rgba(16, 185, 129, 0.15); color: #34d399; }
.ds-tag.modality { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }

.code-snippet-box {
  background: var(--bg-surface-2, #0f172a);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  padding: 8px 12px;
}
.code-content {
  margin: 0;
  font-family: var(--font-mono, monospace);
  font-size: 11px;
  color: var(--text-primary);
  white-space: pre-wrap;
}
.btn-copy-code {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  border-radius: 4px;
  font-size: 10px;
  padding: 1px 6px;
  cursor: pointer;
}
.btn-copy-code:hover { color: var(--text-primary); }

.sql-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  font-family: var(--font-mono, monospace);
}
.sql-table th, .sql-table td {
  padding: 8px 10px;
  border: 1px solid var(--border-default);
  text-align: left;
}
.sql-table th {
  background: var(--bg-surface-2);
  color: var(--accent-science);
  font-weight: 700;
}
.sql-table td {
  color: var(--text-primary);
}

.modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-card {
  background: var(--bg-surface-1);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  max-height: 85vh;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border-default);
  padding-bottom: 12px;
}

.modal-header h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.btn-close {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 16px;
  cursor: pointer;
  padding: 4px;
}

.btn-close:hover {
  color: var(--text-primary);
}
</style>
