<template>
  <div v-if="visible" class="quick-capture-backdrop" @click.self="$emit('close')">
    <div class="quick-capture-dialog">
      <!-- 头部 -->
      <div class="qc-header">
        <div class="qc-title-group">
          <i class="fa-solid fa-bolt" style="color: #eab308; font-size: 18px;"></i>
          <div>
            <h3 class="qc-title">⚡ 快速沉淀本次科研工作 (Quick Capture)</h3>
            <p class="qc-subtitle">无论在本地 4090、学校集群跑完，还是用 Codex/Claude 生成，30 秒记录下来，形成永久可追溯科研记忆</p>
          </div>
        </div>
        <button class="btn-close" @click="$emit('close')">✕</button>
      </div>

      <!-- 表单主体 -->
      <div class="qc-body">
        <div class="form-grid">
          <!-- 1. 会话标题 -->
          <div class="form-group full-width">
            <label class="form-label">📌 本次工作主题 / 简述 <span class="req">*</span></label>
            <input
              v-model="form.title"
              class="form-input"
              placeholder="例如：DGCNN 邻域参数 k=25 探索与过平滑解耦验证"
            />
          </div>

          <!-- 2. 我做了什么 -->
          <div class="form-group full-width">
            <label class="form-label">🧪 我做了什么？(What I Did) <span class="req">*</span></label>
            <textarea
              v-model="form.what_i_did"
              class="form-textarea"
              rows="2"
              placeholder="例如：使用 Codex 修改了聚合层的残差连接，在 4090 服务器上跑了 100 epoch..."
            ></textarea>
          </div>

          <!-- 3. 使用的外部工具 / 机器 -->
          <div class="form-group">
            <label class="form-label">🤖 使用的外部 AI 工具</label>
            <select v-model="form.ai_tool_used" class="form-select">
              <option value="None">无 AI (纯人工实验/代码)</option>
              <option value="Codex">OpenAI Codex</option>
              <option value="Claude Code">Claude Code</option>
              <option value="ChatGPT">ChatGPT / Web UI</option>
              <option value="DeepSeek">DeepSeek Coder</option>
              <option value="Gemini">Google Gemini</option>
              <option value="Other">其他工具</option>
            </select>
          </div>

          <!-- 4. Git Commit (可选) -->
          <div class="form-group">
            <label class="form-label">🔖 关联 Git Commit (可选)</label>
            <input
              v-model="form.git_commit"
              class="form-input font-mono"
              placeholder="例如：a82f31c 或 main branch"
            />
          </div>

          <!-- 5. 实验结果 -->
          <div class="form-group full-width">
            <label class="form-label">📈 实验结果如何？(What Happened) <span class="req">*</span></label>
            <textarea
              v-model="form.what_happened"
              class="form-textarea"
              rows="2"
              placeholder="例如：验证集准确率达到 91.8%，Loss 降到 0.18，但训练显存消耗略有上升..."
            ></textarea>
          </div>

          <!-- 6. 意外发现 / 反思 -->
          <div class="form-group full-width">
            <label class="form-label">💡 我发现了什么 / 意外现象？(Surprises & Insights)</label>
            <input
              v-model="form.what_surprised_me"
              class="form-input"
              placeholder="例如：残差连接有效缓解了梯度消失，证实 k=20 拐点主要是结构退化而非单纯参数失配"
            />
          </div>

          <!-- 7. 下一步 -->
          <div class="form-group full-width">
            <label class="form-label">🧭 下一步打算做什么？(Next Step)</label>
            <input
              v-model="form.next_step"
              class="form-input"
              placeholder="例如：在更大尺度点云数据集 (ShapeNet) 上复现该拐点"
            />
          </div>
        </div>
      </div>

      <!-- 底部操作栏 -->
      <div class="qc-footer">
        <span class="user-belief-hint">
          <i class="fa-solid fa-lock" style="font-size: 11px;"></i>
          标记为 <code>USER_BELIEF</code>，AI 绝无权限自动修改或伪造您的记录
        </span>
        <div class="action-btns">
          <button class="btn-cancel" @click="$emit('close')">取消</button>
          <button
            class="btn-save"
            :disabled="!form.title.trim() || !form.what_i_did.trim() || !form.what_happened.trim() || saving"
            @click="saveQuickCapture"
          >
            {{ saving ? '正在保存...' : '✓ 沉淀本次科研记录 (30s)' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  projectId: { type: String, required: true },
})

