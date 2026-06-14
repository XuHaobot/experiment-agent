<template>
  <div class="chat-view">
    <!-- Sidebar: session list -->
    <aside class="chat-sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <span v-if="!sidebarCollapsed" class="sidebar-title">会话列表</span>
        <button class="btn-icon" @click="sidebarCollapsed = !sidebarCollapsed" :title="sidebarCollapsed ? '展开侧栏' : '收起侧栏'">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
            <template v-if="sidebarCollapsed">
              <polyline points="9 18 15 12 9 6"/>
            </template>
            <template v-else>
              <polyline points="15 18 9 12 15 6"/>
            </template>
          </svg>
        </button>
      </div>
      <template v-if="!sidebarCollapsed">
        <button class="btn-new-chat" @click="startNewChat">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          新建对话
        </button>
        <div class="session-list">
          <div
            v-for="s in sessions"
            :key="s.session_id"
            class="session-item"
            :class="{ active: s.session_id === currentSessionId }"
            @click="switchSession(s.session_id)"
          >
            <div class="session-info">
              <span class="session-title">{{ s.title || '新对话' }}</span>
              <span class="session-meta">{{ s.turn_count || 0 }} 轮 · {{ formatTime(s.created_at) }}</span>
            </div>
            <button class="btn-icon btn-delete" @click.stop="deleteSession(s.session_id)" title="删除会话">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="12" height="12">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
          <div v-if="sessions.length === 0" class="session-empty">暂无历史会话</div>
        </div>
      </template>
    </aside>

    <!-- Main chat area -->
    <div class="chat-main">
      <div class="chat-messages" ref="chatMsgs">
        <!-- Empty state -->
        <div v-if="messages.length === 0" class="chat-welcome">
          <div class="welcome-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" width="40" height="40">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
            </svg>
          </div>
          <h2 class="welcome-title">AI 实验研究助手</h2>
          <p class="welcome-desc">基于你的实验记录进行智能问答、数据分析和报告生成</p>
          <div class="suggestions">
            <button v-for="q in suggestions" :key="q" class="suggestion-btn" @click="send(q)">{{ q }}</button>
          </div>
        </div>

        <!-- Messages -->
        <template v-for="(msg, i) in messages" :key="i">
          <div class="chat-msg" :class="msg.role">
            <div class="msg-avatar">
              <template v-if="msg.role === 'user'">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
                  <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/>
                </svg>
              </template>
              <template v-else>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
                  <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
                </svg>
              </template>
            </div>
            <div class="msg-body">
              <div class="msg-role">{{ msg.role === 'user' ? '你' : '研究助手' }}</div>
              <div class="msg-content markdown-body" v-if="msg.role === 'assistant'" v-html="renderMarkdown(msg.content)"></div>
              <div class="msg-content user-content" v-else>{{ msg.content }}</div>
              <!-- Agent trace for assistant messages -->
              <AgentTrace
                v-if="msg.trace && msg.trace.length"
                :trace="msg.trace"
                :total-iterations="msg.iterations || 0"
              />
            </div>
          </div>
        </template>

        <!-- Streaming state -->
        <div v-if="streaming" class="chat-msg assistant">
          <div class="msg-avatar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <div class="msg-body">
            <div class="msg-role">研究助手</div>
            <div class="msg-content streaming-content">
              <div v-if="streamAnswer" class="markdown-body" v-html="renderMarkdown(streamAnswer) || streamAnswer"></div>
              <span v-else class="typing-dots"><span></span><span></span><span></span></span>
              <!-- Live trace during streaming -->
              <AgentTrace
                v-if="streamTrace.length"
                :trace="streamTrace"
                :total-iterations="streamTrace.length"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Input area -->
      <div class="chat-input-bar">
        <div class="input-wrapper">
          <textarea
            v-model="inputText"
            class="chat-textarea"
            placeholder="输入问题，探索你的实验数据..."
            rows="1"
            @keydown.enter.exact.prevent="send(inputText)"
            @input="autoResize"
            ref="textareaRef"
          ></textarea>
          <button
            class="btn-send"
            @click="send(inputText)"
            :disabled="!inputText.trim() || streaming"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
        </div>
        <div class="input-hint">Enter 发送 · Shift+Enter 换行</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, onUnmounted } from 'vue'
import { marked } from 'marked'
import { api } from '../api/client.js'
import AgentTrace from '../components/AgentTrace.vue'

