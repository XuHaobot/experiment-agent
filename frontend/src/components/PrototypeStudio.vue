<template>
  <div class="proto-studio">
    <div class="ps-header">
      <div>
        <h2 class="ps-title">画原型图</h2>
        <p class="ps-sub">用文字描述页面，自动生成可交互线框</p>
      </div>
      <div class="ps-device">
        <button :class="{ on: device === 'phone' }" @click="device = 'phone'">手机</button>
        <button :class="{ on: device === 'desktop' }" @click="device = 'desktop'">桌面</button>
      </div>
    </div>

    <div class="ps-input">
      <textarea v-model="desc" placeholder="例如：一个实验记录管理页，顶部导航，中间是搜索框，下面是记录卡片列表，每张卡片有标题、标签和操作按钮，底部有新建按钮"></textarea>
      <div class="ps-input-bar">
        <span class="ps-hint">{{ generating ? '生成中…' : '描述越具体，线框越还原' }}</span>
        <button class="ps-gen" :disabled="generating || !desc.trim()" @click="generate">生成线框</button>
      </div>
    </div>

    <div class="ps-canvas" :class="device">
      <div class="ps-frame">
        <div class="ps-screen">
          <template v-if="blocks.length">
            <div v-for="(b, i) in blocks" :key="i" class="wf-block" :class="'wf-' + b.type">
              <span class="wf-label" v-if="b.title">{{ b.title }}</span>
              <!-- 各类型微观呈现 -->
              <div v-if="b.type === 'list'" class="wf-list">
                <span v-for="n in (b.rows || 3)" :key="n" class="wf-line"></span>
              </div>
              <div v-else-if="b.type === 'chart'" class="wf-chart">
                <span v-for="n in 5" :key="n" class="wf-bar" :style="{ height: (20 + (n * 13) % 60) + '%' }"></span>
              </div>
              <div v-else-if="b.type === 'image'" class="wf-image">🖼</div>
              <div v-else-if="b.type === 'form'" class="wf-form">
                <span class="wf-input-line"></span>
                <span class="wf-input-line short"></span>
              </div>
              <div v-else-if="b.type === 'button'" class="wf-btn">{{ b.title || '按钮' }}</div>
              <div v-else-if="b.type === 'search'" class="wf-search">🔍 {{ b.title || '搜索' }}</div>
              <div v-else class="wf-text">{{ b.title || '文本内容' }}</div>
            </div>
          </template>
          <div v-else class="ps-empty">
            <div class="ps-empty-ico">📐</div>
            <p>在上方描述页面，点击「生成线框」</p>
          </div>
        </div>
        <div class="ps-home" v-if="device === 'phone'"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { api } from '../api/client'

const device = ref('phone')
const desc = ref('')
const blocks = ref([])
const generating = ref(false)

function inferType(text) {
  const t = text.toLowerCase()
  if (/导航|nav|菜单|menu|tab/.test(t)) return 'nav'
  if (/头部|header|标题栏|顶栏/.test(t)) return 'header'
  if (/搜索|search|筛选/.test(t)) return 'search'
  if (/列表|list|feed|记录/.test(t)) return 'list'
  if (/图表|chart|数据|趋势|曲线/.test(t)) return 'chart'
  if (/表单|form|输入|登录|注册/.test(t)) return 'form'
  if (/按钮|button|操作|提交/.test(t)) return 'button'
  if (/图片|图|banner|封面|照片/.test(t)) return 'image'
  if (/卡片|card/.test(t)) return 'card'
  if (/底部|footer|底栏/.test(t)) return 'footer'
  return 'text'
}

function heuristic(text) {
  const lines = text.split(/[。\n；;]/).map(s => s.trim()).filter(Boolean)
  return lines.map(line => ({
    type: inferType(line),
    title: line.length > 14 ? line.slice(0, 14) + '…' : line,
    rows: 3,
  }))
}

async function generate() {
  if (!desc.value.trim()) return
  generating.value = true
  // 先给出启发式结果，保证可见可用
  blocks.value = heuristic(desc.value)
  generating.value = false

  // 尝试 LLM 增强（best-effort，失败不影响）
  try {
    const prompt = `你是 UI 线框生成器。根据描述输出 JSON 数组，每个元素含 type(可选: nav/header/search/list/chart/form/button/image/card/footer/text) 和 title(短标题)。只输出 JSON，不要解释。\n描述：${desc.value}`
    const res = await api.chatStream(prompt, null)
    if (res && res.body) {
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      let acc = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const parts = buf.split('\n')
        buf = parts.pop()
        for (const p of parts) {
          const m = p.match(/data:\s*(.*)/)
          if (!m) continue
          try {
            const evt = JSON.parse(m[1])
            if (evt.type === 'answer' && evt.data) acc += evt.data
          } catch { /* ignore */ }
        }
      }
      const start = acc.indexOf('[')
      const end = acc.lastIndexOf(']')
      if (start !== -1 && end !== -1) {
        const arr = JSON.parse(acc.slice(start, end + 1))
        if (Array.isArray(arr) && arr.length) {
          blocks.value = arr.map(b => ({
            type: b.type || inferType(b.title || ''),
            title: b.title || '',
            rows: 3,
          }))
        }
      }
    }
  } catch {
    /* 保留启发式结果 */
  }
}
</script>

