<script setup>
import { ref, watch, computed } from 'vue'
import { api } from '../api/client'

const props = defineProps({
  show: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const loading = ref(false)
const domain = ref([])
const system = ref([])
const domainCount = ref(0)

const ERROR_LABELS = {
  cuda_oom: '显存溢出',
  file_not_found: '文件缺失',
  dependency: '依赖缺失',
  runtime_error: '运行时错误',
  value_error: '参数错误',
  unknown: '未分类',
}

const hasData = computed(() => domain.value.length > 0 || system.value.length > 0)

function labelFor(t) {
  return ERROR_LABELS[t] || (t || '未分类')
}

async function load() {
  if (!props.show) return
  loading.value = true
  try {
    const r = await api.getFaq()
    domain.value = r.domain || []
    system.value = r.system || []
    domainCount.value = r.domain_count || 0
  } catch (e) {
    domain.value = []
    system.value = []
  } finally {
    loading.value = false
  }
}

watch(() => props.show, (v) => { if (v) load() })
</script>

<template>
  <div v-if="show" class="modal-overlay" @click.self="emit('close')">
    <div class="modal-box faq-modal">
      <div class="faq-header">
        <h3>💡 报错知识库（FAQ 沉淀）</h3>
        <button class="btn-icon" @click="emit('close')">✕</button>
      </div>
      <p class="faq-sub">
        系统从每次成功分析中自动沉淀「报错 → 解决方案」，并随使用持续累积；
        相似问题再次出现时可直接复用历史解法。
      </p>

      <div v-if="loading" class="faq-loading">加载中…</div>
      <div v-else-if="!hasData" class="faq-empty">
        暂无沉淀内容。上传带报错的实验日志后，这里会自动积累 FAQ。
      </div>

      <template v-else>
        <section v-if="domain.length" class="faq-section">
          <h4>领域 FAQ（报错 → 解决方案）· 共 {{ domainCount }} 条</h4>
          <div v-for="(item, i) in domain" :key="i" class="faq-card">
            <div class="faq-card-top">
              <span class="faq-tag">{{ labelFor(item.error_type) }}</span>
              <span class="faq-count">出现 {{ item.count }} 次</span>
            </div>
            <div class="faq-err">⚠️ {{ item.error_text }}</div>
            <div class="faq-sol">✅ {{ item.solution_text }}</div>
            <div v-if="item.source_record" class="faq-src">来源：{{ item.source_record }}</div>
          </div>
        </section>

        <section v-if="system.length" class="faq-section">
          <h4>系统常见问题（运行失败排查）</h4>
          <div v-for="(item, i) in system" :key="i" class="faq-card faq-card-sys">
            <div class="faq-card-top">
              <span class="faq-tag faq-tag-sys">{{ item.signature }}</span>
              <span class="faq-count">出现 {{ item.count }} 次</span>
            </div>
            <div class="faq-sol">💡 {{ item.hint || item.message }}</div>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>

<style scoped>
.faq-modal { width: 640px; max-width: 92vw; max-height: 82vh; overflow-y: auto; }
.faq-header { display: flex; align-items: center; justify-content: space-between; }
.faq-header h3 { margin: 0; font-size: 16px; }
.faq-sub { font-size: 12px; color: #6b7280; margin: 6px 0 14px; line-height: 1.6; }
.faq-loading, .faq-empty { font-size: 13px; color: #9ca3af; padding: 24px 0; text-align: center; }
.faq-section { margin-bottom: 18px; }
.faq-section h4 { font-size: 13px; color: #374151; margin: 0 0 10px; }
.faq-card {
  border: 1px solid #e5e7eb; border-radius: 10px; padding: 10px 12px;
  margin-bottom: 10px; background: #fafafa;
}
.faq-card-sys { background: #fff7ed; border-color: #fed7aa; }
.faq-card-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.faq-tag {
  font-size: 11px; padding: 2px 8px; border-radius: 999px;
  background: #eef2ff; color: #4f46e5; font-weight: 600;
}
.faq-tag-sys { background: #ffedd5; color: #c2410c; }
.faq-count { font-size: 11px; color: #9ca3af; }
.faq-err { font-size: 13px; color: #b91c1c; margin-bottom: 4px; word-break: break-word; }
.faq-sol { font-size: 13px; color: #15803d; word-break: break-word; }
.faq-src { font-size: 11px; color: #a1a1aa; margin-top: 4px; }
</style>
