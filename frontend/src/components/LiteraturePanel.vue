<template>
  <div class="literature-panel">
    <div class="lit-header">
      <h3 class="lit-title">{{ lang === 'en-US' ? 'Scientific Literature Explorer & AI Synthesis' : '科学文献检索、本地上传与 AI 深度研读' }}</h3>
      <p class="lit-desc">{{ lang === 'en-US' ? 'Search 6 global academic repositories, upload local PDFs/documents, and run AI deep reading to extract testable hypotheses.' : '跨 6 大官方学术库检索、支持本地 PDF/文档上传解析，并自动运行 AI 深度研读提炼可证伪科学假说。' }}</p>
    </div>

    <!-- 顶部选项卡 -->
    <div style="display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;">
      <button class="btn-secondary" :class="{ 'btn-action-primary': litTab === 'search' }" @click="litTab = 'search'">
        <i class="fa-solid fa-magnifying-glass"></i> {{ lang === 'en-US' ? 'Search Papers' : '在线检索学术文献' }}
      </button>
      <button class="btn-secondary" :class="{ 'btn-action-primary': litTab === 'upload' }" @click="litTab = 'upload'">
        <i class="fa-solid fa-cloud-arrow-up"></i> {{ lang === 'en-US' ? 'Upload PDF / Local Paper' : '📤 本地文献上传与 AI 研读' }}
      </button>
      <button class="btn-secondary" :class="{ 'btn-action-primary': litTab === 'saved' }" @click="litTab = 'saved'; loadSavedPapers()">
        <i class="fa-solid fa-bookmark"></i> {{ lang === 'en-US' ? 'Saved Papers' : '课题保存的文献' }} ({{ savedPapers.length }})
      </button>
      <button class="btn-secondary" :class="{ 'btn-action-primary': litTab === 'import' }" @click="litTab = 'import'">
        <i class="fa-solid fa-file-code"></i> {{ lang === 'en-US' ? 'Direct Import (DOI / BibTeX)' : '📋 DOI / BibTeX 一键导入' }}
      </button>
    </div>

    <!-- 1. 在线搜索区 -->
    <div v-if="litTab === 'search'">
      <div class="search-box">
        <input
          v-model="query"
          :placeholder="lang === 'en-US' ? 'Search papers (e.g. dynamic graph convolutional networks)...' : '输入检索关键词（例如：dynamic graph convolutional networks）...'"
          class="search-input"
          @keyup.enter="search"
        />
        <select v-model="source" class="source-select">
          <option value="openalex">🌍 OpenAlex (全球开放获取)</option>
          <option value="arxiv">📄 arXiv (预印本)</option>
          <option value="semantic_scholar">🔬 Semantic Scholar (AI 引用)</option>
          <option value="pubmed">🧬 PubMed (生物医药与生信)</option>
          <option value="dblp">💻 DBLP (计算机与 AI 会议)</option>
          <option value="crossref">🆔 CrossRef (全球 DOI 检索)</option>
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
              <button class="btn-action-primary" style="font-size: 11px; padding: 4px 10px;" @click="savePaperToProject(p)">
                <i class="fa-solid fa-bookmark"></i> {{ lang === 'en-US' ? 'Save to Project' : '保存至项目' }}
              </button>
              <button class="btn-secondary" style="font-size: 11px;" @click="triggerDirectDeepRead(p)">
                <i class="fa-solid fa-wand-magic-sparkles"></i> 🤖 AI 研读
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 2. 本地文献上传与 AI 自动研读 -->
    <div v-if="litTab === 'upload'" class="card" style="padding: 20px; background: var(--bg-surface-1); border: 1px solid var(--border-default); border-radius: 10px;">
      <div style="margin-bottom: 16px;">
        <h4 style="margin: 0; font-size: 14px; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
          <i class="fa-solid fa-file-pdf" style="color: var(--accent-science);"></i>
          <span>{{ lang === 'en-US' ? 'Upload Local Paper (PDF / Markdown / TXT)' : '上传本地文献并开启 AI 深度研读' }}</span>
        </h4>
        <p style="margin: 4px 0 0; font-size: 12px; color: var(--text-secondary);">
          {{ lang === 'en-US' ? 'Upload full paper PDF or text files. The system extracts full-text sections, summarizes methodology, and extracts hypotheses.' : '上传论文 PDF 或全文文本，系统自动提取标题、作者、核心方法并生成结构化 AI 研读报告与科学假说。' }}
        </p>
      </div>

      <!-- 拖拽上传区域 -->
      <div class="upload-dropzone" @click="triggerFileInput" @dragover.prevent @drop.prevent="handleFileDrop">
        <i class="fa-solid fa-cloud-arrow-up" style="font-size: 32px; color: var(--accent-science); margin-bottom: 10px;"></i>
        <div style="font-weight: 600; font-size: 13px; color: var(--text-primary); margin-bottom: 4px;">
          {{ lang === 'en-US' ? 'Click to browse or drag & drop PDF / TXT / Markdown file here' : '点击选择文件 或 将 PDF / TXT / Markdown 论文拖拽至此' }}
        </div>
        <div class="text-muted font-mono" style="font-size: 11px;">支持格式: .pdf, .txt, .md, .bib (最大 50MB)</div>
        <input ref="fileInput" type="file" accept=".pdf,.txt,.md,.markdown,.bib" style="display: none;" @change="handleFileSelected" />
      </div>

      <!-- 上传中状态 -->
      <div v-if="uploadingPaper" class="empty-hint" style="padding: 20px 0;">
        <i class="fa-solid fa-circle-notch fa-spin" style="color: var(--accent-science); margin-right: 6px;"></i>
        正在解析文档并提取全文段落...
      </div>

      <!-- 或者手动粘贴文本 -->
      <div style="margin-top: 20px; border-top: 1px solid var(--border-default); padding-top: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <label class="form-label" style="margin-bottom: 0;">或者直接粘贴论文全文 / 摘要文本：</label>
          <button class="btn-secondary" style="font-size: 11px;" @click="fillSamplePaperText">填入示例论文文本</button>
        </div>
        <input v-model="manualPaperTitle" placeholder="论文标题 (例如: Dynamic Graph Convolutional Neural Networks)" class="modal-input" style="margin-bottom: 8px;" />
        <textarea
          v-model="manualPaperText"
          placeholder="在此粘贴论文 Abstract / Full Text..."
          rows="6"
          class="modal-textarea"
          style="font-family: var(--font-mono, monospace); font-size: 12px;"
        ></textarea>
        <div style="display: flex; justify-content: flex-end; margin-top: 10px;">
          <button
            class="btn-action-primary"
            :disabled="!manualPaperText.trim() || uploadingPaper"
            @click="handleManualUpload"
          >
            <i class="fa-solid fa-file-circle-check"></i>
            <span>入库并立即启动 AI 深度研读</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 3. 已保存文献区 -->
    <div v-if="litTab === 'saved'">
      <div v-if="savedPapers.length === 0" class="empty-hint">
        {{ lang === 'en-US' ? 'No papers saved in this project yet. Search or upload to begin.' : '当前项目暂未保存文献，在「在线检索」或「本地上传」中沉淀文献证据。' }}
      </div>
      <div v-else class="paper-list">
        <div v-for="p in savedPapers" :key="p.id" class="paper-card">
          <div class="paper-title-row">
            <a v-if="p.url" :href="p.url" target="_blank" class="paper-title">{{ p.title }}</a>
            <span v-else class="paper-title" style="cursor: default;">{{ p.title }}</span>
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
              <span class="badge-status badge-support" style="margin-right: 6px;">{{ (p.source || 'LOCAL').toUpperCase() }}</span>
              <span v-if="p.doi">DOI: {{ p.doi }}</span>
              <span v-if="p.reading_analysis" class="badge-status badge-active" style="margin-left: 6px; background: rgba(56,189,248,0.15); color: #38bdf8;">✓ 已生成 AI 研读报告</span>
            </span>
            <div style="display: flex; gap: 8px;">
              <button class="btn-action-primary" style="font-size: 11px; padding: 4px 10px;" @click="openDeepReadingModal(p)">
                <i class="fa-solid fa-wand-magic-sparkles"></i> {{ p.reading_analysis ? '查看 AI 研读报告' : '🤖 AI 深度研读' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 4. DOI / BibTeX 直接导入区 -->
    <div v-if="litTab === 'import'" class="card" style="padding: 20px; background: var(--bg-surface-1); border: 1px solid var(--border-default); border-radius: 10px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <div>
          <h4 style="margin: 0; font-size: 14px; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
            <i class="fa-solid fa-bolt" style="color: var(--accent-science);"></i>
            <span>{{ lang === 'en-US' ? 'Direct BibTeX / DOI Code Ingestion' : 'DOI / BibTeX 文本免爬虫直入' }}</span>
          </h4>
          <p style="margin: 4px 0 0; font-size: 12px; color: var(--text-secondary);">
            {{ lang === 'en-US' ? 'Paste raw BibTeX citations from Google Scholar, IEEE, CNKI or DOI numbers. Zero anti-scraping risk.' : '支持从 Google Scholar、知网、IEEE、DBLP 等直接复制 BibTeX 代码或 DOI 字符串，秒级完成元数据沉淀与关联。' }}
          </p>
        </div>
        <div style="display: flex; gap: 6px;">
          <button class="btn-secondary" style="font-size: 11px;" @click="fillSampleBibtex">
            {{ lang === 'en-US' ? 'Example BibTeX' : '填入示例 BibTeX' }}
          </button>
          <button class="btn-secondary" style="font-size: 11px;" @click="fillSampleDoi">
            {{ lang === 'en-US' ? 'Example DOI' : '填入示例 DOI' }}
          </button>
        </div>
      </div>

      <div style="margin-bottom: 14px;">
        <textarea
          v-model="directImportText"
          :placeholder="lang === 'en-US' ? 'Paste @article{...} or 10.1145/3305367 here...' : '在此粘贴 BibTeX 引用代码（例如 @inproceedings{...}）或 DOI 编号（例如 10.1145/3305367）...'"
          rows="8"
          class="modal-textarea"
          style="font-family: var(--font-mono, monospace); font-size: 12px;"
        ></textarea>
      </div>

      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span class="text-muted" style="font-size: 11px;">
          <i class="fa-solid fa-shield-halved" style="color: var(--accent-success); margin-right: 4px;"></i>
          {{ lang === 'en-US' ? 'Safe parsing mode: Uses CrossRef API and local AST parser.' : '安全解析模式：自动调用 CrossRef 权威解析与本地 AST 语法树无损提取。' }}
        </span>
        <button
          class="btn-action-primary"
          :disabled="!directImportText.trim() || directImporting"
          @click="handleDirectImport"
          style="padding: 8px 18px; font-size: 12px;"
        >
          <i class="fa-solid fa-cloud-arrow-up"></i>
          <span>{{ directImporting ? (lang === 'en-US' ? 'Importing...' : '正在入库...') : (lang === 'en-US' ? 'Import & Save to Project' : '立即解析并沉淀至课题') }}</span>
        </button>
      </div>
    </div>

    <!-- 5. AI 深度研读报告交互式模态框 -->
    <div v-if="activeReadingPaper" class="modal-mask" @click.self="activeReadingPaper = null">
      <div class="modal-card" style="width: 800px; max-height: 85vh;">
        <div class="modal-header">
          <div>
            <h3 style="display: flex; align-items: center; gap: 8px;">
              <i class="fa-solid fa-wand-magic-sparkles" style="color: var(--accent-science);"></i>
              <span>AI 文献深度研读与假说提炼报告</span>
            </h3>
            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
              《{{ activeReadingPaper.title }}》
            </div>
          </div>
          <button class="btn-close" @click="activeReadingPaper = null"><i class="fa-solid fa-xmark"></i></button>
        </div>

        <div style="flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 16px;">
          <div v-if="analyzingPaper" class="empty-hint" style="padding: 40px 0;">
            <i class="fa-solid fa-circle-notch fa-spin" style="font-size: 24px; color: var(--accent-science); margin-bottom: 10px;"></i>
            <div>AI 正在深度解析文献语义结构并提炼科学假说...</div>
          </div>

          <div v-else-if="readingAnalysis" style="display: flex; flex-direction: column; gap: 14px;">
            <!-- 1. 核心科学问题 -->
            <div class="analysis-section">
              <div class="as-title"><i class="fa-solid fa-circle-question" style="color: var(--accent-science);"></i> 核心研究问题 (Research Question)</div>
              <div class="as-body">{{ readingAnalysis.core_question }}</div>
            </div>

            <!-- 2. 方法论体系 -->
            <div class="analysis-section">
              <div class="as-title"><i class="fa-solid fa-gears" style="color: #a855f7;"></i> 核心方法与技术路线 (Methodology)</div>
              <div class="as-body">{{ readingAnalysis.methodology }}</div>
            </div>

            <!-- 3. 实测结论 -->
            <div class="analysis-section">
              <div class="as-title"><i class="fa-solid fa-square-poll-vertical" style="color: var(--accent-success);"></i> 关键实测结论与证据 (Key Findings)</div>
              <ul class="as-list">
                <li v-for="(kf, idx) in readingAnalysis.key_findings" :key="idx">{{ kf }}</li>
              </ul>
            </div>

            <!-- 4. 局限性与研究空白 -->
            <div class="analysis-section">
              <div class="as-title"><i class="fa-solid fa-triangle-exclamation" style="color: var(--accent-warning);"></i> 局限性与文献空白 (Limitations & Gaps)</div>
              <div class="as-body">{{ readingAnalysis.limitations_and_gaps }}</div>
            </div>

            <!-- 5. 提炼出的科学假说 -->
            <div class="analysis-section" style="border-color: rgba(56, 189, 248, 0.4); background: rgba(56, 189, 248, 0.05);">
              <div class="as-title" style="color: #38bdf8;">
                <i class="fa-solid fa-lightbulb"></i> 提炼出的候选科学假说 (Candidate Hypotheses)
              </div>
              <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 10px;">
                点击「★ 采纳为课题假说」可一键将论文观点转化为待验证的科学假说并在系统中开启实验闭环：
              </div>

              <div style="display: flex; flex-direction: column; gap: 10px;">
                <div v-for="h in readingAnalysis.candidate_hypotheses || []" :key="h.id" class="hyp-candidate-card">
                  <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
                    <strong style="color: var(--text-primary); font-size: 13px;">{{ h.title }}</strong>
                    <button class="btn-action-primary" style="font-size: 11px; padding: 3px 10px;" @click="adoptHypothesis(h)">
                      <i class="fa-solid fa-plus"></i> ★ 采纳为课题假说
                    </button>
                  </div>
                  <div style="font-size: 12px; color: var(--text-primary); line-height: 1.5; margin-bottom: 4px;">
                    {{ h.statement }}
                  </div>
                  <div style="font-size: 11px; color: var(--text-secondary);">
                    <strong>依据:</strong> {{ h.rationale }} | <strong>建议实验:</strong> {{ h.suggested_experiment }}
                  </div>
                </div>
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
      query: '',
      source: 'openalex',
      papers: [],
      savedPapers: [],
      loading: false,
      searched: false,
      directImportText: '',
      directImporting: false,
      uploadingPaper: false,
      manualPaperTitle: '',
      manualPaperText: '',
      activeReadingPaper: null,
      analyzingPaper: false,
      readingAnalysis: null,
    }
  },
  mounted() {
    this.loadSavedPapers()
  },
  methods: {
    triggerFileInput() {
      this.$refs.fileInput?.click()
    },
    async handleFileSelected(e) {
      const file = e.target.files?.[0]
      if (!file) return
      await this.uploadFile(file)
    },
    async handleFileDrop(e) {
      const file = e.dataTransfer?.files?.[0]
      if (!file) return
      await this.uploadFile(file)
    },
    async uploadFile(file) {
      this.uploadingPaper = true
      const reader = new FileReader()
      reader.onload = async () => {
        const base64 = reader.result.split(',')[1]
        try {
          const resp = await fetch(`/api/projects/${this.projectId}/papers/upload`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              filename: file.name,
              content_base64: base64,
            }),
          })
          if (resp.ok) {
            const data = await resp.json()
            alert(this.lang === 'en-US' ? 'Paper uploaded successfully!' : '文献上传并解析成功！即将启动 AI 深度研读...')
            await this.loadSavedPapers()
            this.$emit('refresh')
            // 自动开启深度研读
            if (data.paper) {
              this.openDeepReadingModal(data.paper)
            }
          } else {
            alert('上传失败')
          }
        } catch (err) {
          alert('上传出错: ' + err.message)
        } finally {
          this.uploadingPaper = false
        }
      }
      reader.readAsDataURL(file)
    },
    async handleManualUpload() {
      if (!this.manualPaperText.trim()) return
      this.uploadingPaper = true
      try {
        const resp = await fetch(`/api/projects/${this.projectId}/papers/upload`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            filename: `${this.manualPaperTitle || 'manual_paper'}.txt`,
            text: this.manualPaperText,
          }),
        })
        if (resp.ok) {
          const data = await resp.json()
          alert('文本入库成功！')
          this.manualPaperTitle = ''
          this.manualPaperText = ''
          await this.loadSavedPapers()
          this.$emit('refresh')
          if (data.paper) {
            this.openDeepReadingModal(data.paper)
          }
        }
      } catch (err) {
        alert('提交失败: ' + err.message)
      } finally {
        this.uploadingPaper = false
      }
    },
    fillSamplePaperText() {
      this.manualPaperTitle = 'Dynamic Graph CNN for Learning on Point Clouds'
      this.manualPaperText = `Abstract: Point clouds lack topological information. We propose EdgeConv, a novel operation that acts on graphs dynamically computed in each layer. EdgeConv captures local geometric structure while maintaining permutation invariance. Results show that dynamic edge updates boost robustness under severe point perturbation and noise, outperforming static k-NN baselines with 83.2% accuracy.`
    },
    async openDeepReadingModal(paper) {
      this.activeReadingPaper = paper
      if (paper.reading_analysis) {
        this.readingAnalysis = paper.reading_analysis
        return
      }
      this.analyzingPaper = true
      this.readingAnalysis = null
      try {
        const resp = await fetch(`/api/projects/${this.projectId}/papers/${paper.id || paper.paper_id}/analyze`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        })
        if (resp.ok) {
          const data = await resp.json()
          this.readingAnalysis = data.analysis
          await this.loadSavedPapers()
        }
      } catch (e) {
        alert('研读失败: ' + e.message)
      } finally {
        this.analyzingPaper = false
      }
    },
    async triggerDirectDeepRead(paper) {
      await this.savePaperToProject(paper)
      const target = this.savedPapers.find(p => p.title === paper.title) || paper
      await this.openDeepReadingModal(target)
    },
    async adoptHypothesis(hypothesis) {
      if (!this.activeReadingPaper) return
      try {
        const resp = await fetch(`/api/projects/${this.projectId}/papers/${this.activeReadingPaper.id}/adopt-hypothesis`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ hypothesis }),
        })
        if (resp.ok) {
          alert(`已成功将「${hypothesis.title}」采纳为当前课题科学假说！`)
          this.$emit('refresh')
        } else {
          alert('采纳失败')
        }
      } catch (e) {
        alert('采纳出错: ' + e.message)
      }
    },
    fillSampleBibtex() {
      this.directImportText = `@inproceedings{wang2019dynamic,
  title={Dynamic Graph CNN for Learning on Point Clouds},
  author={Wang, Yue and Sun, Yongbin and Liu, Ziwei and Sarikonda, Sanjay E and Bronstein, Michael M and Solomon, Justin M},
  booktitle={ACM Transactions on Graphics (TOG)},
  year={2019},
  doi={10.1145/3326362}
}`
    },
    fillSampleDoi() {
      this.directImportText = `10.1145/3326362, 10.1038/s41586-020-2649-2`
    },
    async handleDirectImport() {
      if (!this.directImportText.trim()) return
      this.directImporting = true
      try {
        const resp = await fetch(`/api/projects/${this.projectId}/papers/import-direct`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ raw_text: this.directImportText }),
        })
        if (resp.ok) {
          const res = await resp.json()
          alert(this.lang === 'en-US' ? `Successfully imported ${res.saved_count} paper(s)!` : `成功解析并入库 ${res.saved_count} 篇学术文献！`)
          this.directImportText = ''
          this.litTab = 'saved'
          await this.loadSavedPapers()
          this.$emit('refresh')
        } else {
          const err = await resp.json().catch(() => ({}))
          alert('解析导入失败: ' + (err.detail || '未知错误'))
        }
      } catch (e) {
        alert('导入请求出错: ' + e.message)
      } finally {
        this.directImporting = false
      }
    },
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
          await this.loadSavedPapers()
          this.$emit('refresh')
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
        this.$emit('refresh')
      } catch (e) {
        alert('删除失败: ' + e.message)
      }
    },
  },
}
</script>

