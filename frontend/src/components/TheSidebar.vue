<template>
  <aside class="sidebar">
    <div class="sidebar-brand">
      <div class="brand-icon">E</div>
      <span class="brand-text">ExpAgent</span>
    </div>
    <nav class="sidebar-nav">
      <router-link to="/" class="nav-item" active-class="nav-item--active">
        <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
        </svg>
        <span>上传分析</span>
      </router-link>
      <router-link to="/history" class="nav-item" active-class="nav-item--active">
        <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
        </svg>
        <span>实验记忆</span>
      </router-link>
      <router-link to="/graph" class="nav-item" active-class="nav-item--active">
        <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="17" cy="7" r="3"/><circle cx="7" cy="17" r="3"/>
          <line x1="14.3" y1="9.4" x2="9.7" y2="14.6"/>
        </svg>
        <span>知识图谱</span>
      </router-link>
    </nav>
    <div class="sidebar-footer">
      <a href="https://github.com/666ghj/MiroFish" target="_blank" class="nav-item footer-link">
        <span style="font-size:11px;color:var(--text-tertiary)">Inspired by MiroFish</span>
      </a>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 200px;
  min-width: 200px;
  height: 100vh;
  border-right: 1px solid var(--border-secondary);
  background: var(--bg-secondary);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border-secondary);
}

.brand-icon {
  width: 28px;
  height: 28px;
  background: var(--accent);
  color: var(--bg-primary);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
}

.brand-text {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.sidebar-nav {
  flex: 1;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--text-secondary);
  transition: background 0.15s, color 0.15s;
  text-decoration: none;
}

.nav-item:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.nav-item--active {
  background: var(--accent);
  color: var(--bg-primary);
}

.nav-item--active:hover {
  background: var(--accent-hover);
  color: var(--bg-primary);
}

.nav-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.sidebar-footer {
  padding: 12px 10px;
  border-top: 1px solid var(--border-secondary);
}

.footer-link {
  font-size: 11px;
  opacity: 0.6;
}
</style>
