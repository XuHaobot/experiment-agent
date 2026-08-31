<template>
  <div class="project-view">
    <div class="pv-header">
      <h2 class="pv-title">Research Projects</h2>
      <button class="btn-primary" @click="showCreate = true">+ 新建项目</button>
    </div>

    <!-- 新建项目弹窗 -->
    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
      <div class="modal-box">
        <h3>新建 Research Project</h3>
        <input v-model="newName" placeholder="项目名称" class="modal-input" />
        <textarea v-model="newDesc" placeholder="项目描述（可选）" class="modal-textarea" rows="3"></textarea>
        <div class="modal-actions">
          <button class="btn-primary" :disabled="!newName.trim()" @click="createProject">创建</button>
          <button class="btn-secondary" @click="showCreate = false">取消</button>
        </div>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="pv-loading">加载中…</div>

    <!-- 空状态 -->
    <div v-else-if="projects.length === 0" class="pv-empty">
      <div class="empty-icon">🔬</div>
      <p>还没有 Research Project</p>
      <p class="empty-sub">点击「新建项目」开始您的科研之旅</p>
    </div>

    <!-- 项目卡片列表 -->
    <div v-else class="pv-grid">
      <div
        v-for="p in projects"
        :key="p.id"
        class="project-card"
        @click="openProject(p.id)"
      >
        <div class="pc-icon">🔬</div>
        <div class="pc-body">
          <div class="pc-name">{{ p.name }}</div>
          <div class="pc-desc" v-if="p.description">{{ p.description }}</div>
          <div class="pc-meta">
            <span>{{ p.experiment_ids?.length || 0 }} 个实验</span>
            <span>{{ p.questions?.length || 0 }} 个问题</span>
            <span class="pc-date">{{ formatDate(p.updated_at) }}</span>
          </div>
        </div>
        <button class="pc-delete" @click.stop="confirmDelete(p)" title="删除项目">🗑</button>
      </div>
    </div>

    <!-- 删除确认 -->
    <div v-if="pendingDelete" class="modal-overlay" @click.self="pendingDelete = null">
      <div class="modal-box modal-danger">
        <h3>删除项目</h3>
        <p>确定删除「<strong>{{ pendingDelete.name }}</strong>」？</p>
        <p class="modal-sub">项目将被删除，关联的实验记录不受影响。</p>
        <div class="modal-actions">
          <button class="btn-danger" @click="doDelete">删除</button>
          <button class="btn-secondary" @click="pendingDelete = null">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { projectApi } from '../api/project.js'

export default {
  name: 'ProjectView',
  data() {
    return {
      projects: [],
      loading: true,
      showCreate: false,
      newName: '',
      newDesc: '',
      pendingDelete: null,
    }
  },
  mounted() {
    this.loadProjects()
  },
  methods: {
    async loadProjects() {
      this.loading = true
      try {
        const data = await projectApi.list()
        this.projects = data.projects || []
      } catch (e) {
        console.error(e)
      } finally {
        this.loading = false
      }
    },
    async createProject() {
      if (!this.newName.trim()) return
      try {
        await projectApi.create({ name: this.newName.trim(), description: this.newDesc.trim() })
        this.showCreate = false
        this.newName = ''
        this.newDesc = ''
        await this.loadProjects()
      } catch (e) {
        alert('创建失败：' + e.message)
      }
    },
    confirmDelete(p) {
      this.pendingDelete = p
    },
    async doDelete() {
      if (!this.pendingDelete) return
      try {
        await projectApi.delete(this.pendingDelete.id)
        this.pendingDelete = null
        await this.loadProjects()
      } catch (e) {
        alert('删除失败：' + e.message)
      }
    },
    openProject(id) {
      this.$router.push(`/projects/${id}`)
    },
    formatDate(iso) {
      if (!iso) return ''
      return new Date(iso).toLocaleDateString('zh-CN')
    },
  },
}
</script>

<style scoped>
.project-view { padding: 24px; max-width: 1000px; margin: 0 auto; }
.pv-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
.pv-title { font-size: 22px; font-weight: 700; margin: 0; }
.pv-loading, .pv-empty { text-align: center; padding: 60px 0; color: #888; }
.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-sub { font-size: 13px; color: #aaa; }
.pv-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.project-card {
  background: var(--surface, #fff);
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 12px;
  padding: 18px;
  cursor: pointer;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  transition: box-shadow .15s, border-color .15s;
  position: relative;
}
.project-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.08); border-color: #6366f1; }
.pc-icon { font-size: 28px; flex-shrink: 0; }
.pc-body { flex: 1; min-width: 0; }
.pc-name { font-weight: 600; font-size: 15px; margin-bottom: 4px; }
.pc-desc { font-size: 13px; color: #888; margin-bottom: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pc-meta { display: flex; gap: 12px; font-size: 12px; color: #aaa; flex-wrap: wrap; }
.pc-date { margin-left: auto; }
.pc-delete {
  position: absolute; top: 10px; right: 10px;
  background: none; border: none; cursor: pointer;
  font-size: 14px; opacity: 0; transition: opacity .15s;
}
.project-card:hover .pc-delete { opacity: 1; }
.btn-primary { background: #6366f1; color: #fff; border: none; padding: 8px 18px; border-radius: 8px; cursor: pointer; font-size: 14px; }
.btn-primary:disabled { opacity: .5; cursor: not-allowed; }
.btn-secondary { background: none; border: 1px solid #ddd; padding: 8px 18px; border-radius: 8px; cursor: pointer; font-size: 14px; }
.btn-danger { background: #ef4444; color: #fff; border: none; padding: 8px 18px; border-radius: 8px; cursor: pointer; font-size: 14px; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-box { background: #fff; border-radius: 12px; padding: 28px; min-width: 360px; max-width: 480px; }
.modal-box h3 { margin: 0 0 16px; }
.modal-input { width: 100%; box-sizing: border-box; padding: 8px 12px; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 10px; font-size: 14px; }
.modal-textarea { width: 100%; box-sizing: border-box; padding: 8px 12px; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 16px; font-size: 14px; resize: vertical; }
.modal-actions { display: flex; gap: 10px; }
.modal-danger h3 { color: #ef4444; }
.modal-sub { font-size: 12px; color: #888; margin-top: 4px; }
</style>
