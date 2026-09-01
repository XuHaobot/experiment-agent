<template>
  <router-view />
</template>

<script setup>
</script>

<style>
/* ============================================================
   ResearchOS V2 — Global Base & Scrollbar Styling
   ============================================================ */
:root {
  --bg-canvas: #0B0D10;
  --bg-surface-1: #11141A;
  --bg-surface-2: #161B22;
  --bg-hover: #1C222D;

  --border-default: #212631;
  --border-active: #384152;

  --text-primary: #F0F3F8;
  --text-secondary: #8B949E;
  --text-muted: #525A66;

  --accent-science: #388BFD;
  --accent-science-dim: rgba(56, 139, 253, 0.12);
  --accent-success: #3FB950;
  --accent-success-dim: rgba(63, 185, 80, 0.12);
  --accent-warning: #D29922;
  --accent-warning-dim: rgba(210, 153, 34, 0.12);
  --accent-danger: #F85149;
  --accent-danger-dim: rgba(248, 81, 73, 0.12);

  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}

[data-theme="light"] {
  --bg-canvas: #F7F8FA;
  --bg-surface-1: #FFFFFF;
  --bg-surface-2: #F3F4F6;
  --bg-hover: #EAECF0;

  --border-default: #E4E7EC;
  --border-active: #C8CDD5;

  --text-primary: #101828;
  --text-secondary: #667085;
  --text-muted: #98A2B3;

  --accent-science: #2563EB;
  --accent-science-dim: rgba(37, 99, 235, 0.08);
  --accent-success: #16A34A;
  --accent-success-dim: rgba(22, 163, 74, 0.08);
  --accent-warning: #B7791F;
  --accent-warning-dim: rgba(183, 121, 31, 0.08);
  --accent-danger: #DC2626;
  --accent-danger-dim: rgba(220, 38, 38, 0.08);
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  scrollbar-width: thin;
  scrollbar-color: var(--border-default) transparent;
}

html, body {
  height: 100%;
  width: 100%;
  overflow: hidden;
  background-color: var(--bg-canvas);
  color: var(--text-primary);
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  height: 100%;
  width: 100%;
  overflow: hidden;
}

/* 全局极简暗色/浅色自适应滚动条 */
::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: var(--border-default);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--border-active);
}

/* 全局通用输入控件与暗黑主题表单适配 */
input, textarea, select {
  background-color: var(--bg-surface-2);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  outline: none;
  font-family: inherit;
}

input:focus, textarea:focus, select:focus {
  border-color: var(--accent-science);
}

.modal-input, .modal-textarea {
  width: 100%;
  padding: 8px 12px;
  background-color: var(--bg-surface-2) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-default) !important;
  border-radius: 6px;
  font-size: 13px;
  transition: border-color 0.2s;
}

.modal-input:focus, .modal-textarea:focus {
  border-color: var(--accent-science) !important;
}

.form-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.btn-secondary {
  background-color: var(--bg-surface-2) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-default) !important;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
}

.btn-secondary:hover {
  background-color: var(--bg-hover) !important;
  border-color: var(--border-active) !important;
}

.btn-action-primary {
  background-color: var(--accent-science) !important;
  color: #ffffff !important;
  border: 1px solid transparent !important;
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
}

.btn-action-primary:hover {
  opacity: 0.9;
}

.btn-action-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