<style scoped>
.proto-studio { display: flex; flex-direction: column; height: 100%; background: var(--panel-bg); }
.ps-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 16px 8px; }
.ps-title { font-size: 15px; font-weight: 600; color: var(--text-primary); }
.ps-sub { font-size: 11px; color: var(--text-tertiary); margin-top: 2px; }
.ps-device { display: flex; background: var(--bg-tertiary); border-radius: 8px; padding: 2px; }
.ps-device button { border: none; background: transparent; font-size: 11.5px; padding: 4px 10px; border-radius: 6px; cursor: pointer; color: var(--text-secondary); }
.ps-device button.on { background: var(--card-bg); color: var(--accent); box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.ps-input { padding: 0 16px 10px; }
.ps-input textarea { width: 100%; height: 64px; resize: none; border: 1px solid var(--border-primary); border-radius: 9px; padding: 9px 11px; font-size: 12.5px; font-family: inherit; outline: none; color: var(--text-primary); background: var(--card-bg); }
.ps-input textarea:focus { border-color: var(--accent); }
.ps-input-bar { display: flex; align-items: center; justify-content: space-between; margin-top: 7px; }
.ps-hint { font-size: 10.5px; color: var(--text-tertiary); }
.ps-gen { background: var(--accent); color: #fff; border: none; border-radius: 8px; padding: 6px 14px; font-size: 12px; cursor: pointer; }
.ps-gen:disabled { opacity: .5; cursor: not-allowed; }
.ps-canvas { flex: 1; overflow: auto; padding: 14px; display: flex; justify-content: center; background: var(--bg-tertiary); }
.ps-frame { background: #fff; border: 1px solid var(--border-primary); display: flex; flex-direction: column; }
.ps-frame .ps-screen { flex: 1; overflow: auto; }
.ps-canvas.phone .ps-frame { width: 300px; min-height: 560px; border-radius: 22px; padding: 10px; box-shadow: 0 10px 30px rgba(0,0,0,.12); }
.ps-canvas.phone .ps-home { height: 4px; width: 60px; background: #d4d4d8; border-radius: 3px; margin: 8px auto 4px; }
.ps-canvas.desktop .ps-frame { width: 100%; max-width: 460px; min-height: 460px; border-radius: 10px; padding: 12px; box-shadow: 0 10px 30px rgba(0,0,0,.10); }
.wf-block { background: #f1f2f4; border: 1px dashed #c7c7cc; border-radius: 7px; padding: 8px; margin-bottom: 8px; min-height: 28px; position: relative; }
.wf-label { font-size: 10.5px; color: #6b6b73; display: block; margin-bottom: 4px; }
.wf-nav, .wf-header { background: #e7ecf7; border-color: #c5d2ee; }
.wf-footer { background: #eef0f2; }
.wf-list .wf-line { display: block; height: 7px; background: #d4d4d8; border-radius: 4px; margin: 4px 0; }
.wf-chart { display: flex; align-items: flex-end; gap: 6px; height: 56px; padding-top: 6px; }
.wf-bar { flex: 1; background: var(--accent); border-radius: 3px 3px 0 0; opacity: .8; }
.wf-image { height: 60px; display: flex; align-items: center; justify-content: center; background: #e8e8ec; border-radius: 6px; font-size: 22px; }
.wf-form .wf-input-line { display: block; height: 16px; background: #fff; border: 1px solid #d4d4d8; border-radius: 5px; margin: 4px 0; }
.wf-form .wf-input-line.short { width: 60%; }
.wf-btn { display: inline-block; background: var(--accent); color: #fff; font-size: 11px; padding: 5px 14px; border-radius: 7px; }
.wf-search { background: #fff; border: 1px solid #d4d4d8; border-radius: 16px; padding: 6px 12px; font-size: 11px; color: #9a9aa0; }
.wf-text { font-size: 11px; color: #8a8a90; line-height: 1.5; }
.ps-empty { text-align: center; color: var(--text-tertiary); padding: 50px 20px; }
.ps-empty-ico { font-size: 30px; margin-bottom: 8px; }
</style>
