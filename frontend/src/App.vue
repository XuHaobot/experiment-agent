<template>
  <WorkspaceMain />
</template>

<script setup>
import WorkspaceMain from './views/WorkspaceMain.vue'
</script>

<style>
/* 全局样式重置 - 保留原有设计系统 */
:root {
  --primary: #F3A04C;
  --accent: #E58522;
  --background: #F4F4F6;
  --panel-bg: #FEFDFC;
  --card-bg: #fff;
  --bg-primary: #F4F4F6;
  --bg-secondary: rgba(0,0,0,.04);
  --bg-tertiary: rgba(0,0,0,.06);
  --border-primary: rgba(0,0,0,.12);
  --border-secondary: rgba(0,0,0,.08);
  --text-primary: rgba(0,0,0,.8);
  --text-secondary: rgba(0,0,0,.5);
  --text-tertiary: rgba(0,0,0,.35);
  --radius-sm: 8px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --font-mono: ui-monospace, "Cascadia Code", "Fira Code", monospace;
}

@media (prefers-color-scheme: dark) {
  :root {
    --background: #232324;
    --panel-bg: #332D28;
    --card-bg: #2E2E2E;
    --bg-primary: #232324;
    --bg-secondary: rgba(255,255,255,.06);
    --bg-tertiary: rgba(255,255,255,.1);
    --border-primary: rgba(255,255,255,.15);
    --border-secondary: rgba(255,255,255,.1);
    --text-primary: rgba(255,255,255,.8);
    --text-secondary: rgba(255,255,255,.5);
    --text-tertiary: rgba(255,255,255,.35);
  }
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body {
  height: 100%;
  overflow: hidden;
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  height: 100%;
}
</style>
