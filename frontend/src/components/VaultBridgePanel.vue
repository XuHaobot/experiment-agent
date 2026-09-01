<template>
  <div class="vault-bridge-container">
    <div class="panel-header">
      <div>
        <h2 class="panel-title">📓 Obsidian Knowledge Layer (Vault Bridge)</h2>
        <p class="panel-subtitle">
          将当前科研课题的假说、实验、证据、结论无损投影至 Obsidian Vault，支持标准 YAML Frontmatter 与 [[Wikilinks]]。
        </p>
      </div>
      <div class="header-actions">
        <button class="btn-secondary" @click="handleReconcile" :disabled="isLoading">
          🔍 检查修改状态 (Reconcile)
        </button>
        <button class="btn-primary" @click="handlePreview" :disabled="isLoading">
          👁️ 预览导出 (Preview)
        </button>
      </div>
    </div>

    <!-- Configuration Card -->
    <div class="config-card">
      <div class="field-row">
        <label class="field-label">Obsidian Vault 路径 (本地磁盘目录)</label>
        <div class="input-row">
          <input
            v-model="vaultPath"
            placeholder="例如: E:\MyObsidianVault 或 /Users/name/Vault"
            class="input-path"
            spellcheck="false"
          />
          <button class="btn-export" @click="handleExport" :disabled="!vaultPath.trim() || isLoading">
            🚀 导出至 Obsidian
          </button>
        </div>
        <p class="field-tip">
          💡 导出会按 <code>00_Project</code>、<code>02_Hypotheses</code>、<code>04_Evidence</code> 等子目录生成原子 Markdown。
          <b>用户在文件内撰写的笔记内容绝不会被覆盖</b>。
        </p>
      </div>
    </div>

    <!-- Status Banner / Result Card -->
    <div v-if="exportResult" class="result-card" :class="{ success: exportResult.success }">
      <div class="result-header">
        <span class="result-icon">✅</span>
        <span class="result-title">成功同步至 Obsidian Vault</span>
      </div>
      <div class="result-stats">
        <div class="stat-badge new">新建: {{ exportResult.files_created }}</div>
        <div class="stat-badge update">更新: {{ exportResult.files_updated }}</div>
        <div class="stat-badge skip">跳过(未变): {{ exportResult.files_skipped }}</div>
        <div class="stat-badge total">总托管实体: {{ exportResult.total_managed }}</div>
      </div>
      <div class="result-tip">
        已在目标目录建立 <code>ResearchOS/manifest.json</code> 托管清单。你现在可以在 Obsidian 中打开并使用 <b>Graph View</b> 浏览双链知识网。
      </div>
    </div>

    <!-- Reconcile Table -->
    <div v-if="reconcileResult && reconcileResult.items" class="reconcile-card">
      <div class="reconcile-header">
        <h3>🔍 Vault 状态检查结果 (共 {{ reconcileResult.total_managed }} 个托管文件)</h3>
      </div>
      <div class="reconcile-list">
        <div v-for="item in reconcileResult.items" :key="item.rel_path" class="reconcile-item">
          <span class="item-path">{{ item.rel_path }}</span>
          <span class="item-status" :class="item.status.toLowerCase()">{{ item.status }}</span>
          <span class="item-detail">{{ item.detail }}</span>
        </div>
      </div>
    </div>

    <!-- Preview Modal -->
    <div v-if="showPreviewModal" class="modal-mask" @click.self="showPreviewModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3>👁️ 导出预览 (Export Preview)</h3>
          <button class="btn-close" @click="showPreviewModal = false">✕</button>
        </div>

        <div v-if="previewData" class="preview-content">
          <div class="preview-stats-row">
            <div class="stat-box create">
              <span class="num">{{ previewData.total_files_to_create }}</span>
              <span class="lbl">待新建文件</span>
            </div>
            <div class="stat-box update">
              <span class="num">{{ previewData.total_files_to_update }}</span>
              <span class="lbl">待更新文件 (保留笔记)</span>
            </div>
            <div class="stat-box conflicts">
              <span class="num">{{ previewData.total_conflicts }}</span>
              <span class="lbl">冲突</span>
            </div>
          </div>

          <div class="breakdown-title">📦 实体分类统计</div>
          <div class="breakdown-chips">
            <span v-for="(cnt, type) in previewData.entities_breakdown" :key="type" class="chip">
              <b>{{ type.toUpperCase() }}</b>: {{ cnt }}
            </span>
          </div>

          <div class="actions-list-title">📄 拟执行的文件变更明细</div>
          <div class="file-actions-table">
            <div v-for="act in previewData.file_actions" :key="act.rel_path" class="action-row">
              <span class="act-badge" :class="act.action">{{ act.action.toUpperCase() }}</span>
              <span class="act-path">{{ act.rel_path }}</span>
              <span v-if="act.has_user_notes" class="user-notes-badge">🛡️ 保留用户笔记</span>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-secondary" @click="showPreviewModal = false">取消</button>
          <button class="btn-primary" @click="confirmExportFromPreview">确认并立即导出</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  projectId: {
    type: String,
    required: true,
  },
})

