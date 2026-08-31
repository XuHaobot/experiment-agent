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
</style>
