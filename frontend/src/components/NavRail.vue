<template>
  <nav class="nav-rail">
    <!-- 品牌 -->
    <div class="rail-logo" :class="{ active: active === 'chat' }" @click="$emit('navigate', 'chat')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="18" height="18">
        <path d="M12 2 2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
      </svg>
    </div>

    <!-- 主导航 -->
    <div class="rail-items">
      <button
        v-for="item in items"
        :key="item.key"
        class="rail-item"
        :class="{ active: active === item.key }"
        @click="$emit('navigate', item.key)"
        @mouseenter="hover = item.key"
        @mouseleave="hover = ''"
      >
        <span class="rail-ico" v-html="item.svg"></span>
        <span class="rail-tip" v-if="hover === item.key">
          <span class="tip-title">{{ item.label }}</span>
          <span class="tip-desc">{{ item.desc }}</span>
        </span>
      </button>
    </div>

    <!-- 底部 -->
    <div class="rail-bottom">
      <button
        class="rail-item"
        :class="{ active: active === 'settings' }"
        @click="$emit('navigate', 'settings')"
        @mouseenter="hover = 'settings'"
        @mouseleave="hover = ''"
      >
        <span class="rail-ico" v-html="settingsSvg"></span>
        <span class="rail-tip" v-if="hover === 'settings'">
          <span class="tip-title">模型设置</span>
          <span class="tip-desc">绑定你的 API Key（BYOK）</span>
        </span>
      </button>
    </div>
  </nav>
</template>

<script setup>
import { ref } from 'vue'

defineProps({ active: { type: String, default: 'chat' } })
defineEmits(['navigate'])

const hover = ref('')

const I = {
  chat: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="20" height="20"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
  records: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="20" height="20"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"/><path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/></svg>',
  graph: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="20" height="20"><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><line x1="15.5" y1="7.5" x2="8" y2="15"/><line x1="9" y1="6" x2="15" y2="6"/></svg>',
  features: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="20" height="20"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>',
  report: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="20" height="20"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="13" y2="17"/></svg>',
}
const settingsSvg = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="20" height="20"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>'

const items = [
  { key: 'chat',     label: '对话',     desc: '一句话向研究助手提问或唤起功能', svg: I.chat },
  { key: 'records',  label: '实验记录', desc: '查看与管理你的实验、训练日志',   svg: I.records },
  { key: 'graph',    label: '关系图谱', desc: '参数与指标之间的关联可视化',     svg: I.graph },
  { key: 'features', label: '功能库',   desc: '预置科研工具：报告/原型/对比…',  svg: I.features },
  { key: 'report',   label: '报告工坊', desc: '一键汇总对话与指标生成报告',     svg: I.report },
  { key: 'projects', label: 'Projects', desc: 'Research Project 管理与科研闭环', svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="20" height="20"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>' },
]
</script>

<style scoped>
.nav-rail {
  width: 52px;
  flex-shrink: 0;
  height: 100vh;
  background: var(--rail-bg);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 0;
  gap: 6px;
  position: relative;
  z-index: 30;
}

.rail-logo {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, #2F6BFF, #1F5AF0);
  cursor: pointer;
  margin-bottom: 10px;
  transition: transform 0.15s;
}
.rail-logo:hover { transform: scale(1.05); }
.rail-logo.active { box-shadow: 0 0 0 2px rgba(47,107,255,0.4); }

.rail-items {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
  align-items: center;
}

.rail-item {
  position: relative;
  width: 40px;
  height: 40px;
  border: none;
  background: transparent;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--rail-fg);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.rail-item:hover { background: var(--rail-bg-hover); color: var(--rail-fg-active); }
.rail-item.active { color: var(--rail-fg-active); background: var(--rail-bg-hover); }
.rail-item.active::before {
  content: '';
  position: absolute;
  left: -12px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  border-radius: 0 3px 3px 0;
  background: var(--rail-active-bar);
}

.rail-ico { display: flex; }

.rail-bottom {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  padding-top: 6px;
  border-top: 1px solid rgba(255,255,255,0.08);
}

/* tooltip */
.rail-tip {
  position: absolute;
  left: calc(100% + 12px);
  top: 50%;
  transform: translateY(-50%);
  background: #1A1A1E;
  color: #fff;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  padding: 7px 10px;
  width: 180px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  pointer-events: none;
  box-shadow: 0 8px 24px rgba(0,0,0,0.35);
  z-index: 50;
}
.rail-tip::before {
  content: '';
  position: absolute;
  left: -5px;
  top: 50%;
  transform: translateY(-50%) rotate(45deg);
  width: 9px; height: 9px;
  background: #1A1A1E;
  border-left: 1px solid rgba(255,255,255,0.1);
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.tip-title { font-size: 12px; font-weight: 600; }
.tip-desc { font-size: 11px; color: #A1A1AA; line-height: 1.4; }
</style>
