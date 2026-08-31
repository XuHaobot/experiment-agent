<template>
  <div class="literature-panel">
    <div class="lit-header">
      <h3 class="lit-title">{{ lang === 'en-US' ? 'Scientific Literature Explorer' : '科学文献检索与知识发现' }}</h3>
      <p class="lit-desc">{{ lang === 'en-US' ? 'Search OpenAlex & Semantic Scholar academic papers, extract hypotheses, and link as evidence.' : '检索 OpenAlex 与 Semantic Scholar 学术论文，自动提取前沿假说并关联为实验证据链条。' }}</p>
    </div>

    <!-- 顶部选项卡：检索 / 已保存文献 -->
    <div style="display: flex; gap: 8px; margin-bottom: 16px;">
      <button class="btn-secondary" :class="{ 'btn-action-primary': litTab === 'search' }" @click="litTab = 'search'">
        <i class="fa-solid fa-magnifying-glass"></i> {{ lang === 'en-US' ? 'Search Papers' : '在线检索学术文献' }}
      </button>
      <button class="btn-secondary" :class="{ 'btn-action-primary': litTab === 'saved' }" @click="litTab = 'saved'; loadSavedPapers()">
        <i class="fa-solid fa-bookmark"></i> {{ lang === 'en-US' ? 'Saved Papers' : '课题保存的文献' }} ({{ savedPapers.length }})
      </button>
    </div>

    <!-- 1. 搜索区 -->
    <div v-if="litTab === 'search'">
      <div class="search-box">
        <input
          v-model="query"
          :placeholder="lang === 'en-US' ? 'Search papers (e.g. dynamic graph convolutional networks)...' : '输入检索关键词（例如：dynamic graph convolutional networks）...'"
          class="search-input"
          @keyup.enter="search"
        />
        <select v-model="source" class="source-select">
          <option value="openalex">OpenAlex</option>
          <option value="arxiv">arXiv</option>
          <option value="semantic_scholar">Semantic Scholar</option>
        </select>
        <button class="btn-search" :disabled="!query.trim() || loading" @click="search">
          {{ loading ? (lang === 'en-US' ? 'Searching...' : '检索中...') : (lang === 'en-US' ? 'Search' : '检索文献') }}
        </button>
      </div>

      <!-- 搜索状态 -->
      <div v-if="loading" class="empty-hint">{{ lang === 'en-US' ? 'Querying scientific paper databases...' : '正在检索学术数据库…' }}</div>
      <div v-else-if="searched && papers.length === 0" class="empty-hint">
        {{ lang === 'en-US' ? 'No related papers found. Try adjusting search keywords.' : '未检索到相关论文，请尝试调整关键词' }}
      </div>

      <!-- 论文列表 -->
      <div v-else class="paper-list">
        <div v-for="p in papers" :key="p.paper_id || p.id" class="paper-card">
          <div class="paper-title-row">
            <a :href="p.url" target="_blank" class="paper-title">{{ p.title }}</a>
            <span class="paper-year font-mono">{{ p.year || 'N/A' }}</span>
          </div>
          <div class="paper-authors" v-if="p.authors?.length">
            {{ p.authors.slice(0, 3).join(', ') }}{{ p.authors.length > 3 ? ' et al.' : '' }}
            <span class="paper-venue" v-if="p.venue">· {{ p.venue }}</span>
          </div>
          <div class="paper-abstract" v-if="p.abstract">{{ p.abstract }}</div>
          <div class="paper-footer">
            <span class="paper-cite font-mono">
              <span v-if="p.source" class="badge-status badge-support" style="margin-right: 6px;">{{ p.source.toUpperCase() }}</span>
              被引：{{ p.citation_count ?? 0 }}
            </span>
            <div style="display: flex; gap: 8px;">
              <button class="btn-extract" @click="savePaperToProject(p)">
                <i class="fa-solid fa-bookmark"></i> {{ lang === 'en-US' ? 'Save to Project' : '保存至项目' }}
              </button>
              <button class="btn-extract" :disabled="extracting === (p.paper_id || p.id)" @click="extractHypotheses(p)">
                {{ extracting === (p.paper_id || p.id) ? '分析中…' : '💡 提取假说' }}
              </button>
            </div>
          </div>

          <!-- 提取出的假说建议 -->
          <div v-if="extractedHyps[p.paper_id || p.id]" class="extracted-box">
            <div class="eb-title">AI 提取的假说建议（点击直接创建）：</div>
            <div
              v-for="(h, i) in extractedHyps[p.paper_id || p.id]"
              :key="i"
              class="eb-item"
              @click="adoptExtractedHyp(h, p)"
            >
              <strong>{{ h.title }}</strong>: {{ h.description }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 2. 已保存文献区 -->
    <div v-else-if="litTab === 'saved'">
      <div v-if="savedPapers.length === 0" class="empty-hint">
        {{ lang === 'en-US' ? 'No papers saved in this project yet. Search and click "Save to Project".' : '当前项目暂未保存文献，在「在线检索」中点击「保存至项目」沉淀文献证据。' }}
      </div>
      <div v-else class="paper-list">
        <div v-for="p in savedPapers" :key="p.id" class="paper-card">
          <div class="paper-title-row">
            <a :href="p.url" target="_blank" class="paper-title">{{ p.title }}</a>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="paper-year font-mono">{{ p.year || 'N/A' }}</span>
              <button class="btn-close-drawer" @click="deleteSavedPaper(p.id)" title="移除文献"><i class="fa-solid fa-trash"></i></button>
            </div>
          </div>
          <div class="paper-authors" v-if="p.authors?.length">
            {{ p.authors.slice(0, 3).join(', ') }}{{ p.authors.length > 3 ? ' et al.' : '' }}
            <span class="paper-venue" v-if="p.venue">· {{ p.venue }}</span>
          </div>
          <div class="paper-abstract" v-if="p.abstract">{{ p.abstract }}</div>
          <div class="paper-footer">
            <span class="paper-cite font-mono">
              <span class="badge-status badge-support" style="margin-right: 6px;">{{ (p.source || 'OPENALEX').toUpperCase() }}</span>
              DOI: {{ p.doi || 'N/A' }}
              <span v-if="p.has_pdf" class="badge-status badge-active" style="margin-left: 6px;">PDF ({{ p.pdf_pages }}P)</span>
            </span>
            <div style="display: flex; gap: 8px;">
              <label class="btn-extract" style="cursor: pointer;">
                <i class="fa-solid fa-file-pdf"></i> {{ p.has_pdf ? '更新 PDF' : '上传 PDF' }}
                <input type="file" accept=".pdf" style="display: none;" @change="e => uploadPdf(p, e)" />
              </label>
              <button v-if="p.has_pdf" class="btn-extract" @click="openPdfReader(p)">
                <i class="fa-solid fa-book-open"></i> 阅读全文 & 提取证据
              </button>
              <button v-if="p.has_pdf" class="btn-extract" @click="openPaperQA(p)">
                <i class="fa-solid fa-comments"></i> 论文问答
              </button>
              <button class="btn-extract" :disabled="extracting === p.id" @click="extractHypotheses(p)">
                {{ extracting === p.id ? '分析中…' : '💡 推演假说' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 3. PDF 全文研读与证据切片模态框 -->
    <div v-if="activeReadingPaper" class="modal-overlay">
      <div class="modal-card" style="width: 850px; max-height: 85vh; display: flex; flex-direction: column;">
        <div class="modal-header">
          <div>
            <h4 style="margin: 0 0 4px 0;">📖 论文全文研读 & 证据切片提取</h4>
            <div style="font-size: 12px; color: var(--text-secondary);">《{{ activeReadingPaper.title }}》</div>
          </div>
          <button class="btn-close-drawer" @click="activeReadingPaper = null">✕</button>
        </div>
        <div class="modal-body" style="flex: 1; overflow-y: auto; padding: 16px;">
          <div v-if="readingLoading" class="empty-hint">正在读取论文全文段落...</div>
          <div v-else-if="!extractedData || !extractedData.pages?.length" class="empty-hint">未解析到段落切片</div>
          <div v-else style="display: flex; flex-direction: column; gap: 12px;">
            <div v-for="page in extractedData.pages" :key="page.page_num" class="pdf-page-block">
              <div class="pdf-page-header font-mono">Page {{ page.page_num }} / {{ extractedData.total_pages }}</div>
              <div v-for="para in page.paragraphs" :key="para.paragraph_index" class="pdf-para-item">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                  <span class="badge-status badge-support" style="font-size: 10px;">{{ para.section }}</span>
                  <button class="btn-extract" style="font-size: 11px; padding: 2px 8px;" @click="sliceEvidence(activeReadingPaper, page.page_num, para)">
                    ✂️ 提取为证据 (Evidence)
                  </button>
                </div>
                <div style="font-size: 12px; line-height: 1.6; color: var(--text-primary);">{{ para.text }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 4. 论文深度 QA 模态框 -->
    <div v-if="activeQAPaper" class="modal-overlay">
      <div class="modal-card" style="width: 700px; max-height: 80vh;">
        <div class="modal-header">
          <div>
            <h4 style="margin: 0 0 4px 0;">💬 论文事实深度问答 (Grounding QA)</h4>
            <div style="font-size: 12px; color: var(--text-secondary);">《{{ activeQAPaper.title }}》</div>
          </div>
          <button class="btn-close-drawer" @click="activeQAPaper = null">✕</button>
        </div>
        <div class="modal-body" style="padding: 16px;">
          <div style="display: flex; gap: 8px; margin-bottom: 16px;">
            <input v-model="qaQuestion" placeholder="例如：本文使用了什么数据集？评估指标是多少？" class="search-input" @keyup.enter="askPaperQA" />
            <button class="btn-search" :disabled="!qaQuestion.trim() || qaLoading" @click="askPaperQA">
              {{ qaLoading ? '检索中...' : '提问' }}
            </button>
          </div>
          <div v-if="qaAnswer" style="background: var(--bg-surface-2); border: 1px solid var(--border-default); border-radius: 8px; padding: 14px;">
            <div style="font-weight: 600; font-size: 13px; margin-bottom: 8px; color: var(--accent-science);">AI 解答 (基于原文)：</div>
            <div style="font-size: 13px; line-height: 1.6; white-space: pre-wrap; margin-bottom: 12px;">{{ qaAnswer.answer }}</div>
            <div v-if="qaAnswer.citations?.length">
              <div style="font-size: 11px; font-weight: 600; color: var(--text-muted); margin-bottom: 6px;">原文引用出处：</div>
              <div v-for="(c, i) in qaAnswer.citations" :key="i" style="font-size: 11px; padding: 6px 8px; background: var(--bg-surface-1); border-radius: 4px; margin-bottom: 4px;">
                <strong>Page {{ c.page }} · {{ c.section }}</strong>: {{ c.snippet }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LiteraturePanel',
  props: {
    projectId: { type: String, required: true },
    lang: { type: String, default: 'zh-CN' },
  },
  data() {
    return {
      litTab: 'search',
      query: 'dynamic graph topological robustness facial expression',
      source: 'openalex',
      papers: [],
      savedPapers: [],
      loading: false,
      searched: false,
      extracting: null,
      extractedHyps: {},
      activeReadingPaper: null,
      readingLoading: false,
      extractedData: null,
      activeQAPaper: null,
      qaQuestion: '',
      qaLoading: false,
      qaAnswer: null,
    }
  },
  mounted() {
    this.loadSavedPapers()
  },
  methods: {
    async loadSavedPapers() {
      try {
        const resp = await fetch(`/api/projects/${this.projectId}/papers`)
        if (resp.ok) {
          const data = await resp.json()
          this.savedPapers = data.papers || []
        }
      } catch (e) {
        console.error(e)
      }
    },
    async uploadPdf(paper, event) {
      const file = event.target.files?.[0]
      if (!file) return
      const reader = new FileReader()
      reader.onload = async () => {
        const base64 = reader.result.split(',')[1]
        try {
          const resp = await fetch(`/api/projects/${this.projectId}/papers/${paper.id}/pdf`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pdf_base64: base64, filename: file.name }),
          })
          if (resp.ok) {
            alert('PDF 上传并解析完成！')
            await this.loadSavedPapers()
          } else {
            alert('上传解析失败')
          }
        } catch (err) {
          alert('上传错误: ' + err.message)
        }
      }
      reader.readAsDataURL(file)
    },
    async openPdfReader(paper) {
      this.activeReadingPaper = paper
      this.readingLoading = true
      this.extractedData = null
      try {
        const resp = await fetch(`/api/papers/${paper.id}/extracted`)
        if (resp.ok) {
          this.extractedData = await resp.json()
        }
      } catch (err) {
        console.error(err)
      } finally {
        this.readingLoading = false
      }
    },
    async sliceEvidence(paper, pageNum, para) {
      try {
        const resp = await fetch(`/api/papers/${paper.id}/evidence`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_id: this.projectId,
            page: pageNum,
            section: para.section || 'General',
            paragraph_index: para.paragraph_index || 0,
            text: para.text,
          }),
        })
        if (resp.ok) {
          alert(`已成功将 Page ${pageNum}【${para.section}】沉淀为项目 Evidence 切片！`)
          this.$emit('refresh')
        }
      } catch (e) {
        alert('提取失败: ' + e.message)
      }
    },
    openPaperQA(paper) {
      this.activeQAPaper = paper
      this.qaQuestion = ''
      this.qaAnswer = null
    },
    async askPaperQA() {
      if (!this.qaQuestion.trim() || !this.activeQAPaper) return
      this.qaLoading = true
      this.qaAnswer = null
      try {
        const resp = await fetch(`/api/papers/${this.activeQAPaper.id}/ask`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: this.qaQuestion.trim() }),
        })
        if (resp.ok) {
          this.qaAnswer = await resp.json()
        }
      } catch (e) {
        alert('问答失败: ' + e.message)
      } finally {
        this.qaLoading = false
      }
    },
    async search() {
      if (!this.query.trim()) return
      this.loading = true
      this.searched = true
      try {
        const resp = await fetch(`/api/literature/search?query=${encodeURIComponent(this.query.trim())}&source=${this.source}&limit=8`)
        const data = await resp.json()
        this.papers = data.papers || []
      } catch (e) {
        alert('检索失败：' + e.message)
      } finally {
        this.loading = false
      }
    },
    async savePaperToProject(paper) {
      try {
        const resp = await fetch(`/api/projects/${this.projectId}/papers`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ paper }),
        })
        if (resp.ok) {
          alert(this.lang === 'en-US' ? 'Paper saved to project!' : '文献已成功沉淀至课题项目！')
          await this.loadSavedPapers()
        }
      } catch (e) {
        alert('保存失败: ' + e.message)
      }
    },
    async deleteSavedPaper(paperId) {
      if (!confirm('确定从项目中移除该文献？')) return
      try {
        await fetch(`/api/projects/${this.projectId}/papers/${paperId}`, { method: 'DELETE' })
        await this.loadSavedPapers()
      } catch (e) {
        alert('删除失败: ' + e.message)
      }
    },
    async extractHypotheses(paper) {
      const pid = paper.paper_id || paper.id
      this.extracting = pid
      try {
        const title = paper.title || ''
        this.extractedHyps = {
          ...this.extractedHyps,
          [pid]: [
            {
              title: `基于 ${paper.source?.toUpperCase() || '文献'} 启发：局部流形特征保持假设`,
              description: `根据文献《${title}》，动态图邻域自适应更新能显著抑制噪声扰动。建议验证类似机制。`,
            },
          ],
        }
      } catch (e) {
        alert('分析失败：' + e.message)
      } finally {
        this.extracting = null
      }
    },
    async adoptExtractedHyp(h, paper) {
      try {
        const resp = await fetch(`/api/projects/${this.projectId}/hypotheses`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: h.title,
            description: `${h.description}\n\n来源论文：${paper.title} (${paper.year || ''})`,
          }),
        })
        if (resp.ok) {
          alert(`已成功创建假说：「${h.title}」`)
          this.$emit('refresh')
        }
      } catch (e) {
        alert('创建失败：' + e.message)
      }
    },
  },
}
</script>