const vaultPath = ref('data/obsidian_vault')
const isLoading = ref(false)
const exportResult = ref(null)
const previewData = ref(null)
const showPreviewModal = ref(false)
const reconcileResult = ref(null)

async function handlePreview() {
  if (!vaultPath.value.trim()) {
    alert('请先输入有效的 Obsidian Vault 目录路径')
    return
  }
  isLoading.value = true
  try {
    const res = await fetch(`/api/projects/${props.projectId}/vault/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vault_path: vaultPath.value.trim() }),
    })
    if (!res.ok) {
      const err = await res.json()
      alert(`预览失败: ${err.detail || '未知错误'}`)
      return
    }
    previewData.value = await res.json()
    showPreviewModal.value = true
  } catch (e) {
    alert(`预览请求异常: ${e}`)
  } finally {
    isLoading.value = false
  }
}

async function confirmExportFromPreview() {
  showPreviewModal.value = false
  await handleExport()
}

async function handleExport() {
  if (!vaultPath.value.trim()) {
    alert('请先输入有效的 Obsidian Vault 目录路径')
    return
  }
  isLoading.value = true
  try {
    const res = await fetch(`/api/projects/${props.projectId}/vault/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vault_path: vaultPath.value.trim() }),
    })
    if (!res.ok) {
      const err = await res.json()
      alert(`导出失败: ${err.detail || '未知错误'}`)
      return
    }
    exportResult.value = await res.json()
  } catch (e) {
    alert(`导出请求异常: ${e}`)
  } finally {
    isLoading.value = false
  }
}