const emit = defineEmits(['close', 'saved'])

const saving = ref(false)

const form = reactive({
  title: '',
  what_i_did: '',
  ai_tool_used: 'Codex',
  git_commit: '',
  what_happened: '',
  what_surprised_me: '',
  next_step: '',
})

async function saveQuickCapture() {
  if (!form.title.trim() || !form.what_i_did.trim() || !form.what_happened.trim()) return
  saving.value = true
  try {
    const res = await fetch(`/api/projects/${props.projectId}/quick-capture`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: form.title.trim(),
        what_i_did: form.what_i_did.trim(),
        what_happened: form.what_happened.trim(),
        what_surprised_me: form.what_surprised_me.trim(),
        next_step: form.next_step.trim(),
        ai_tool_used: form.ai_tool_used,
        git_commit: form.git_commit.trim() || undefined,
      }),
    })
    if (res.ok) {
      form.title = ''
      form.what_i_did = ''
      form.what_happened = ''
      form.what_surprised_me = ''
      form.next_step = ''
      form.git_commit = ''
      emit('saved')
      emit('close')
    } else {
      alert('保存失败，请检查输入')
    }
  } catch (e) {
    alert('请求失败: ' + e)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.quick-capture-backdrop {
  position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 2000;
  display: flex; align-items: center; justify-content: center; padding: 20px;
}
.quick-capture-dialog {
  background: var(--bg-surface-1, #fff); border-radius: 12px; width: 100%; max-width: 720px;
  max-height: 90vh; display: flex; flex-direction: column; box-shadow: 0 16px 40px rgba(0,0,0,0.3);
  overflow: hidden; border: 1px solid var(--border-default, #e2e8f0);
}
.qc-header {
  padding: 16px 20px; border-bottom: 1px solid var(--border-default, #e2e8f0);
  display: flex; justify-content: space-between; align-items: center; background: var(--bg-surface-2, #f8fafc);
}
.qc-title-group { display: flex; align-items: center; gap: 10px; }
.qc-title { font-size: 16px; margin: 0; font-weight: 700; color: var(--text-primary, #0f172a); }
.qc-subtitle { font-size: 12px; color: var(--text-secondary, #64748b); margin: 2px 0 0 0; }
.btn-close { background: none; border: none; font-size: 16px; cursor: pointer; color: var(--text-muted, #94a3b8); }

.qc-body { padding: 18px 20px; overflow-y: auto; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.full-width { grid-column: span 2; }
.form-label { display: block; font-size: 12px; font-weight: 600; color: var(--text-primary, #334155); margin-bottom: 5px; }
.req { color: #ef4444; }
.form-input { width: 100%; box-sizing: border-box; border: 1px solid var(--border-default, #cbd5e1); border-radius: 6px; padding: 8px 10px; font-size: 13px; background: var(--bg-surface-2, #f8fafc); }
.form-select { width: 100%; box-sizing: border-box; border: 1px solid var(--border-default, #cbd5e1); border-radius: 6px; padding: 8px 10px; font-size: 13px; background: var(--bg-surface-2, #f8fafc); }
.form-textarea { width: 100%; box-sizing: border-box; border: 1px solid var(--border-default, #cbd5e1); border-radius: 6px; padding: 8px 10px; font-size: 13px; background: var(--bg-surface-2, #f8fafc); resize: vertical; }

.qc-footer {
  padding: 12px 20px; border-top: 1px solid var(--border-default, #e2e8f0);
  display: flex; justify-content: space-between; align-items: center; background: var(--bg-surface-2, #f8fafc);
}
.user-belief-hint { font-size: 11px; color: var(--text-secondary, #64748b); }
.user-belief-hint code { background: #fef3c7; color: #b45309; padding: 1px 4px; border-radius: 3px; font-weight: 700; }
.action-btns { display: flex; gap: 8px; }
.btn-cancel { background: transparent; border: 1px solid var(--border-default, #cbd5e1); border-radius: 6px; padding: 6px 14px; font-size: 12px; cursor: pointer; }
.btn-save { background: #3b82f6; color: #fff; border: none; border-radius: 6px; padding: 6px 18px; font-size: 12px; font-weight: 600; cursor: pointer; }
.btn-save:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