// --- State ---
const messages = ref([])          // {role, content, trace?, iterations?}
const inputText = ref('')
const streaming = ref(false)
const streamAnswer = ref('')
const streamTrace = ref([])
const currentSessionId = ref(null)
const sessions = ref([])
const sidebarCollapsed = ref(false)
const chatMsgs = ref(null)
const textareaRef = ref(null)
let abortController = null  // AbortController for SSE stream cancellation

const suggestions = [
  '有哪些实验报过错？',
  '对比最近几次实验的参数差异',
  '总结一下所有训练实验的结果',
  '有没有 cuda out of memory 的记录？',
]

// --- Markdown ---
marked.setOptions({ breaks: true, gfm: true })

function renderMarkdown(text) {
  if (!text) return ''
  try { return marked.parse(text) } catch { return text }
}

// --- Auto-resize textarea ---
function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'
}

// --- Scroll to bottom ---
async function scrollToBottom() {
  await nextTick()
  if (chatMsgs.value) chatMsgs.value.scrollTop = chatMsgs.value.scrollHeight
}

// --- Session management ---
async function loadSessions() {
  try {
    const res = await api.getSessions()
    sessions.value = (res.sessions || []).map(s => ({
      ...s,
      title: s.title || (s.turn_count > 0 ? `对话 ${s.session_id.slice(0, 6)}` : '新对话'),
    }))
  } catch (e) {
    console.error('Failed to load sessions:', e)
  }
}

function startNewChat() {
  cancelStream()
  currentSessionId.value = null
  messages.value = []
  streamAnswer.value = ''
  streamTrace.value = []
  resetTextarea()
}

function cancelStream() {
  if (abortController) {
    abortController.abort()
    abortController = null
  }
  streaming.value = false
}

function resetTextarea() {
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
  }
}

async function switchSession(sid) {
  cancelStream()
  currentSessionId.value = sid
  messages.value = []
  streamAnswer.value = ''
  streamTrace.value = []
  resetTextarea()
  try {
    const res = await api.getSessionHistory(sid)
    const history = res.history || []
    for (const turn of history) {
      messages.value.push({
        role: turn.role,
        content: turn.content,
        trace: turn.metadata?.trace || [],
        iterations: turn.metadata?.iterations || 0,
      })
    }
    await scrollToBottom()
  } catch (e) {
    console.error('Failed to load session history:', e)
  }
}

async function deleteSession(sid) {
  try {
    await api.deleteSession(sid)
    sessions.value = sessions.value.filter(s => s.session_id !== sid)
    if (currentSessionId.value === sid) {
      startNewChat()
    }
  } catch (e) {
    console.error('Failed to delete session:', e)
  }
}

// --- Send message (SSE streaming) ---
async function send(question) {
  const q = (question || '').trim()
  if (!q || streaming.value) return

  messages.value.push({ role: 'user', content: q })
  inputText.value = ''
  streaming.value = true
  streamAnswer.value = ''
  streamTrace.value = []
  await scrollToBottom()

  // Reset textarea height
  resetTextarea()

  // Create AbortController for this stream
  abortController = new AbortController()

  try {
    const reader = await api.chatStream(q, currentSessionId.value, abortController.signal)
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''  // keep incomplete line in buffer

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed || !trimmed.startsWith('data: ')) continue
        const payload = trimmed.slice(6)

        if (payload === '[DONE]') continue

        try {
          const event = JSON.parse(payload)
          if (event.type === 'session_id') {
            currentSessionId.value = event.session_id
          } else if (event.type === 'trace') {
            streamTrace.value = [...streamTrace.value, event.step]
            await scrollToBottom()
          } else if (event.type === 'answer') {
            streamAnswer.value = event.answer
            await scrollToBottom()
          }
        } catch {
          // ignore malformed JSON
        }
      }
    }

    // Finalize: move streaming content into messages
    messages.value.push({
      role: 'assistant',
      content: streamAnswer.value || '未获取到回答',
      trace: streamTrace.value,
      iterations: streamTrace.value.length,
    })
    streamAnswer.value = ''
    streamTrace.value = []

  } catch (e) {
    // AbortError is expected when user cancels / navigates away
    if (e.name === 'AbortError') {
      // If we got partial content, still save it
      if (streamAnswer.value) {
        messages.value.push({
          role: 'assistant',
          content: streamAnswer.value,
          trace: streamTrace.value,
          iterations: streamTrace.value.length,
        })
      }
      streamAnswer.value = ''
      streamTrace.value = []
    } else {
      console.error('Stream error:', e)
      messages.value.push({
        role: 'assistant',
        content: `请求出错: ${e.message}`,
      })
    }
  } finally {
    abortController = null
    streaming.value = false
    await scrollToBottom()
    loadSessions()  // refresh sidebar
  }
}

