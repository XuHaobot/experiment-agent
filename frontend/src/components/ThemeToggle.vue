<template>
  <button class="theme-toggle" @click="$emit('update:modelValue', !modelValue)" :title="modelValue ? '切换亮色' : '切换暗色'">
    <svg v-if="!modelValue" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="toggle-icon">
      <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
    </svg>
    <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="toggle-icon">
      <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/>
      <line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/>
      <line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>
  </button>
</template>

<script setup>
defineProps({ modelValue: Boolean })
defineEmits(['update:modelValue'])
</script>

<style scoped>
.theme-toggle {
  width: 34px;
  height: 34px;
  border: 1px solid var(--border-secondary);
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, border-color 0.15s;
}

.theme-toggle:hover {
  background: var(--bg-tertiary);
  border-color: var(--border-primary);
}

.toggle-icon {
  width: 16px;
  height: 16px;
  color: var(--text-primary);
}
</style>