async function handleReconcile() {
  if (!vaultPath.value.trim()) {
    alert('请先输入有效的 Obsidian Vault 目录路径')
    return
  }
  isLoading.value = true
  try {
    const res = await fetch(`/api/projects/${props.projectId}/vault/reconcile`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vault_path: vaultPath.value.trim() }),
    })
    if (!res.ok) {
      const err = await res.json()
      alert(`Reconcile 失败: ${err.detail || '未知错误'}`)
      return
    }
    reconcileResult.value = await res.json()
  } catch (e) {
    alert(`Reconcile 异常: ${e}`)
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.vault-bridge-container {
  padding: 20px;
  max-width: 1080px;
  margin: 0 auto;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}
.panel-title {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 6px 0;
}
.panel-subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}
.header-actions {
  display: flex;
  gap: 10px;
}
.btn-primary {
  padding: 8px 16px;
  background: #3b82f6;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
}
.btn-primary:hover { background: #2563eb; }
.btn-secondary {
  padding: 8px 16px;
  background: var(--bg-surface-2, #f1f5f9);
  color: var(--text-primary, #475569);
  border: 1px solid var(--border-default, #cbd5e1);
  border-radius: 6px;
  cursor: pointer;
}
.btn-secondary:hover { background: var(--bg-surface-3, #e2e8f0); }

.config-card {
  background: var(--bg-surface-1, #1e293b);
  border: 1px solid var(--border-default, #334155);
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.field-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.field-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #f8fafc);
}
.input-row {
  display: flex;
  gap: 10px;
}
.input-path {
  flex: 1;
  padding: 10px 14px;
  background: var(--bg-surface-2, #0f172a);
  color: var(--text-primary, #f8fafc);
  border: 1px solid var(--border-default, #334155);
  border-radius: 6px;
  font-family: var(--font-mono, monospace);
  font-size: 13px;
}
.btn-export {
  padding: 10px 20px;
  background: #10b981;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
}
.btn-export:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}
.field-tip {
  font-size: 12px;
  color: var(--text-secondary, #94a3b8);
  margin: 4px 0 0 0;
}
.field-tip code {
  background: var(--bg-surface-2, #0f172a);
  color: var(--accent-science, #38bdf8);
  padding: 2px 4px;
  border-radius: 4px;
  font-family: monospace;
}

.result-card {
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: 10px;
  padding: 18px;
  margin-bottom: 20px;
}
.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.result-title {
  font-size: 15px;
  font-weight: 600;
  color: #34d399;
}
.result-stats {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}
.stat-badge {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}
.stat-badge.new { background: #dcfce7; color: #15803d; }
.stat-badge.update { background: #e0f2fe; color: #0369a1; }
.stat-badge.skip { background: #f1f5f9; color: #64748b; }
.stat-badge.total { background: #fef3c7; color: #b45309; }
.result-tip {
  font-size: 12px;
  color: #34d399;
}

.reconcile-card {
  background: var(--bg-surface-1, #1e293b);
  border: 1px solid var(--border-default, #334155);
  border-radius: 10px;
  padding: 18px;
  margin-bottom: 20px;
}
.reconcile-header h3 {
  font-size: 14px;
  margin: 0 0 12px 0;
  color: var(--text-primary, #f8fafc);
}
.reconcile-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 260px;
  overflow-y: auto;
}
.reconcile-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  padding: 6px 8px;
  background: var(--bg-surface-2, #0f172a);
  border-radius: 6px;
}
.item-path {
  font-family: monospace;
  color: var(--text-primary, #f8fafc);
}
.item-status {
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 11px;
}
.item-status.unchanged { background: #dcfce7; color: #166534; }
.item-status.user_modified { background: #fef3c7; color: #92400e; }
.item-status.conflict { background: #fee2e2; color: #991b1b; }
.item-detail {
  color: var(--text-secondary, #94a3b8);
  font-size: 11px;
}

/* Modal */
.modal-mask {
  position: fixed; inset: 0; background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center; z-index: 2000;
}
.modal-card {
  width: 580px; max-width: 90vw; max-height: 85vh; background: var(--bg-surface-1, #1e293b);
  border: 1px solid var(--border-default, #334155);
  border-radius: 12px; padding: 20px; display: flex; flex-direction: column;
  color: var(--text-primary, #f8fafc);
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;
}
.modal-header h3 { margin: 0; font-size: 16px; color: var(--text-primary, #f8fafc); }
.btn-close { border: none; background: transparent; cursor: pointer; font-size: 16px; color: var(--text-secondary, #94a3b8); }
.preview-content {
  flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 14px;
}
.preview-stats-row {
  display: flex; gap: 12px;
}
.stat-box {
  flex: 1; padding: 12px; border-radius: 8px; display: flex; flex-direction: column; align-items: center;
}
.stat-box.create { background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); color: #34d399; }
.stat-box.update { background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3); color: #60a5fa; }
.stat-box.conflicts { background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); color: #f87171; }
.stat-box .num { font-size: 20px; font-weight: 700; }
.stat-box .lbl { font-size: 11px; margin-top: 2px; }

.breakdown-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip {
  padding: 4px 8px; background: var(--bg-surface-2, #0f172a); border-radius: 4px; font-size: 11px; color: var(--text-primary, #f8fafc);
}
.file-actions-table {
  max-height: 180px; overflow-y: auto; background: var(--bg-surface-2, #0f172a); border-radius: 6px; padding: 8px;
  display: flex; flex-direction: column; gap: 6px; border: 1px solid var(--border-default, #334155);
}
.action-row {
  display: flex; align-items: center; gap: 8px; font-size: 12px;
}
.act-badge {
  padding: 1px 5px; border-radius: 3px; font-size: 10px; font-weight: 700;
}
.act-badge.create { background: #dcfce7; color: #166534; }
.act-badge.update { background: #e0f2fe; color: #075985; }
.act-path { font-family: monospace; flex: 1; color: var(--text-primary, #f8fafc); }
.user-notes-badge { font-size: 11px; color: #38bdf8; }

.modal-footer {
  margin-top: 16px; display: flex; justify-content: flex-end; gap: 10px;
}
</style>