// --- Utils ---
function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  if (isNaN(d.getTime())) return ''
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

// --- Lifecycle ---
onMounted(() => {
  loadSessions()
})

onUnmounted(() => {
  cancelStream()
})
</script>

<style scoped>
.chat-view {
  display: flex; height: 100%; overflow: hidden;
  background: var(--bg-primary);
}

/* ==================== Sidebar ==================== */
.chat-sidebar {
  width: 240px; flex-shrink: 0; display: flex; flex-direction: column;
  border-right: 1px solid var(--border-secondary);
  background: var(--bg-secondary);
  transition: width 0.2s ease;
}
.chat-sidebar.collapsed { width: 40px; }

.sidebar-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 12px; border-bottom: 1px solid var(--border-secondary);
  flex-shrink: 0;
}
.sidebar-title {
  font-family: var(--font-mono); font-size: 12px; font-weight: 600;
  color: var(--text-secondary);
}

.btn-icon {
  width: 24px; height: 24px; border: none; border-radius: var(--radius-sm);
  background: transparent; display: flex; align-items: center; justify-content: center;
  color: var(--text-tertiary); cursor: pointer; flex-shrink: 0;
}
.btn-icon:hover { background: var(--bg-tertiary); color: var(--text-primary); }

.btn-new-chat {
  display: flex; align-items: center; gap: 6px; width: calc(100% - 16px);
  margin: 8px; padding: 8px 10px; border: 1px dashed var(--border-primary);
  border-radius: var(--radius-sm); background: transparent;
  font-size: 13px; color: var(--text-secondary); cursor: pointer;
}
.btn-new-chat:hover { background: var(--bg-tertiary); color: var(--text-primary); border-style: solid; }

.session-list {
  flex: 1; overflow-y: auto; padding: 4px 8px; display: flex; flex-direction: column; gap: 2px;
}
.session-item {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 8px; border-radius: var(--radius-sm); cursor: pointer;
}
.session-item:hover { background: var(--bg-tertiary); }
.session-item.active { background: var(--bg-tertiary); }
.session-item.active .session-title { color: var(--text-primary); font-weight: 500; }

.session-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.session-title {
  font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  color: var(--text-secondary);
}
.session-meta { font-size: 11px; color: var(--text-tertiary); }