<style scoped>
.literature-panel { padding: 0; color: var(--text-primary); }
.lit-header { margin-bottom: 20px; }
.lit-title { font-size: 16px; margin: 0 0 6px; color: var(--text-primary); font-weight: 700; }
.lit-desc { color: var(--text-secondary); font-size: 13px; margin: 0; line-height: 1.5; }
.search-box { display: flex; gap: 8px; margin-bottom: 20px; }
.search-input { flex: 1; padding: 8px 12px; border: 1px solid var(--border-default); border-radius: 6px; font-size: 12px; background: var(--bg-surface-2); color: var(--text-primary); outline: none; }
.source-select { border: 1px solid var(--border-default); border-radius: 6px; padding: 8px 12px; font-size: 12px; background: var(--bg-surface-2); color: var(--text-primary); }
.btn-search { background: var(--accent-science); color: #fff; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; }
.empty-hint { color: var(--text-muted); font-size: 13px; text-align: center; padding: 40px 0; font-style: italic; }
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

.upload-dropzone {
  border: 2px dashed var(--border-active);
  border-radius: 10px;
  padding: 36px 20px;
  text-align: center;
  background: var(--bg-surface-2);
  cursor: pointer;
  transition: all 0.2s ease;
}
.upload-dropzone:hover {
  border-color: var(--accent-science);
  background: var(--bg-hover);
}

.analysis-section {
  background: var(--bg-surface-2);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 14px 16px;
}
.as-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.as-body {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
}
.as-list {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
}
.hyp-candidate-card {
  background: var(--bg-surface-1);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  padding: 12px;
}
</style>