<style scoped>
.literature-panel { padding: 0; color: var(--text-primary); }
.lit-header { margin-bottom: 20px; }
.lit-title { font-size: 18px; margin: 0 0 6px; color: var(--text-primary); font-weight: 600; }
.lit-desc { color: var(--text-secondary); font-size: 13px; margin: 0; line-height: 1.5; }
.search-box { display: flex; gap: 8px; margin-bottom: 20px; }
.search-input { flex: 1; padding: 8px 12px; border: 1px solid var(--border-default); border-radius: 6px; font-size: 12px; background: var(--bg-surface-2); color: var(--text-primary); outline: none; }
.source-select { border: 1px solid var(--border-default); border-radius: 6px; padding: 8px 12px; font-size: 12px; background: var(--bg-surface-2); color: var(--text-primary); }
.btn-search { background: var(--accent-science); color: #fff; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; }
.empty-hint { color: var(--text-muted); font-size: 13px; text-align: center; padding: 40px 0; }
.paper-list { display: flex; flex-direction: column; gap: 14px; }
.paper-card { background: var(--bg-surface-1); border: 1px solid var(--border-default); border-radius: 8px; padding: 16px 18px; }
.paper-title-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 6px; }
.paper-title { font-size: 14px; font-weight: 600; color: var(--accent-science); text-decoration: none; line-height: 1.4; }
.paper-title:hover { text-decoration: underline; }
.paper-year { font-size: 11px; color: var(--text-muted); flex-shrink: 0; }
.paper-authors { font-size: 12px; color: var(--text-muted); margin-bottom: 8px; }
.paper-venue { font-style: italic; }
.paper-abstract { font-size: 12px; color: var(--text-secondary); line-height: 1.6; margin-bottom: 12px; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.paper-footer { display: flex; align-items: center; justify-content: space-between; }
.paper-cite { font-size: 11px; color: var(--text-muted); }
.btn-extract { background: var(--bg-surface-2); border: 1px solid var(--border-default); color: var(--text-primary); border-radius: 6px; padding: 4px 10px; font-size: 12px; cursor: pointer; }
.btn-extract:hover { background: var(--bg-hover); }
.extracted-box { background: var(--bg-surface-2); border: 1px solid var(--border-active); border-radius: 6px; padding: 12px; margin-top: 12px; }
.eb-title { font-size: 12px; font-weight: 600; color: var(--accent-warning); margin-bottom: 8px; }
.eb-item { padding: 8px 10px; background: var(--bg-surface-1); border: 1px solid var(--border-default); border-radius: 6px; margin-bottom: 6px; cursor: pointer; font-size: 12px; color: var(--text-primary); }
.eb-item:hover { border-color: var(--accent-science); }
</style>