.btn-delete { opacity: 0; }
.session-item:hover .btn-delete { opacity: 1; }
.btn-delete:hover { color: #e55; }

.session-empty {
  padding: 20px; text-align: center; color: var(--text-tertiary); font-size: 12px;
}

/* ==================== Main chat ==================== */
.chat-main {
  flex: 1; display: flex; flex-direction: column; min-width: 0; overflow: hidden;
}

.chat-messages {
  flex: 1; overflow-y: auto; padding: 16px 20px; display: flex; flex-direction: column; gap: 16px;
}

/* Welcome / empty */
.chat-welcome {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 100%; gap: 10px; padding: 20px;
}
.welcome-icon { color: var(--text-tertiary); opacity: 0.5; margin-bottom: 4px; }
.welcome-title {
  font-family: var(--font-mono); font-size: 18px; font-weight: 600;
  color: var(--text-primary); margin: 0;
}
.welcome-desc { font-size: 13px; color: var(--text-tertiary); margin: 0 0 12px; }

.suggestions { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; max-width: 600px; }
.suggestion-btn {
  padding: 8px 14px; border: 1px solid var(--border-secondary); border-radius: var(--radius-md);
  background: var(--bg-secondary); font-size: 13px; color: var(--text-secondary);
  cursor: pointer; text-align: left; line-height: 1.4;
}
.suggestion-btn:hover { border-color: var(--border-primary); background: var(--bg-tertiary); color: var(--text-primary); }

/* Messages */
.chat-msg {
  display: flex; gap: 12px; max-width: 820px; width: 100%;
  margin: 0 auto;
}
.chat-msg.user { flex-direction: row-reverse; }

.msg-avatar {
  width: 30px; height: 30px; border-radius: var(--radius-sm);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.chat-msg.user .msg-avatar { background: var(--accent); color: var(--bg-primary); }
.chat-msg.assistant .msg-avatar { background: var(--bg-tertiary); color: var(--text-secondary); border: 1px solid var(--border-secondary); }

.msg-body { flex: 1; min-width: 0; }
.msg-role { font-size: 11px; color: var(--text-tertiary); margin-bottom: 3px; font-weight: 500; }

.msg-content {
  padding: 10px 14px; border-radius: var(--radius-md); font-size: 13px; line-height: 1.7;
  word-break: break-word;
}
.chat-msg.user .msg-content,
.chat-msg.user .user-content {
  background: var(--accent); color: var(--bg-primary);
  border-radius: var(--radius-md) var(--radius-md) 4px var(--radius-md);
}
.chat-msg.assistant .msg-content {
  background: var(--bg-secondary); color: var(--text-primary);
  border: 1px solid var(--border-secondary);
  border-radius: var(--radius-md) var(--radius-md) var(--radius-md) 4px;
}

/* Markdown styles */
.markdown-body :deep(h1) { font-size: 17px; margin: 12px 0 8px; font-weight: 600; border-bottom: 1px solid var(--border-secondary); padding-bottom: 4px; }
.markdown-body :deep(h2) { font-size: 15px; margin: 10px 0 6px; font-weight: 600; }
.markdown-body :deep(h3) { font-size: 14px; margin: 8px 0 4px; font-weight: 600; color: var(--text-secondary); }
.markdown-body :deep(p) { margin: 4px 0; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { padding-left: 20px; margin: 4px 0; }
.markdown-body :deep(li) { margin: 2px 0; }
.markdown-body :deep(code) {
  font-family: var(--font-mono); font-size: 12px; background: var(--bg-tertiary);
  padding: 2px 5px; border-radius: 3px;
}
.markdown-body :deep(pre) {
  background: var(--bg-tertiary); padding: 10px 12px; border-radius: var(--radius-sm);
  overflow-x: auto; margin: 6px 0; font-size: 12px; line-height: 1.5;
}
.markdown-body :deep(pre code) { background: none; padding: 0; }
.markdown-body :deep(blockquote) {
  border-left: 3px solid var(--border-primary); padding-left: 12px;
  color: var(--text-secondary); margin: 6px 0; font-size: 13px;
}
.markdown-body :deep(table) { border-collapse: collapse; margin: 6px 0; font-size: 12px; width: 100%; }
.markdown-body :deep(th), .markdown-body :deep(td) {
  border: 1px solid var(--border-secondary); padding: 5px 8px; text-align: left;
}
.markdown-body :deep(th) { background: var(--bg-tertiary); font-weight: 600; }
.markdown-body :deep(strong) { font-weight: 600; }
.markdown-body :deep(a) { color: var(--text-primary); text-decoration: underline; text-underline-offset: 2px; }

/* Streaming state */
.streaming-content { min-height: 32px; }
.typing-dots {
  display: inline-flex; gap: 4px; padding: 4px 0;
}
.typing-dots span {
  width: 6px; height: 6px; border-radius: 50%; background: var(--text-tertiary);
  animation: typing-bounce 1.2s infinite;
}
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing-bounce {
  0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
  30% { opacity: 1; transform: translateY(-4px); }
}

/* ==================== Input bar ==================== */
.chat-input-bar {
  flex-shrink: 0; padding: 12px 20px 14px;
  border-top: 1px solid var(--border-secondary);
}
.input-wrapper {
  display: flex; align-items: flex-end; gap: 8px; max-width: 820px; margin: 0 auto;
}
.chat-textarea {
  flex: 1; padding: 10px 14px; border: 1px solid var(--border-primary);
  border-radius: var(--radius-md); font-size: 13px; font-family: var(--font-sans);
  resize: none; background: var(--bg-primary); color: var(--text-primary);
  line-height: 1.5; min-height: 40px; max-height: 160px;
}
.chat-textarea:focus { outline: none; border-color: var(--accent); }
.chat-textarea::placeholder { color: var(--text-tertiary); }

.btn-send {
  width: 36px; height: 36px; border: 1px solid var(--border-primary);
  border-radius: var(--radius-md); background: var(--accent); color: var(--bg-primary);
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.btn-send:hover:not(:disabled) { opacity: 0.85; }
.btn-send:disabled { opacity: 0.35; cursor: not-allowed; background: var(--bg-tertiary); color: var(--text-tertiary); border-color: var(--border-secondary); }

.input-hint {
  max-width: 820px; margin: 4px auto 0; font-size: 11px; color: var(--text-tertiary);
  text-align: right;
}
</style>
