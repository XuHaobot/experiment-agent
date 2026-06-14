<template>
  <div class="workspace-main">
    <!-- 顶部工具栏 -->
    <div class="top-bar">
      <div class="top-bar-left">
        <h1 class="app-title">Experiment Agent</h1>
        <span class="status-badge" v-if="selectedRecord">
          {{ selectedRecord.task || selectedRecord.id }}
        </span>
      </div>
    </div>

    <!-- 新建实验弹窗 -->
    <div v-if="showNewExpDialog" class="modal-overlay" @click.self="showNewExpDialog = false">
      <div class="modal-box">
        <h3>新建实验</h3>
        <input v-model="newExpName" placeholder="实验名称（如：YOLOv8训练调试）" class="modal-input" @keydown.enter="createExperiment" />
        <textarea v-model="newExpDesc" placeholder="实验描述（可选）" class="modal-textarea" rows="2"></textarea>
        <div class="modal-actions">
          <button class="btn-primary" :disabled="!newExpName.trim()" @click="createExperiment">创建</button>
          <button class="btn-secondary" @click="showNewExpDialog = false; newExpName = ''; newExpDesc = ''">取消</button>
        </div>
      </div>
    </div>

    <!-- 删除实验确认弹窗 -->
    <div v-if="pendingDeleteExp" class="modal-overlay" @click.self="pendingDeleteExp = null">
      <div class="modal-box modal-danger">
        <h3>删除实验</h3>
        <p class="modal-msg">确定删除实验「<strong>{{ pendingDeleteExp.name }}</strong>」？</p>
        <p class="modal-sub">实验记录不会被删除，仅取消分组关系。</p>
        <div class="modal-actions">
          <button class="btn-danger" @click="confirmDeleteExperiment">删除</button>
          <button class="btn-secondary" @click="pendingDeleteExp = null">取消</button>
        </div>
      </div>
    </div>

    <!-- 删除记录确认弹窗 -->
    <div v-if="pendingDeleteRecord" class="modal-overlay" @click.self="pendingDeleteRecord = null">
      <div class="modal-box modal-danger">
        <h3>删除实验记录</h3>
        <p class="modal-msg">确定删除记录「<strong>{{ pendingDeleteRecord.task || pendingDeleteRecord.id }}</strong>」？</p>
        <p class="modal-sub">将同时删除关联的报告和图谱，此操作不可恢复。</p>
        <div class="modal-actions">
          <button class="btn-danger" @click="confirmDeleteRecord">删除</button>
          <button class="btn-secondary" @click="pendingDeleteRecord = null">取消</button>
        </div>
      </div>
    </div>

    <!-- 上传记录弹窗 -->
    <div v-if="showUploadDialog" class="modal-overlay" @click.self="closeUploadDialog">
      <div class="modal-box modal-upload">
        <h3>添加记录到「{{ uploadTargetExp?.name }}」</h3>
        <div class="upload-drop" :class="{ drag: isDragging }" @dragover.prevent="isDragging = true" @dragleave="isDragging = false" @drop.prevent="onDrop">
          <label class="upload-label">
            <input type="file" accept=".txt,.md,.json" @change="onFileChange" hidden />
            <span>选择文件或拖拽到此处</span>
          </label>
          <span class="upload-hint">支持 .txt / .md / .json</span>
          <div v-if="uploadFile" class="file-chip">
            <span>{{ uploadFile.name }}</span>
            <button @click="uploadFile = null">✕</button>
          </div>
        </div>
        <textarea v-model="uploadText" class="upload-textarea" placeholder="或粘贴实验日志、聊天记录..." rows="4"></textarea>
        <div v-if="analyzeError" class="analyze-error">{{ analyzeError }}</div>
        <div class="modal-actions">
          <button class="btn-primary" :disabled="analyzing || (!uploadFile && !uploadText.trim())" @click="startAnalysis">
            {{ analyzing ? `分析中... ${analyzeProgress}%` : '开始分析' }}
          </button>
          <button class="btn-secondary" @click="closeUploadDialog" :disabled="analyzing">关闭</button>
        </div>
      </div>
    </div>

    <!-- 三栏布局主体 -->
    <div class="three-col-layout">
      <!-- ========== 左侧栏：实验管理 + 记录列表 ========== -->
      <aside class="col-left">
        <!-- 当前实验指示器 -->
        <div v-if="currentExperiment" class="current-exp-bar">
          <span class="current-exp-label">当前实验</span>
          <span class="current-exp-name">{{ currentExperiment.name }}</span>
          <span class="current-exp-count">{{ currentExperiment.recordCount || 0 }} 条记录</span>
        </div>
        <div v-else class="current-exp-bar empty">
          <span class="current-exp-label">请先选择或新建一个实验</span>
        </div>

        <!-- 实验列表 -->
        <div class="panel-header">
          <h2>实验列表</h2>
          <button class="btn-new-exp-sm" @click="showNewExpDialog = true">+ 新建</button>
        </div>
        <div class="exp-scroll">
          <template v-for="group in experimentsByMonth" :key="group.key">
            <div class="month-header">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="12" height="12"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
              <span>{{ group.label }}</span>
            </div>
            <div
              v-for="exp in group.items"
              :key="exp.id"
              class="exp-card"
              :class="{ active: currentExperiment?.id === exp.id }"
              @click="selectCurrentExperiment(exp)"
            >
              <div class="exp-card-top">
                <span class="exp-card-name">{{ exp.name }}</span>
                <span class="status-tag" :class="getExpStatus(exp)">{{ statusLabel(getExpStatus(exp)) }}</span>
              </div>
              <div class="exp-card-bottom">
                <span class="exp-card-date">{{ formatDate(exp.created_at) }}</span>
                <span class="exp-card-count">{{ exp.recordCount || 0 }} 条记录</span>
                <button class="exp-del-btn" @click.stop="deleteExperiment(exp)" title="删除实验">✕</button>
              </div>
              <!-- 展开时显示记录 -->
              <div v-if="expandedExps.has(exp.id)" class="exp-records">
                <div
                  v-for="r in getRecordsForExp(exp.id)"
                  :key="r.id"
                  class="record-item"
                  :class="{ selected: selectedRecord?.id === r.id }"
                  @click="selectRecord(r)"
                >
                  <div class="record-task">{{ r.task || r.id }}</div>
                  <div class="record-meta">
                    <span v-if="r.dataset" class="chip">{{ truncate(r.dataset, 14) }}</span>
                    <span v-if="r.model" class="chip">{{ r.model }}</span>
                    <span class="chip-date">{{ formatDate(r.created_at) }}</span>
                    <button class="record-del-btn" @click.stop="pendingDeleteRecord = r" title="删除记录">✕</button>
                  </div>
                </div>
                <div v-if="getRecordsForExp(exp.id).length === 0" class="exp-no-records">
                  暂无记录，点击下方按钮上传日志开始分析
                </div>
                <button class="add-record-btn" @click.stop="openUploadDialog(exp)">+ 添加记录</button>
              </div>
            </div>
          </template>
          <div v-if="experiments.length === 0" class="empty-hint">
            暂无实验，点击「+ 新建」创建
          </div>
        </div>
      </aside>

      <!-- ========== 中间栏：AI 对话助手 ========== -->
      <main class="col-center">
        <div class="chat-container">
          <div class="chat-header">
            <div class="chat-header-left">
              <h2>AI 实验研究助手</h2>
              <p class="chat-desc">基于你的实验记录进行智能问答、数据分析和报告生成</p>
            </div>
            <div class="chat-header-actions">
              <div class="session-dropdown" v-if="showSessionList">
                <div class="session-list">
                  <div class="session-list-header">
                    <span>历史对话</span>
                    <button class="session-new-btn" @click="createNewSession" title="新建对话">+ 新对话</button>
                  </div>
                  <div
                    v-for="s in sessionList"
                    :key="s.session_id"
                    class="session-item"
                    :class="{ active: s.session_id === currentSessionId }"
                    @click="switchSession(s.session_id)"
                  >
                    <span class="session-item-title">{{ getSessionTitle(s) }}</span>
                    <span class="session-item-meta">{{ s.turn_count }} 轮 · {{ formatSessionTime(s.last_active) }}</span>
                  </div>
                  <div v-if="!sessionList.length" class="session-empty">暂无历史对话</div>
                </div>
              </div>
              <button class="chat-history-btn" @click="toggleSessionList" :title="showSessionList ? '关闭' : '历史对话'">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                <span v-if="sessionList.length">{{ sessionList.length }}</span>
              </button>
            </div>
          </div>

          <div class="messages-area" ref="messagesArea">
            <div v-for="msg in messages" :key="msg.id" class="msg-row" :class="msg.role === 'user' ? 'msg-user' : 'msg-assistant'">
              <div class="msg-bubble" :class="{ 'is-streaming': msg.streaming }">
                <div class="msg-text" v-html="renderMd(msg.content)"></div>
                <!-- AgentV2 工具调用链 -->
                <details v-if="msg.agentTrace?.length" class="msg-trace">
                  <summary>{{ msg.agentTrace.length }} 步工具调用</summary>
                  <div v-for="(step, si) in msg.agentTrace" :key="si" class="trace-step">
                    <span class="trace-tool">{{ step.tool_name || step.tool || '?' }}</span>
                    <span class="trace-status" :class="step.status">{{ step.status }}</span>
                    <span v-if="step.result_preview" class="trace-result">{{ truncate(String(step.result_preview), 80) }}</span>
                  </div>
                </details>
              </div>
            </div>
            <div v-if="isLoading && !hasStreamingMsg" class="msg-row msg-assistant">
              <div class="msg-bubble typing">
                <span class="dot"></span><span class="dot"></span><span class="dot"></span>
              </div>
            </div>
            <div v-if="messages.length === 0 && !isLoading" class="empty-chat">
              <div class="empty-icon">🧪</div>
              <p>选择左侧实验或直接输入问题开始对话</p>
              <div class="quick-actions">
                <button v-for="qa in quickQuestions" :key="qa" class="quick-btn" @click="sendQuickQuestion(qa)">{{ qa }}</button>
              </div>
            </div>
          </div>

          <div v-if="selectedRecord" class="context-tags">
            <span class="ctx-tag">@{{ selectedRecord.id }}</span>
            <span class="ctx-tag ctx-removable" @click="clearSelection">✕ 移除</span>
            <span class="ctx-hint">当前选中实验将作为对话上下文</span>
          </div>

          <div class="input-area">
            <textarea v-model="userInput" placeholder="输入你的问题... Enter 发送 · Shift+Enter 换行" class="chat-input" rows="3" @keydown.exact.enter.prevent="sendMessage"></textarea>
            <div class="input-toolbar">
              <div class="toolbar-left">
                <button class="tool-btn" @click="handleAction('chart')">生成图表</button>
                <button class="tool-btn" @click="handleAction('compare')">对比分析</button>
                <button class="tool-btn" @click="handleAction('export')">导出报告</button>
              </div>
              <button class="btn-send" :disabled="!userInput.trim() || isLoading" @click="sendMessage">发送</button>
            </div>
          </div>
        </div>
      </main>

      <!-- ========== 右侧栏：图谱 + 详情/操作 ========== -->
      <aside class="col-right">
        <!-- 图谱区域 -->
        <div class="panel-header">
          <h2>图谱预览</h2>
          <div class="graph-header-actions">
            <select v-model="selectedGraphFile" @change="loadGraph" class="graph-select-sm">
              <option value="">选择图谱...</option>
              <option v-for="g in graphList" :key="g.filename" :value="g.filename">{{ g.filename }}</option>
            </select>
            <button v-if="graphData" class="btn-sm" @click="toggleGraphFull">全屏</button>
          </div>
        </div>

        <div class="graph-wrap" ref="graphWrap">
          <KnowledgeGraph v-if="graphData && graphData.entities?.length" :data="graphData" />
          <div v-else-if="graphLoading" class="graph-empty">
            <p>加载图谱中...</p>
          </div>
          <div v-else class="graph-empty">
            <div class="graph-empty-icon">🔗</div>
            <p>实验关系图谱</p>
            <p class="graph-empty-hint">从上方下拉选择已有图谱，或上传分析后自动生成</p>
          </div>
        </div>

        <!-- 详情/操作面板 -->
        <div class="linkage-panel">
          <template v-if="selectedRecord">
            <div class="detail-section-header">
              <h3>实验详情</h3>
              <button class="expand-detail-btn" @click="showDetailFullscreen = true" title="全屏查看">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
                  <polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/>
                  <line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/>
                </svg>
              </button>
            </div>

            <!-- 基本信息卡片 -->
            <div class="link-card active">
              <div class="link-card-title">{{ selectedRecord.task || selectedRecord.id }}</div>
              <div class="detail-meta-row" v-if="recordDetail?.source">
                <span class="detail-label">来源</span><span>{{ recordDetail.source }}</span>
              </div>
              <div class="detail-meta-row" v-if="selectedRecord.dataset">
                <span class="detail-label">数据集</span><span>{{ selectedRecord.dataset }}</span>
              </div>
              <div class="detail-meta-row" v-if="selectedRecord.model">
                <span class="detail-label">模型</span><span>{{ selectedRecord.model }}</span>
              </div>
              <div class="detail-meta-row">
                <span class="detail-label">时间</span><span>{{ formatDate(selectedRecord.created_at) }}</span>
              </div>
            </div>

            <!-- 加载中 -->
            <div v-if="recordDetailLoading" class="detail-loading">加载详情...</div>

            <!-- 分析结果卡片 -->
            <div v-else-if="recordDetail" class="link-card">
              <div class="link-card-title">
                分析结果
                <span class="llm-badge" :class="recordLlmUsed ? 'llm-on' : 'llm-off'">
                  {{ recordLlmUsed ? 'LLM 增强' : '规则抽取' }}
                </span>
              </div>

              <!-- 原始摘要（几乎总是有） -->
              <div v-if="recordDetail.raw_summary" class="detail-block">
                <span class="detail-label">摘要</span>
                <p class="detail-text">{{ recordDetail.raw_summary }}</p>
              </div>

              <!-- 运行命令 -->
              <div v-if="recordDetail.commands?.length" class="detail-block">
                <span class="detail-label">运行命令</span>
                <code v-for="(c, i) in recordDetail.commands.slice(0, 3)" :key="i" class="detail-code">{{ extractText(c) }}</code>
              </div>

              <!-- 参数 -->
              <div v-if="hasAnyParams" class="detail-block">
                <span class="detail-label">参数</span>
                <div v-if="recordDetail.params?.original && Object.keys(recordDetail.params.original).length" class="param-group">
                  <span class="param-layer">原始</span>
                  <span v-for="(v, k) in recordDetail.params.original" :key="k" class="param-chip">{{ k }}={{ v }}</span>
                </div>
                <div v-if="recordDetail.params?.adjusted && Object.keys(recordDetail.params.adjusted).length" class="param-group">
                  <span class="param-layer">调整后</span>
                  <span v-for="(v, k) in recordDetail.params.adjusted" :key="k" class="param-chip adjusted">{{ k }}={{ v }}</span>
                </div>
              </div>

              <!-- 报错 -->
              <div v-if="extractedErrors.length" class="detail-block">
                <span class="detail-label">报错</span>
                <p v-for="(err, i) in extractedErrors" :key="i" class="detail-text error-text">{{ err }}</p>
              </div>

              <!-- 解决方案 -->
              <div v-if="extractedSolutions.length" class="detail-block">
                <span class="detail-label">解决方案</span>
                <p v-for="(sol, i) in extractedSolutions" :key="i" class="detail-text">{{ sol }}</p>
              </div>

              <!-- 结论 -->
              <div v-if="recordDetail.conclusion" class="detail-block">
                <span class="detail-label">结论</span>
                <p class="detail-text">{{ recordDetail.conclusion }}</p>
              </div>

              <!-- 下一步 -->
              <div v-if="recordDetail.next_step" class="detail-block">
                <span class="detail-label">下一步</span>
                <p class="detail-text">{{ recordDetail.next_step }}</p>
              </div>

              <!-- 空状态增强提示 -->
              <div v-if="isRecordEmpty" class="detail-empty-hint">
                该记录结构化信息较少，上传包含训练命令、参数、报错的详细日志可获得更完整的分析
              </div>

              <!-- 分析过程（Agent Trace） -->
              <details v-if="agentTraceSteps.length" class="detail-trace">
                <summary>分析过程（{{ agentTraceSteps.length }} 步）</summary>
                <div v-for="(step, si) in agentTraceSteps" :key="si" class="trace-step">
                  <span class="trace-tool">{{ step.tool }}</span>
                  <span class="trace-status" :class="step.status">{{ step.status === 'success' ? 'success' : step.status === 'deferred' ? 'deferred' : 'error' }}</span>
                  <span v-if="step.detail" class="trace-result">{{ truncate(step.detail, 60) }}</span>
                </div>
              </details>
            </div>

            <!-- 复盘报告卡片 -->
            <div v-if="reportContent" class="link-card">
              <div class="link-card-title">
                复盘报告
                <span class="report-char-count">{{ cleanReport.length }} 字符</span>
              </div>
              <div class="report-preview" v-html="renderMd(reportPreview)"></div>
              <div v-if="cleanReport.length > 600" class="report-more-hint">
                ... 已截断预览，共 {{ cleanReport.length }} 字符
              </div>
            </div>

            <!-- 报告生成中 -->
            <div v-if="reportGenerating" class="link-card report-loading-card">
              <div class="detail-loading">正在生成报告...</div>
            </div>

            <!-- 快速操作 -->
            <div class="link-card actions">
              <div class="link-card-title">快速操作</div>
              <div class="action-btns">
                <button class="act-btn" :disabled="reportGenerating" @click="generateReport">
                  {{ reportGenerating ? '生成中...' : '生成报告' }}
                </button>
                <button class="act-btn" @click="exportReport" :disabled="!reportContent">导出报告</button>
                <button class="act-btn" @click="addToGraph">加入图谱</button>
              </div>
            </div>
          </template>

          <!-- 无选中时 -->
          <template v-else>
            <h3>联动提示</h3>
            <div class="link-card">
              <div class="link-card-title">开始使用</div>
              <div class="link-card-content">从左侧选择一条实验记录查看详情，或上传新文件进行分析</div>
            </div>
            <div class="link-card">
              <div class="link-card-title">工作流程</div>
              <div class="link-card-content">上传日志 → 自动分析 → 查看详情/图谱 → 对话生成报告 → 导出</div>
            </div>
          </template>
        </div>

        <div class="link-status">
          <div class="status-item ok"><span class="status-dot"></span><span>后端已连接</span></div>
          <div class="status-item" :class="records.length ? 'ok' : 'warn'"><span class="status-dot"></span><span>{{ records.length }} 条实验记录</span></div>
        </div>
      </aside>
    </div>

    <!-- 全屏图谱弹窗 -->
    <div v-if="graphFullscreen" class="graph-fullscreen-overlay" @click="graphFullscreen = false">
      <div class="graph-fullscreen-box" @click.stop>
        <div class="graph-fs-header">
          <span>知识图谱 — {{ selectedGraphFile }}</span>
          <button class="btn-sm" @click="graphFullscreen = false">关闭</button>
        </div>
        <div class="graph-fs-body">
          <KnowledgeGraph v-if="graphData" :data="graphData" />
        </div>
      </div>
    </div>

    <!-- 全屏实验详情弹窗 -->
    <div v-if="showDetailFullscreen && selectedRecord" class="detail-fullscreen-overlay" @click.self="showDetailFullscreen = false">
      <div class="detail-fullscreen-box" @click.stop>
        <div class="detail-fs-header">
          <h2>{{ selectedRecord.task || selectedRecord.id }}</h2>
          <button class="btn-secondary" @click="showDetailFullscreen = false">关闭</button>
        </div>

        <!-- 锚点导航 + 搜索 -->
        <div class="detail-fs-nav">
          <div class="fs-nav-pills">
            <button
              v-for="sec in fsSections"
              :key="sec.id"
              class="fs-nav-pill"
              :class="{ active: fsActiveSection === sec.id }"
              @click="scrollToSection(sec.id)"
            >{{ sec.label }}</button>
          </div>
          <div class="fs-nav-search">
            <input
              v-model="fsSearchQuery"
              class="fs-search-input"
              type="text"
              placeholder="搜索关键词..."
              @input="onFsSearch"
              @keydown.enter="jumpToNextMatch"
            />
            <span v-if="fsSearchQuery && fsMatchCount > 0" class="fs-search-info">
              {{ fsMatchIndex + 1 }}/{{ fsMatchCount }}
              <button class="fs-search-arrow" @click="jumpToPrevMatch" title="上一个">&#8249;</button>
              <button class="fs-search-arrow" @click="jumpToNextMatch" title="下一个">&#8250;</button>
            </span>
            <span v-else-if="fsSearchQuery && fsMatchCount === 0" class="fs-search-info fs-no-match">无匹配</span>
          </div>
        </div>

        <div class="detail-fs-body" ref="fsBodyRef">
          <!-- 基本信息 -->
          <section class="fs-section" id="fs-basic">
            <h3 class="fs-section-title">基本信息</h3>
            <div class="fs-meta-grid">
              <div v-if="recordDetail?.source" class="fs-meta-item">
                <span class="detail-label">来源</span>
                <span>{{ recordDetail.source }}</span>
              </div>
              <div v-if="selectedRecord.dataset" class="fs-meta-item">
                <span class="detail-label">数据集</span>
                <span>{{ selectedRecord.dataset }}</span>
              </div>
              <div v-if="selectedRecord.model" class="fs-meta-item">
                <span class="detail-label">模型</span>
                <span>{{ selectedRecord.model }}</span>
              </div>
              <div class="fs-meta-item">
                <span class="detail-label">时间</span>
                <span>{{ formatDate(selectedRecord.created_at) }}</span>
              </div>
              <div class="fs-meta-item">
                <span class="detail-label">分析方式</span>
                <span class="llm-badge" :class="recordLlmUsed ? 'llm-on' : 'llm-off'">{{ recordLlmUsed ? 'LLM 增强' : '规则抽取' }}</span>
              </div>
            </div>
          </section>

          <!-- 分析结果 -->
          <section class="fs-section" id="fs-analysis">
            <h3 class="fs-section-title">分析结果</h3>

            <div v-if="recordDetail?.raw_summary" class="fs-field">
              <span class="detail-label">摘要</span>
              <p>{{ recordDetail.raw_summary }}</p>
            </div>

            <div v-if="recordDetail?.commands?.length" class="fs-field">
              <span class="detail-label">运行命令</span>
              <div class="fs-code-list">
                <code v-for="(c, i) in recordDetail.commands" :key="i">{{ extractText(c) }}</code>
              </div>
            </div>

            <div v-if="hasAnyParams" class="fs-field">
              <span class="detail-label">参数</span>
              <div v-if="recordDetail.params?.original && Object.keys(recordDetail.params.original).length" class="param-group">
                <span class="param-layer">原始</span>
                <span v-for="(v, k) in recordDetail.params.original" :key="k" class="param-chip">{{ k }}={{ v }}</span>
              </div>
              <div v-if="recordDetail.params?.adjusted && Object.keys(recordDetail.params.adjusted).length" class="param-group">
                <span class="param-layer">调整后</span>
                <span v-for="(v, k) in recordDetail.params.adjusted" :key="k" class="param-chip adjusted">{{ k }}={{ v }}</span>
              </div>
            </div>

            <div v-if="extractedErrors.length" class="fs-field">
              <span class="detail-label">报错</span>
              <p v-for="(err, i) in extractedErrors" :key="i" class="detail-text error-text">{{ err }}</p>
            </div>

            <div v-if="extractedSolutions.length" class="fs-field">
              <span class="detail-label">解决方案</span>
              <p v-for="(sol, i) in extractedSolutions" :key="i">{{ sol }}</p>
            </div>

            <div v-if="recordDetail?.conclusion" class="fs-field">
              <span class="detail-label">结论</span>
              <p>{{ recordDetail.conclusion }}</p>
            </div>

            <div v-if="recordDetail?.next_step" class="fs-field">
              <span class="detail-label">下一步</span>
              <p>{{ recordDetail.next_step }}</p>
            </div>

            <div v-if="isRecordEmpty" class="fs-empty-hint">
              该记录结构化信息较少，上传包含训练命令、参数、报错的详细日志可获得更完整的分析
            </div>
          </section>

          <!-- 分析过程 -->
          <section v-if="agentTraceSteps.length" class="fs-section" id="fs-trace">
            <h3 class="fs-section-title">分析过程（{{ agentTraceSteps.length }} 步）</h3>
            <div class="fs-trace-list">
              <div v-for="(step, si) in agentTraceSteps" :key="si" class="fs-trace-item">
                <span class="fs-trace-idx">{{ si + 1 }}</span>
                <span class="trace-tool">{{ step.tool }}</span>
                <span class="trace-status" :class="step.status">{{ step.status }}</span>
                <span v-if="step.detail" class="fs-trace-detail">{{ step.detail }}</span>
              </div>
            </div>
          </section>

          <!-- 复盘报告 -->
          <section v-if="reportContent" class="fs-section" id="fs-report">
            <h3 class="fs-section-title">
              复盘报告
              <span class="report-char-count">{{ cleanReport.length }} 字符</span>
            </h3>
            <div class="fs-report-body" v-html="renderMd(cleanReport)"></div>
          </section>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { marked } from 'marked'
import { api } from '../api/client'
import KnowledgeGraph from '../components/KnowledgeGraph.vue'

// ========== marked 配置 ==========
marked.setOptions({ breaks: true, gfm: true })

// ========== 状态 ==========
const records = ref([])
const searchQuery = ref('')
const selectedRecord = ref(null)
const messages = ref([])
const userInput = ref('')

// ========== 会话管理 ==========
const currentSessionId = ref('workspace-main-session')
const sessionList = ref([])
const showSessionList = ref(false)
const isLoading = ref(false)
const graphData = ref(null)
const messagesArea = ref(null)

// 上传
const uploadFile = ref(null)
const uploadText = ref('')
const isDragging = ref(false)
const analyzing = ref(false)
const analyzeProgress = ref(0)
const analyzeError = ref('')
const showUploadDialog = ref(false)
const uploadTargetExp = ref(null)  // 弹窗对应的目标实验

// 图谱
const graphList = ref([])
const selectedGraphFile = ref('')
const graphLoading = ref(false)
const graphFullscreen = ref(false)

// 详情 & 报告
const recordDetail = ref(null)
const recordDetailLoading = ref(false)
const reportContent = ref('')
const reportGenerating = ref(false)
const showDetailFullscreen = ref(false)

// 关闭弹窗时重置搜索状态
watch(showDetailFullscreen, (val) => {
  if (!val) {
    fsSearchQuery.value = ''
    clearFsHighlights()
    fsMatchCount.value = 0
    fsMatchIndex.value = 0
    fsActiveSection.value = 'fs-basic'
  }
})

// 新建实验
const showNewExpDialog = ref(false)
const newExpName = ref('')
const newExpDesc = ref('')

// 实验分组管理
const experiments = ref([])          // 所有实验列表（含 recordCount）
const currentExperiment = ref(null)  // 当前选中的实验分组
const expandedExps = ref(new Set())  // 展开的实验 ID 集合
const pendingDeleteExp = ref(null)   // 待删除的实验（控制弹窗）
const pendingDeleteRecord = ref(null) // 待删除的记录（控制弹窗）
const analyzingExpId = ref(null)     // 正在分析中的实验 ID（用于"进行中"状态）

const quickQuestions = [
  '有哪些实验报过错？',
  '对比最近几次实验的参数差异',
  '总结所有训练实验的结果',
]

// ========== 计算属性 ==========

/** 扩展搜索范围 */
const filteredRecords = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()
  if (!q) return records.value
  return records.value.filter(r => {
    const hay = [r.task, r.id, r.dataset, r.model, r.filename, r.source]
      .filter(Boolean).join(' ').toLowerCase()
    return hay.includes(q)
  })
})

/** 实验按月份分组（最新月份在前） */
const experimentsByMonth = computed(() => {
  const groups = new Map()
  for (const exp of experiments.value) {
    const d = exp.created_at ? new Date(exp.created_at) : new Date()
    if (isNaN(d.getTime())) {
      const key = 'unknown'
      if (!groups.has(key)) groups.set(key, { key, label: '未知日期', items: [] })
      groups.get(key).items.push(exp)
      continue
    }
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    if (!groups.has(key)) {
      groups.set(key, { key, label: `${d.getFullYear()}年${d.getMonth() + 1}月`, items: [] })
    }
    groups.get(key).items.push(exp)
  }
  return [...groups.values()].sort((a, b) => b.key.localeCompare(a.key))
})

/** 从报告中去除 Section 7 "Agent 分析过程" */
const cleanReport = computed(() => {
  if (!reportContent.value) return ''
  // 报告 Section 7 标题是 "## 7. Agent 分析过程" 或类似
  const idx = reportContent.value.search(/##\s*7\.\s*Agent/i)
  if (idx === -1) return reportContent.value
  return reportContent.value.slice(0, idx).trim()
})

/** 报告预览：取前 600 字符 */
const reportPreview = computed(() => {
  const text = cleanReport.value
  if (text.length <= 600) return text
  // 尝试在句子边界截断
  const cut = text.slice(0, 600)
  const lastBreak = cut.lastIndexOf('\n')
  if (lastBreak > 300) return cut.slice(0, lastBreak)
  return cut
})

/** 判断记录是否几乎所有字段为空 */
const isRecordEmpty = computed(() => {
  const d = recordDetail.value
  if (!d) return false
  return !d.commands?.length
    && !d.errors?.length
    && !d.solutions?.length
    && !d.conclusion
    && !d.next_step
    && !hasAnyParams.value
})

/** 从 recordDetail 中提取 agent trace 步骤 */
const agentTraceSteps = computed(() => {
  return recordDetail.value?.agent_trace?.steps || []
})

/** 记录是否使用了 LLM */
const recordLlmUsed = computed(() => {
  return recordDetail.value?.metadata?.llm_used || false
})

/** 当前是否有正在流式输出的消息 */
const hasStreamingMsg = computed(() => {
  return messages.value.some(m => m.streaming)
})

// ========== 全屏详情弹窗：锚点导航 & 搜索 ==========

const fsBodyRef = ref(null)
const fsActiveSection = ref('fs-basic')
const fsSearchQuery = ref('')
const fsMatchCount = ref(0)
const fsMatchIndex = ref(0)
let _fsHighlights = [] // 当前高亮的 DOM 节点列表

/** 动态可见的 section 列表 */
const fsSections = computed(() => {
  const list = [
    { id: 'fs-basic', label: '基本信息' },
    { id: 'fs-analysis', label: '分析结果' },
  ]
  if (agentTraceSteps.value.length) {
    list.push({ id: 'fs-trace', label: `分析过程(${agentTraceSteps.value.length})` })
  }
  if (reportContent.value) {
    list.push({ id: 'fs-report', label: '复盘报告' })
  }
  return list
})

function scrollToSection(id) {
  fsActiveSection.value = id
  const el = document.getElementById(id)
  if (el && fsBodyRef.value) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

/** 搜索：在 .detail-fs-body 内高亮匹配文本 */
function onFsSearch() {
  const q = fsSearchQuery.value.trim()
  clearFsHighlights()
  if (!q || !fsBodyRef.value) {
    fsMatchCount.value = 0
    fsMatchIndex.value = 0
    return
  }
  // 遍历所有文本节点，包装匹配文字为 <mark>
  const body = fsBodyRef.value
  const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      // 跳过 script/style/mark 内部的节点
      const parent = node.parentElement
      if (!parent) return NodeFilter.FILTER_REJECT
      const tag = parent.tagName
      if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'MARK' || tag === 'INPUT') return NodeFilter.FILTER_REJECT
      return NodeFilter.FILTER_ACCEPT
    }
  })

  const lowerQ = q.toLowerCase()
  const textNodes = []
  while (walker.nextNode()) textNodes.push(walker.currentNode)

  let count = 0
  _fsHighlights = []

  for (const textNode of textNodes) {
    const text = textNode.textContent
    const lowerText = text.toLowerCase()
    let idx = lowerText.indexOf(lowerQ)
    if (idx === -1) continue

    const frag = document.createDocumentFragment()
    let lastIdx = 0
    while (idx !== -1) {
      // 前面的普通文本
      if (idx > lastIdx) {
        frag.appendChild(document.createTextNode(text.slice(lastIdx, idx)))
      }
      // 匹配的 mark
      const mark = document.createElement('mark')
      mark.className = 'fs-hl'
      mark.textContent = text.slice(idx, idx + q.length)
      frag.appendChild(mark)
      _fsHighlights.push(mark)
      count++
      lastIdx = idx + q.length
      idx = lowerText.indexOf(lowerQ, lastIdx)
    }
    // 剩余文本
    if (lastIdx < text.length) {
      frag.appendChild(document.createTextNode(text.slice(lastIdx)))
    }
    textNode.parentNode.replaceChild(frag, textNode)
  }

  fsMatchCount.value = count
  fsMatchIndex.value = count > 0 ? 0 : 0
  if (count > 0) {
    _highlightActive()
  }
}

function clearFsHighlights() {
  // 把 <mark> 替换回纯文本
  const body = fsBodyRef.value
  if (!body) return
  const marks = body.querySelectorAll('mark.fs-hl')
  marks.forEach(m => {
    const text = document.createTextNode(m.textContent)
    m.parentNode.replaceChild(text, m)
  })
  // 合并相邻文本节点
  body.normalize()
  _fsHighlights = []
}

function _highlightActive() {
  // 移除旧激活
  const body = fsBodyRef.value
  if (body) {
    body.querySelectorAll('mark.fs-hl-active').forEach(m => m.classList.remove('fs-hl-active'))
  }
  const idx = fsMatchIndex.value
  if (idx >= 0 && idx < _fsHighlights.length) {
    const mark = _fsHighlights[idx]
    mark.classList.add('fs-hl-active')
    mark.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

function jumpToNextMatch() {
  if (fsMatchCount.value === 0) return
  fsMatchIndex.value = (fsMatchIndex.value + 1) % fsMatchCount.value
  _highlightActive()
}

function jumpToPrevMatch() {
  if (fsMatchCount.value === 0) return
  fsMatchIndex.value = (fsMatchIndex.value - 1 + fsMatchCount.value) % fsMatchCount.value
  _highlightActive()
}

/** 是否有任何参数 */
const hasAnyParams = computed(() => {
  const p = recordDetail.value?.params
  if (!p) return false
  return Object.keys(p.original || {}).length > 0
    || Object.keys(p.adjusted || {}).length > 0
    || Object.keys(p.suggested || {}).length > 0
})

/** 提取报错文本 */
const extractedErrors = computed(() => {
  const d = recordDetail.value
  if (!d?.errors?.length) return []
  return d.errors.map(e => typeof e === 'string' ? e : (e.message || e.raw || JSON.stringify(e)))
})

/** 提取解决方案文本 */
const extractedSolutions = computed(() => {
  const d = recordDetail.value
  if (!d?.solutions?.length) return []
  return d.solutions.map(s => typeof s === 'string' ? s : (s.message || s.raw || JSON.stringify(s)))
})

// ========== 状态系统 ==========

/** 判断实验状态 */
function getExpStatus(exp) {
  if (analyzingExpId.value === exp.id) return 'running'
  if ((exp.recordCount || 0) > 0) return 'done'
  return 'pending'
}

/** 状态中文标签 */
function statusLabel(status) {
  return { pending: '待开始', running: '进行中', done: '完成', failed: '失败', paused: '已暂停' }[status] || status
}

// ========== 工具函数 ==========

function renderMd(text) {
  if (!text) return ''
  try { return marked.parse(text) } catch { return text }
}

function extractText(item) {
  if (!item) return ''
  return typeof item === 'string' ? item : (item.message || item.raw || JSON.stringify(item))
}

function truncate(str, max) {
  if (!str) return ''
  return str.length > max ? str.slice(0, max) + '...' : str
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return ''
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function scrollToBottom() {
  if (messagesArea.value) messagesArea.value.scrollTop = messagesArea.value.scrollHeight
}

/**
 * 在图谱列表中查找与给定 record ID 匹配的图谱文件。
 * 匹配逻辑：图谱文件名包含 record ID 中的时间戳部分（前 15 字符，如 20260612-150207）
 */
function findMatchingGraph(recordId) {
  if (!recordId || !graphList.value.length) return null
  // record ID 格式: YYYYMMDD-HHMMSS-xxxxx，取前 15 字符作为时间戳
  const ts = recordId.slice(0, 15)
  if (ts.length < 8) return null
  return graphList.value.find(g => g.filename.includes(ts)) || null
}

// ========== 数据加载 ==========

async function fetchRecords() {
  try {
    const res = await api.getRecords()
    records.value = res?.records || []
  } catch (e) {
    console.error('获取实验记录失败:', e)
  }
}

async function fetchExperiments() {
  try {
    const res = await api.getExperiments()
    experiments.value = res?.experiments || []
    // 同步 currentExperiment 引用
    if (currentExperiment.value) {
      const updated = experiments.value.find(e => e.id === currentExperiment.value.id)
      currentExperiment.value = updated || null
    }
  } catch (e) {
    console.error('获取实验列表失败:', e)
  }
}

async function fetchGraphList() {
  try {
    const res = await api.getGraphList()
    graphList.value = res?.graphs || []
  } catch (e) {
    console.error('获取图谱列表失败:', e)
  }
}

/** 从后端恢复历史对话记录 */
async function fetchChatHistory(sessionId = null) {
  const sid = sessionId || currentSessionId.value
  try {
    const res = await api.getSessionHistory(sid)
    if (!res?.history?.length) {
      messages.value = []
      return
    }
    const restored = res.history
      .filter(t => t.role === 'user' || t.role === 'assistant')
      .map((t, i) => ({
        id: `msg-restored-${i}`,
        role: t.role,
        content: t.content,
        agentTrace: t.agent_trace || [],
      }))
    messages.value = restored
    await nextTick()
    scrollToBottom()
  } catch (e) {
    // 会话不存在，静默
    messages.value = []
  }
}

/** 拉取会话列表 */
async function fetchSessionList() {
  try {
    const res = await api.getSessions()
    sessionList.value = (res?.sessions || [])
      .filter(s => s.turn_count > 0)
      .sort((a, b) => b.last_active - a.last_active)
  } catch (e) {
    console.error('获取会话列表失败:', e)
  }
}

/** 切换会话 */
async function switchSession(sessionId) {
  currentSessionId.value = sessionId
  showSessionList.value = false
  await fetchChatHistory(sessionId)
}

/** 新建对话 */
async function createNewSession() {
  // 用空 session_id 让后端自动创建新会话
  currentSessionId.value = ''  // 触发 sendMessage 创建新会话
  messages.value = []
  showSessionList.value = false
  // 通过发一个隐藏请求来让后端分配新 session_id
  // 或者直接用 null 让下次 sendMessage 自动创建
  currentSessionId.value = '__new__'
}

/** 会话标题：取第一条用户消息的前 20 字 */
function getSessionTitle(s) {
  if (s.session_id === currentSessionId.value && messages.value.length) {
    const first = messages.value.find(m => m.role === 'user')
    if (first) return first.content.slice(0, 24) + (first.content.length > 24 ? '...' : '')
  }
  // 对于非当前会话，用 ID 缩短显示
  return s.session_id.replace('session-', '对话 ')
}

function formatSessionTime(ts) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  const now = new Date()
  const diffMs = now - d
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin} 分钟前`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour} 小时前`
  const diffDay = Math.floor(diffHour / 24)
  if (diffDay < 7) return `${diffDay} 天前`
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function toggleSessionList() {
  showSessionList.value = !showSessionList.value
  if (showSessionList.value) fetchSessionList()
}

/** 获取某个实验下的记录列表 */
function getRecordsForExp(expId) {
  const exp = experiments.value.find(e => e.id === expId)
  if (!exp?.record_ids?.length) return []
  const idSet = new Set(exp.record_ids)
  return records.value.filter(r => idSet.has(r.id))
}

async function loadGraph() {
  if (!selectedGraphFile.value) { graphData.value = null; return }
  graphLoading.value = true
  try {
    graphData.value = await api.getGraph(selectedGraphFile.value)
  } catch (e) {
    console.error('加载图谱失败:', e)
    graphData.value = null
  } finally {
    graphLoading.value = false
  }
}


// ========== 实验分组管理 ==========

function selectCurrentExperiment(exp) {
  // 切换选中
  if (currentExperiment.value?.id === exp.id) {
    // 再次点击 → 展开/折叠
    if (expandedExps.value.has(exp.id)) {
      expandedExps.value.delete(exp.id)
    } else {
      expandedExps.value.add(exp.id)
    }
    return
  }
  currentExperiment.value = exp
  expandedExps.value.add(exp.id)
  // 清除之前选中的记录
  clearSelection()
}

function deleteExperiment(exp) {
  pendingDeleteExp.value = exp
}

async function confirmDeleteExperiment() {
  const exp = pendingDeleteExp.value
  if (!exp) return
  pendingDeleteExp.value = null
  try {
    await api.deleteExperiment(exp.id)
    if (currentExperiment.value?.id === exp.id) {
      currentExperiment.value = null
    }
    expandedExps.value.delete(exp.id)
    await fetchExperiments()
  } catch (e) {
    console.error('删除实验失败:', e)
  }
}

async function confirmDeleteRecord() {
  const rec = pendingDeleteRecord.value
  if (!rec) return
  pendingDeleteRecord.value = null
  try {
    await api.deleteRecord(rec.id)
    // 如果删除的是当前选中的记录，清空详情
    if (selectedRecord.value?.id === rec.id) {
      clearSelection()
    }
    // 刷新记录和实验列表
    await Promise.all([fetchRecords(), fetchExperiments(), fetchGraphList()])
  } catch (e) {
    console.error('删除记录失败:', e)
  }
}

/** 将记录关联到指定实验 */
async function addRecordToExperiment(recordId, expId) {
  try {
    await api.addRecordToExperiment(recordId, expId)
    await fetchExperiments() // 刷新 recordCount
  } catch (e) {
    console.error('关联记录到实验失败:', e)
  }
}

// ========== 选中实验 → 加载详情 + 报告 + 图谱 ==========

async function selectRecord(r) {
  selectedRecord.value = r
  recordDetail.value = null
  reportContent.value = ''

  recordDetailLoading.value = true
  try {
    const res = await api.getRecord(r.id)
    if (res?.record) {
      recordDetail.value = res.record
      reportContent.value = res.report || ''
    }
  } catch (e) {
    console.error('加载详情失败:', e)
  } finally {
    recordDetailLoading.value = false
  }

  // 自动加载关联图谱
  const match = findMatchingGraph(r.id)
  if (match) {
    selectedGraphFile.value = match.filename
    loadGraph()
  }
}

function clearSelection() {
  selectedRecord.value = null
  recordDetail.value = null
  reportContent.value = ''
}

// ========== 上传弹窗控制 ==========

function openUploadDialog(exp) {
  uploadTargetExp.value = exp
  uploadFile.value = null
  uploadText.value = ''
  analyzeError.value = ''
  showUploadDialog.value = true
}

function closeUploadDialog() {
  if (analyzing.value) return
  showUploadDialog.value = false
  uploadFile.value = null
  uploadText.value = ''
  analyzeError.value = ''
}

// ========== 上传分析 ==========

function onFileChange(e) {
  uploadFile.value = e.target.files[0] || null
  if (uploadFile.value) uploadText.value = ''
}

function onDrop(e) {
  isDragging.value = false
  const f = e.dataTransfer.files[0]
  if (f) { uploadFile.value = f; uploadText.value = '' }
}

async function startAnalysis() {
  if (!uploadFile.value && !uploadText.value.trim()) {
    analyzeError.value = '请上传文件或粘贴文本'
    return
  }
  analyzing.value = true
  analyzeError.value = ''
  analyzeProgress.value = 10
  // 标记目标实验为"进行中"
  if (uploadTargetExp.value) {
    analyzingExpId.value = uploadTargetExp.value.id
  }

  try {
    let result
    if (uploadFile.value) {
      analyzeProgress.value = 30
      result = await api.analyzeFile(uploadFile.value)
    } else {
      analyzeProgress.value = 30
      result = await api.analyzeText(uploadText.value)
    }
    analyzeProgress.value = 90

    // 刷新列表
    await Promise.all([fetchRecords(), fetchGraphList()])
    analyzeProgress.value = 100

    // 自动选中新记录（直接使用 analyze 返回的数据，避免额外 API 调用）
    if (result?.record?.id) {
      const rec = result.record
      selectedRecord.value = {
        id: rec.id,
        task: rec.task || '',
        dataset: rec.dataset || '',
        model: rec.model || '',
        created_at: rec.created_at || '',
      }
      recordDetail.value = rec
      reportContent.value = result.report || ''

      // 直接使用 analyze 返回的图谱数据（避免额外 API 调用）
      if (result.graph?.entities?.length) {
        graphData.value = result.graph
      }

      // 同时尝试从列表匹配图谱文件（用于下拉选择器）
      const match = findMatchingGraph(rec.id)
      if (match) {
        selectedGraphFile.value = match.filename
      }

      // 将记录关联到目标实验
      if (uploadTargetExp.value) {
        await addRecordToExperiment(rec.id, uploadTargetExp.value.id)
      }
    }

    // 清空输入并关闭弹窗
    uploadFile.value = null
    uploadText.value = ''
    showUploadDialog.value = false
  } catch (e) {
    analyzeError.value = e.message || '分析失败，请重试'
    console.error('[startAnalysis]', e)
  } finally {
    analyzing.value = false
    analyzingExpId.value = null
    setTimeout(() => { analyzeProgress.value = 0 }, 600)
  }
}

// ========== 新建实验 ==========

async function createExperiment() {
  if (!newExpName.value.trim()) return
  try {
    const res = await api.createExperiment(newExpName.value.trim(), newExpDesc.value.trim(), new Date().toISOString())
    newExpName.value = ''
    newExpDesc.value = ''
    showNewExpDialog.value = false
    // 刷新实验列表并自动选中新建的实验
    await fetchExperiments()
    if (res?.experiment) {
      const newExp = experiments.value.find(e => e.id === res.experiment.id)
      if (newExp) {
        currentExperiment.value = newExp
        expandedExps.value.add(newExp.id)
      }
    }
  } catch (e) {
    console.error('创建实验失败:', e)
  }
}

// ========== 对话功能 ==========

/**
 * 发送消息。
 * @param {Object} [opts]
 * @param {boolean} opts.silent - true 时不将回复推入聊天列表（用于静默生成报告）
 * @returns {Promise<string>} 回复文本
 */
async function sendMessage(opts = {}) {
  const text = userInput.value.trim()
  if (!text || isLoading.value) return ''

  // 显示用户原始消息（不含上下文注入）
  messages.value.push({ id: `msg-${Date.now()}`, role: 'user', content: text })
  userInput.value = ''
  await nextTick()
  scrollToBottom()

  // 如果有选中实验，注入上下文到发送给后端的文本中
  let questionForAPI = text
  if (selectedRecord.value) {
    const exp = selectedRecord.value
    questionForAPI = `[当前选中实验: ${exp.task || exp.id}]\n${text}`
  }

  isLoading.value = true
  let replyText = ''
  const agentTraceSteps = []

  // 新建会话时传 null，后端会自动创建并返回新 session_id
  const sidForApi = currentSessionId.value === '__new__' ? null : currentSessionId.value

  try {
    const reader = await api.chatStream(
      questionForAPI,
      sidForApi,
    )

    // 立即创建助手消息占位（内容逐步填充）
    const msgId = `msg-${Date.now()}-resp`
    if (!opts.silent) {
      messages.value.push({
        id: msgId,
        role: 'assistant',
        content: '',
        agentTrace: [],
        streaming: true,
      })
    }

    // 读取 SSE 流
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // 保留未完成的行

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const dataStr = line.slice(6).trim()
        if (dataStr === '[DONE]') continue

        try {
          const event = JSON.parse(dataStr)
          if (event.type === 'session_id') {
            // 新建会话时后端返回分配的 session_id
            if (currentSessionId.value === '__new__' || !currentSessionId.value) {
              currentSessionId.value = event.session_id
            }
          } else if (event.type === 'trace') {
            agentTraceSteps.push(event.step)
            if (!opts.silent) {
              const msg = messages.value.find(m => m.id === msgId)
              if (msg) msg.agentTrace = [...agentTraceSteps]
            }
          } else if (event.type === 'token') {
            replyText += event.token
            if (!opts.silent) {
              const msg = messages.value.find(m => m.id === msgId)
              if (msg) msg.content = replyText
              await nextTick()
              scrollToBottom()
            }
          } else if (event.type === 'answer') {
            // 最终完整回答（兜底，若 token 流已覆盖则内容一致）
            if (!replyText) {
              replyText = event.answer || ''
            }
          }
        } catch (e) {
          // JSON 解析失败，跳过此行
        }
      }
    }

    // 流结束，标记完成
    if (!opts.silent) {
      const msg = messages.value.find(m => m.id === msgId)
      if (msg) {
        msg.content = replyText || '（无回复内容）'
        msg.streaming = false
      }
    } else {
      // silent 模式下也需要拿到回复文本
      replyText = replyText || ''
    }
  } catch (e) {
    console.error('发送消息失败:', e)
    if (!opts.silent) {
      messages.value.push({
        id: `msg-${Date.now()}-err`,
        role: 'assistant',
        content: '抱歉，请求出错，请稍后重试。',
      })
    }
  } finally {
    isLoading.value = false
    await nextTick()
    scrollToBottom()
  }
  return replyText
}

function sendQuickQuestion(q) {
  userInput.value = q
  sendMessage()
}

function handleAction(key) {
  const actions = {
    chart() {
      userInput.value = selectedRecord.value
        ? `请为实验 ${selectedRecord.value.task || selectedRecord.value.id} 生成训练曲线分析`
        : '请为当前实验生成训练曲线图表'
      sendMessage()
    },
    compare() {
      userInput.value = '对比最近三次实验的关键参数和结果差异'
      sendMessage()
    },
    async export() {
      if (reportContent.value) {
        exportReport()
      } else {
        userInput.value = selectedRecord.value
          ? `请为实验 ${selectedRecord.value.task || selectedRecord.value.id} 生成完整的分析报告`
          : '请导出当前实验的完整分析报告'
        // 静默生成，回复写入右栏报告卡片
        reportGenerating.value = true
        try {
          const reply = await sendMessage({ silent: true })
          if (reply) reportContent.value = reply
        } finally {
          reportGenerating.value = false
        }
      }
    },
  }
  if (actions[key]) {
    const result = actions[key]()
    if (result && typeof result.catch === 'function') {
      result.catch(e => console.error('[handleAction]', e))
    }
  }
}

// ========== 快速操作（右栏按钮） ==========

/**
 * 生成报告：发送消息，将回复直接写入右栏报告卡片（不显示在聊天中）。
 */
async function generateReport() {
  if (!selectedRecord.value || reportGenerating.value) return
  reportGenerating.value = true
  userInput.value = `请为实验 ${selectedRecord.value.task || selectedRecord.value.id} 生成完整的复盘报告`
  try {
    const reply = await sendMessage({ silent: true })
    if (reply) {
      reportContent.value = reply
    } else {
      // 生成失败时给一个可见的提示
      reportContent.value = ''
      messages.value.push({
        id: `msg-${Date.now()}-warn`,
        role: 'assistant',
        content: '报告生成失败，请稍后重试。',
      })
    }
  } finally {
    reportGenerating.value = false
  }
}

function exportReport() {
  const content = cleanReport.value || reportContent.value
  if (!content) return
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `report-${selectedRecord.value?.id || 'export'}.md`
  a.click()
  URL.revokeObjectURL(url)
}

function addToGraph() {
  if (!selectedRecord.value) return
  const r = selectedRecord.value
  const match = findMatchingGraph(r.id)
  if (match) {
    selectedGraphFile.value = match.filename
    loadGraph()
  } else {
    messages.value.push({
      id: `msg-${Date.now()}-info`,
      role: 'assistant',
      content: `实验 ${r.task || r.id} 暂未生成知识图谱。上传分析实验记录后会自动生成图谱。`,
    })
    nextTick(scrollToBottom)
  }
}

function toggleGraphFull() {
  graphFullscreen.value = !graphFullscreen.value
}

// ========== 生命周期 ==========

onMounted(() => {
  fetchRecords()
  fetchGraphList()
  fetchExperiments()
  fetchSessionList()
  fetchChatHistory()
  // 点击外部关闭会话列表
  document.addEventListener('click', _closeSessionListOnOutsideClick)
})

onUnmounted(() => {
  document.removeEventListener('click', _closeSessionListOnOutsideClick)
})

function _closeSessionListOnOutsideClick(e) {
  if (!showSessionList.value) return
  const dropdown = document.querySelector('.session-dropdown')
  const btn = document.querySelector('.chat-history-btn')
  if (dropdown && !dropdown.contains(e.target) && btn && !btn.contains(e.target)) {
    showSessionList.value = false
  }
}

watch(messages, () => { nextTick(scrollToBottom) }, { deep: true })
</script>

<style scoped>
.workspace-main { display: flex; flex-direction: column; height: 100vh; background: var(--bg-primary, #F4F4F6); color: var(--text-primary, rgba(0,0,0,.8)); font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; overflow: hidden; }

/* ---- 弹窗 ---- */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.3); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal-box { background: var(--panel-bg, #FEFDFC); border-radius: 14px; padding: 20px 24px; width: 380px; box-shadow: 0 12px 40px rgba(0,0,0,.15); }
.modal-box h3 { font-size: 15px; font-weight: 600; margin: 0 0 14px; }
.modal-input { width: 100%; padding: 8px 12px; border: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); border-radius: 8px; font-size: 13px; background: var(--bg-secondary, rgba(0,0,0,.04)); outline: none; margin-bottom: 8px; box-sizing: border-box; }
.modal-input:focus { border-color: #F3A04C; }
.modal-textarea { width: 100%; padding: 8px 12px; border: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); border-radius: 8px; font-size: 13px; background: var(--bg-secondary, rgba(0,0,0,.04)); outline: none; resize: vertical; font-family: inherit; margin-bottom: 12px; box-sizing: border-box; }
.modal-textarea:focus { border-color: #F3A04C; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; }
.modal-danger { border-top: 3px solid #E65C53; }
.modal-msg { font-size: 13px; color: var(--text-primary, rgba(0,0,0,.8)); margin-bottom: 4px; line-height: 1.6; }
.modal-msg strong { color: #E65C53; }
.modal-sub { font-size: 12px; color: var(--text-secondary, rgba(0,0,0,.5)); margin-bottom: 16px; }
.btn-danger { padding: 7px 16px; border: none; border-radius: 10px; background: #E65C53; color: #fff; font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-danger:hover { background: #D14B42; }

/* ---- 顶部 ---- */
.top-bar { display: flex; justify-content: space-between; align-items: center; padding: 12px 20px; border-bottom: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); background: var(--panel-bg, #FEFDFC); flex-shrink: 0; }
.top-bar-left { display: flex; align-items: center; gap: 12px; }
.app-title { font-size: 18px; font-weight: 600; margin: 0; }
.status-badge { font-size: 12px; padding: 4px 10px; border-radius: 999px; background: color-mix(in srgb, #F3A04C 12%, transparent); color: #E58522; border: 0.5px solid color-mix(in srgb, #F3A04C 25%, transparent); max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.top-bar-right { display: flex; gap: 8px; }
.btn-primary { padding: 7px 16px; border: none; border-radius: 10px; background: #F3A04C; color: #fff; font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-primary:hover { background: #E58522; }
.btn-primary:disabled { opacity: .5; cursor: not-allowed; }
.btn-secondary { padding: 7px 16px; border: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); border-radius: 10px; background: var(--bg-secondary, rgba(0,0,0,.04)); color: var(--text-primary); font-size: 13px; cursor: pointer; }
.btn-secondary:hover { background: rgba(0,0,0,.06); }

/* ---- 三栏 ---- */
.three-col-layout { display: grid; grid-template-columns: 280px 1fr 320px; flex: 1; min-height: 0; overflow: hidden; }

/* ---- 左栏 ---- */
.col-left { background: var(--panel-bg, #FEFDFC); border-right: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); display: flex; flex-direction: column; overflow: hidden; }

/* 上传弹窗样式 */
.modal-upload { width: 420px; }
.modal-upload .upload-drop { margin-bottom: 10px; }
.modal-upload .upload-textarea { margin-bottom: 10px; }

/* 添加记录按钮 */
.add-record-btn { width: 100%; padding: 6px 0; margin-top: 8px; border: 1px dashed var(--border-primary, rgba(0,0,0,.12)); border-radius: 8px; background: none; font-size: 12px; color: #E58522; cursor: pointer; font-weight: 500; transition: background 0.15s, border-color 0.15s; }
.add-record-btn:hover { background: color-mix(in srgb, #F3A04C 6%, transparent); border-color: #F3A04C; }

.upload-drop { border: 1.5px dashed var(--border-primary, rgba(0,0,0,.12)); border-radius: 10px; padding: 16px; text-align: center; background: var(--bg-secondary, rgba(0,0,0,.02)); }
.upload-drop.drag { border-color: #F3A04C; background: color-mix(in srgb, #F3A04C 5%, transparent); }
.upload-label { display: block; cursor: pointer; font-size: 13px; color: var(--text-secondary, rgba(0,0,0,.5)); margin-bottom: 4px; }
.upload-label:hover { color: #E58522; }
.upload-hint { font-size: 11px; color: var(--text-tertiary, rgba(0,0,0,.35)); }
.file-chip { display: inline-flex; align-items: center; gap: 6px; margin-top: 8px; padding: 4px 10px; background: color-mix(in srgb, #F3A04C 10%, transparent); border-radius: 6px; font-size: 12px; color: #E58522; }
.file-chip button { border: none; background: none; cursor: pointer; font-size: 11px; color: var(--text-tertiary); }
.upload-textarea { width: 100%; padding: 8px 10px; border: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); border-radius: 8px; font-size: 12px; font-family: ui-monospace, monospace; background: var(--bg-secondary, rgba(0,0,0,.04)); outline: none; resize: vertical; box-sizing: border-box; line-height: 1.5; }
.upload-textarea:focus { border-color: #F3A04C; }
.btn-analyze { padding: 7px 0; border: none; border-radius: 8px; background: #F3A04C; color: #fff; font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-analyze:hover:not(:disabled) { background: #E58522; }
.btn-analyze:disabled { opacity: .45; cursor: not-allowed; }
.analyze-error { font-size: 12px; color: #E65C53; padding: 4px 0; margin-bottom: 8px; }

/* 当前实验指示器 */
.current-exp-bar { display: flex; align-items: center; gap: 8px; padding: 8px 16px; background: color-mix(in srgb, #F3A04C 8%, transparent); border-bottom: 0.5px solid color-mix(in srgb, #F3A04C 20%, transparent); flex-shrink: 0; }
.current-exp-bar.empty { background: var(--bg-secondary, rgba(0,0,0,.03)); border-bottom: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); }
.current-exp-label { font-size: 10px; color: var(--text-tertiary, rgba(0,0,0,.35)); font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
.current-exp-name { font-size: 13px; font-weight: 600; color: #E58522; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.current-exp-count { font-size: 11px; color: var(--text-tertiary, rgba(0,0,0,.35)); flex-shrink: 0; }

/* 实验列表 */
.btn-new-exp-sm { padding: 3px 10px; border: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); border-radius: 6px; background: none; font-size: 11px; color: #E58522; cursor: pointer; font-weight: 500; }
.btn-new-exp-sm:hover { background: color-mix(in srgb, #F3A04C 8%, transparent); }
.exp-scroll { flex: 1; overflow-y: auto; padding: 0 10px 10px; }

/* 月份分组标题 */
.month-header { display: flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 600; color: var(--text-secondary, rgba(0,0,0,.5)); padding: 10px 4px 6px; letter-spacing: 0.3px; }
.month-header svg { color: var(--text-tertiary, rgba(0,0,0,.3)); flex-shrink: 0; }

/* 实验卡片 */
.exp-card { padding: 10px 12px; border-radius: 10px; cursor: pointer; margin-bottom: 6px; border: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); background: var(--panel-bg, #FEFDFC); transition: border-color 0.15s, background 0.15s; }
.exp-card:hover { border-color: var(--border-primary, rgba(0,0,0,.12)); }
.exp-card.active { background: color-mix(in srgb, #F3A04C 6%, transparent); border-color: color-mix(in srgb, #F3A04C 25%, transparent); }
.exp-card-top { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 4px; }
.exp-card-name { font-size: 13px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.exp-card-bottom { display: flex; align-items: center; gap: 8px; font-size: 11px; color: var(--text-tertiary, rgba(0,0,0,.35)); }
.exp-card-date { flex-shrink: 0; }
.exp-card-count { flex-shrink: 0; }

/* 状态角标 */
.status-tag { font-size: 10px; font-weight: 500; padding: 2px 8px; border-radius: 9px; flex-shrink: 0; line-height: 1.4; }
.status-tag.pending { background: rgba(0,0,0,.06); color: var(--text-secondary, rgba(0,0,0,.45)); }
.status-tag.running { background: rgba(235,164,0,.12); color: #C08800; }
.status-tag.done { background: rgba(64,180,62,.12); color: #2E8B2C; }
.status-tag.failed { background: rgba(230,92,83,.12); color: #C43E35; }
.status-tag.paused { background: rgba(59,130,246,.12); color: #2563EB; }

/* 删除按钮 */
.exp-del-btn { border: none; background: none; cursor: pointer; font-size: 11px; color: var(--text-tertiary, rgba(0,0,0,.25)); padding: 2px 4px; border-radius: 4px; opacity: 0; transition: opacity 0.1s; flex-shrink: 0; margin-left: auto; }
.exp-card:hover .exp-del-btn { opacity: 1; }
.exp-del-btn:hover { background: rgba(230,92,83,.1); color: #E65C53; }

/* 展开记录 */
.exp-records { padding: 6px 0 2px; margin-top: 6px; border-top: 0.5px solid var(--border-secondary, rgba(0,0,0,.06)); }
.exp-no-records { font-size: 11px; color: var(--text-tertiary, rgba(0,0,0,.3)); padding: 4px 0; }

.panel-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px 8px; flex-shrink: 0; }
.panel-header h2 { font-size: 15px; font-weight: 500; margin: 0; }
.record-count { font-size: 12px; color: var(--text-tertiary, rgba(0,0,0,.35)); padding: 2px 8px; border: 0.5px solid var(--border-secondary); border-radius: 9px; }
.search-input { margin: 0 12px 8px; height: 34px; width: calc(100% - 24px); border: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); border-radius: 10px; background: var(--bg-secondary, rgba(0,0,0,.04)); padding: 0 12px; font-size: 13px; outline: none; box-sizing: border-box; }
.search-input:focus { border-color: #F3A04C; box-shadow: 0 0 0 2px rgba(243,160,76,.1); }
.record-list { flex: 1; overflow-y: auto; padding: 0 8px 8px; }
.record-item { padding: 10px 12px; border-radius: 10px; cursor: pointer; margin-bottom: 4px; border: 0.5px solid transparent; }
.record-item:hover { background: var(--bg-secondary, rgba(0,0,0,.04)); }
.record-item.selected { background: color-mix(in srgb, #F3A04C 8%, transparent); border-color: color-mix(in srgb, #F3A04C 20%, transparent); }
.record-task { font-size: 13px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-bottom: 4px; }
.record-meta { display: flex; gap: 6px; flex-wrap: wrap; }
.chip { font-size: 11px; padding: 1px 6px; border: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); border-radius: 4px; color: var(--text-tertiary, rgba(0,0,0,.35)); max-width: 100px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chip-date { font-size: 11px; color: var(--text-tertiary, rgba(0,0,0,.35)); }
.record-del-btn { border: none; background: none; cursor: pointer; font-size: 11px; color: var(--text-tertiary, rgba(0,0,0,.25)); padding: 2px 4px; border-radius: 4px; opacity: 0; transition: opacity 0.1s; flex-shrink: 0; margin-left: auto; }
.record-item:hover .record-del-btn { opacity: 1; }
.record-del-btn:hover { background: rgba(230,92,83,.1); color: #E65C53; }
.empty-hint { padding: 20px; text-align: center; color: var(--text-tertiary, rgba(0,0,0,.35)); font-size: 13px; }

/* ---- 中栏 ---- */
.col-center { display: flex; flex-direction: column; overflow: hidden; background: var(--card-bg, #fff); }
.chat-container { display: flex; flex-direction: column; height: 100%; padding: 20px; }
.chat-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; flex-shrink: 0; gap: 12px; }
.chat-header-left { flex: 1; min-width: 0; }
.chat-header h2 { font-size: 16px; font-weight: 500; margin: 0 0 6px; }
.chat-desc { font-size: 13px; color: var(--text-secondary, rgba(0,0,0,.5)); margin: 0; }
.chat-header-actions { display: flex; align-items: center; gap: 6px; position: relative; flex-shrink: 0; padding-top: 2px; }
.chat-history-btn { display: flex; align-items: center; gap: 4px; padding: 5px 10px; border: 0.5px solid var(--border-secondary, rgba(0,0,0,.1)); border-radius: 16px; background: var(--bg-secondary, rgba(0,0,0,.03)); font-size: 11px; color: var(--text-secondary, rgba(0,0,0,.5)); cursor: pointer; transition: all .15s; white-space: nowrap; }
.chat-history-btn:hover { background: rgba(0,0,0,.06); color: var(--text-primary); border-color: var(--accent, #F3A04C); }
.chat-history-btn svg { flex-shrink: 0; }

/* 会话列表下拉面板 */
.session-dropdown { position: absolute; top: 100%; right: 0; margin-top: 6px; z-index: 50; }
.session-list { width: 260px; background: var(--panel-bg, #FEFDFC); border: 0.5px solid var(--border-secondary, rgba(0,0,0,.1)); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,.1); overflow: hidden; }
.session-list-header { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; border-bottom: 0.5px solid var(--border-secondary, rgba(0,0,0,.06)); font-size: 12px; font-weight: 600; color: var(--text-primary); }
.session-new-btn { border: none; background: none; color: var(--accent, #F3A04C); font-size: 11px; font-weight: 500; cursor: pointer; padding: 2px 6px; border-radius: 8px; }
.session-new-btn:hover { background: color-mix(in srgb, #F3A04C 10%, transparent); }
.session-item { padding: 8px 14px; cursor: pointer; border-bottom: 0.5px solid var(--border-secondary, rgba(0,0,0,.04)); transition: background .1s; }
.session-item:hover { background: rgba(0,0,0,.03); }
.session-item.active { background: color-mix(in srgb, #F3A04C 8%, transparent); }
.session-item-title { display: block; font-size: 12px; font-weight: 500; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.session-item-meta { display: block; font-size: 10px; color: var(--text-tertiary, rgba(0,0,0,.35)); margin-top: 2px; }
.session-empty { padding: 16px; text-align: center; font-size: 12px; color: var(--text-tertiary, rgba(0,0,0,.35)); }
.messages-area { flex: 1; overflow-y: auto; margin-bottom: 16px; min-height: 0; padding-right: 4px; }
.msg-row { display: flex; margin-bottom: 12px; }
.msg-user { justify-content: flex-end; }
.msg-assistant { justify-content: flex-start; }
.msg-bubble { max-width: 80%; padding: 10px 16px; border-radius: 14px; font-size: 13px; line-height: 1.6; word-break: break-word; }
.msg-user .msg-bubble { background: color-mix(in srgb, #F3A04C 12%, transparent); border: 0.5px solid color-mix(in srgb, #F3A04C 20%, transparent); border-radius: 14px 14px 4px 14px; }
.msg-assistant .msg-bubble { background: var(--bg-secondary, rgba(0,0,0,.04)); border: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); border-radius: 14px 14px 14px 4px; }
.msg-text :deep(code) { font-family: ui-monospace, monospace; font-size: 12px; background: rgba(0,0,0,.05); padding: 1px 5px; border-radius: 3px; }
.msg-text :deep(pre) { background: rgba(0,0,0,.04); padding: 8px 12px; border-radius: 6px; overflow-x: auto; margin: 6px 0; }
.msg-text :deep(pre code) { background: none; padding: 0; }
.msg-text :deep(ul), .msg-text :deep(ol) { padding-left: 20px; margin: 4px 0; }
.msg-text :deep(li) { margin: 2px 0; }
.msg-text :deep(h1), .msg-text :deep(h2), .msg-text :deep(h3) { font-size: 14px; font-weight: 600; margin: 8px 0 4px; }
.msg-text :deep(table) { border-collapse: collapse; font-size: 12px; margin: 6px 0; width: 100%; }
.msg-text :deep(th), .msg-text :deep(td) { border: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); padding: 4px 8px; text-align: left; }
.msg-text :deep(blockquote) { border-left: 3px solid #F3A04C; padding-left: 10px; margin: 6px 0; color: var(--text-secondary); }

/* Agent trace 折叠 */
.msg-trace { margin-top: 8px; border-top: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); padding-top: 6px; }
.msg-trace summary { font-size: 11px; color: var(--text-tertiary, rgba(0,0,0,.35)); cursor: pointer; user-select: none; }
.msg-trace summary:hover { color: var(--text-secondary); }
.trace-step { display: flex; gap: 6px; align-items: center; font-size: 11px; padding: 2px 0; color: var(--text-secondary, rgba(0,0,0,.5)); }
.trace-tool { font-family: ui-monospace, monospace; font-weight: 500; color: var(--text-primary, rgba(0,0,0,.7)); }
.trace-status { padding: 0 5px; border-radius: 3px; font-size: 10px; }
.trace-status.success { background: rgba(64,180,62,.1); color: #40B43E; }
.trace-status.deferred { background: rgba(235,164,0,.1); color: #EBA400; }
.trace-status.error, .trace-status.failed { background: rgba(230,92,83,.1); color: #E65C53; }
.trace-result { font-size: 10px; color: var(--text-tertiary, rgba(0,0,0,.35)); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 200px; }

.typing { display: flex; gap: 4px; padding: 14px 20px !important; }
.dot { width: 7px; height: 7px; border-radius: 50%; background: var(--text-tertiary, rgba(0,0,0,.25)); animation: bounce 1.2s infinite; }
.dot:nth-child(2) { animation-delay: .15s; }
.dot:nth-child(3) { animation-delay: .3s; }
@keyframes bounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-6px); } }
.empty-chat { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-tertiary, rgba(0,0,0,.35)); }
.empty-icon { font-size: 40px; margin-bottom: 12px; }
.quick-actions { display: flex; gap: 8px; margin-top: 16px; flex-wrap: wrap; justify-content: center; }
.quick-btn { padding: 6px 14px; border: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); border-radius: 999px; background: none; font-size: 12px; color: var(--text-secondary, rgba(0,0,0,.5)); cursor: pointer; }
.quick-btn:hover { background: var(--bg-secondary, rgba(0,0,0,.04)); color: var(--text-primary); }
.context-tags { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; flex-shrink: 0; }
.ctx-tag { font-size: 11px; padding: 3px 10px; border-radius: 999px; background: color-mix(in srgb, #F3A04C 10%, transparent); color: #E58522; border: 0.5px solid color-mix(in srgb, #F3A04C 20%, transparent); max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ctx-removable { cursor: pointer; background: rgba(0,0,0,.04); border-color: rgba(0,0,0,.08); color: var(--text-tertiary, rgba(0,0,0,.35)); }
.ctx-removable:hover { background: rgba(0,0,0,.08); }
.ctx-hint { font-size: 11px; color: var(--text-tertiary, rgba(0,0,0,.35)); }
.input-area { flex-shrink: 0; }
.chat-input { width: 100%; min-height: 72px; padding: 10px 14px; border: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); border-radius: 10px; background: var(--bg-secondary, rgba(0,0,0,.04)); font-size: 13px; font-family: inherit; resize: none; outline: none; box-sizing: border-box; line-height: 1.5; }
.chat-input:focus { border-color: #F3A04C; box-shadow: 0 0 0 2px rgba(243,160,76,.1); }
.input-toolbar { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; }
.toolbar-left { display: flex; gap: 6px; }
.tool-btn { padding: 4px 10px; border: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); border-radius: 999px; background: none; font-size: 11px; color: var(--text-secondary, rgba(0,0,0,.5)); cursor: pointer; }
.tool-btn:hover { background: rgba(0,0,0,.04); color: var(--text-primary); }
.btn-send { padding: 7px 18px; border: none; border-radius: 8px; background: #F3A04C; color: #fff; font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-send:hover:not(:disabled) { background: #E58522; }
.btn-send:disabled { opacity: .45; cursor: not-allowed; }

/* ---- 右栏 ---- */
.col-right { background: var(--panel-bg, #FEFDFC); border-left: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); display: flex; flex-direction: column; overflow: hidden; }
.graph-header-actions { display: flex; gap: 6px; align-items: center; }
.graph-select-sm { padding: 3px 6px; border: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); border-radius: 6px; background: var(--bg-secondary, rgba(0,0,0,.04)); font-size: 11px; max-width: 150px; outline: none; color: var(--text-primary); }
.btn-sm { padding: 3px 10px; border: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); border-radius: 6px; background: none; font-size: 11px; cursor: pointer; }
.btn-sm:hover { background: rgba(0,0,0,.04); }
.graph-wrap { flex: 0 0 200px; min-height: 180px; margin: 0 12px; border: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); border-radius: 10px; overflow: hidden; display: flex; align-items: center; justify-content: center; }
.graph-empty { text-align: center; color: var(--text-secondary, rgba(0,0,0,.5)); }
.graph-empty-icon { font-size: 28px; margin-bottom: 6px; }
.graph-empty-hint { font-size: 11px; color: var(--text-tertiary, rgba(0,0,0,.35)); margin-top: 4px; }
.linkage-panel { padding: 0 12px; flex: 1; overflow-y: auto; min-height: 0; }
.linkage-panel h3 { font-size: 14px; font-weight: 500; margin: 12px 0 10px; }
.link-card { background: var(--bg-secondary, rgba(0,0,0,.04)); border: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); border-radius: 10px; padding: 10px 12px; margin-bottom: 8px; }
.link-card.active { background: color-mix(in srgb, #F3A04C 8%, transparent); border-color: color-mix(in srgb, #F3A04C 20%, transparent); }
.link-card-title { font-size: 12px; font-weight: 500; margin-bottom: 6px; display: flex; align-items: center; justify-content: space-between; }
.link-card-content { font-size: 11px; color: var(--text-secondary, rgba(0,0,0,.5)); line-height: 1.6; }

/* 详情 */
.detail-meta-row { display: flex; justify-content: space-between; font-size: 11px; padding: 2px 0; color: var(--text-secondary, rgba(0,0,0,.5)); gap: 8px; }
.detail-meta-row > span:last-child { text-align: right; word-break: break-all; max-width: 180px; overflow: hidden; text-overflow: ellipsis; }
.detail-label { color: var(--text-tertiary, rgba(0,0,0,.35)); font-weight: 500; flex-shrink: 0; }
.detail-loading { padding: 10px; text-align: center; font-size: 12px; color: var(--text-tertiary); }
.detail-block { margin-top: 8px; }
.detail-code { display: block; font-family: ui-monospace, monospace; font-size: 11px; padding: 3px 6px; background: rgba(0,0,0,.04); border-radius: 4px; margin: 2px 0; overflow-x: auto; word-break: break-all; }
.detail-text { font-size: 11px; color: var(--text-secondary, rgba(0,0,0,.5)); line-height: 1.5; margin: 2px 0; }
.error-text { color: #E65C53; }
.detail-empty-hint { font-size: 11px; color: var(--text-tertiary, rgba(0,0,0,.35)); padding: 8px 0; text-align: center; }

/* LLM 状态标识 */
.llm-badge { font-size: 10px; font-weight: 500; padding: 1px 7px; border-radius: 6px; }
.llm-badge.llm-on { background: rgba(64,180,62,.1); color: #2E8B2C; }
.llm-badge.llm-off { background: rgba(235,164,0,.1); color: #C08800; }

/* 分析过程折叠区 */
.detail-trace { margin-top: 10px; border-top: 0.5px solid var(--border-secondary, rgba(0,0,0,.06)); padding-top: 6px; }
.detail-trace summary { font-size: 11px; color: var(--text-tertiary, rgba(0,0,0,.35)); cursor: pointer; user-select: none; font-weight: 500; }
.detail-trace summary:hover { color: var(--text-secondary); }
.detail-trace .trace-step { display: flex; gap: 6px; align-items: center; font-size: 11px; padding: 2px 0; color: var(--text-secondary, rgba(0,0,0,.5)); }
.detail-trace .trace-tool { font-family: ui-monospace, monospace; font-weight: 500; color: var(--text-primary, rgba(0,0,0,.7)); font-size: 11px; }
.detail-trace .trace-status { padding: 0 5px; border-radius: 3px; font-size: 10px; }
.detail-trace .trace-status.success { background: rgba(64,180,62,.1); color: #40B43E; }
.detail-trace .trace-status.deferred { background: rgba(235,164,0,.1); color: #EBA400; }
.detail-trace .trace-status.error { background: rgba(230,92,83,.1); color: #E65C53; }
.detail-trace .trace-result { font-size: 10px; color: var(--text-tertiary, rgba(0,0,0,.35)); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 180px; }

/* 参数 */
.param-group { display: flex; gap: 4px; flex-wrap: wrap; align-items: center; margin: 2px 0; }
.param-layer { font-size: 10px; color: var(--text-tertiary, rgba(0,0,0,.35)); font-weight: 500; margin-right: 2px; }
.param-chip { font-size: 10px; padding: 1px 6px; background: rgba(0,0,0,.04); border: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); border-radius: 4px; font-family: ui-monospace, monospace; }
.param-chip.adjusted { background: color-mix(in srgb, #F3A04C 8%, transparent); border-color: color-mix(in srgb, #F3A04C 20%, transparent); }

/* 报告预览 */
.report-char-count { font-size: 10px; font-weight: 400; color: var(--text-tertiary, rgba(0,0,0,.35)); }
.report-preview { font-size: 11px; color: var(--text-secondary, rgba(0,0,0,.5)); line-height: 1.5; max-height: 160px; overflow-y: auto; }
.report-preview :deep(code) { font-family: ui-monospace, monospace; font-size: 10px; background: rgba(0,0,0,.05); padding: 1px 4px; border-radius: 2px; }
.report-preview :deep(strong) { font-weight: 600; color: var(--text-primary); }
.report-preview :deep(ul), .report-preview :deep(ol) { padding-left: 16px; margin: 3px 0; }
.report-preview :deep(li) { margin: 1px 0; }
.report-preview :deep(h1), .report-preview :deep(h2), .report-preview :deep(h3) { font-size: 12px; font-weight: 600; margin: 6px 0 3px; }
.report-more-hint { font-size: 10px; color: var(--text-tertiary); margin-top: 4px; }
.report-loading-card { text-align: center; }

.action-btns { display: flex; gap: 6px; margin-top: 8px; }
.act-btn { flex: 1; padding: 5px 0; border: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); border-radius: 8px; background: var(--bg-primary, rgba(0,0,0,.02)); font-size: 11px; cursor: pointer; }
.act-btn:hover { background: rgba(0,0,0,.06); }
.act-btn:disabled { opacity: .45; cursor: not-allowed; }

/* 状态 */
.link-status { padding: 10px 12px; border-top: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); flex-shrink: 0; }
.status-item { display: flex; align-items: center; gap: 8px; font-size: 11px; color: var(--text-secondary, rgba(0,0,0,.5)); margin-bottom: 4px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #40B43E; }
.status-item.ok .status-dot { background: #40B43E; }
.status-item.warn .status-dot { background: #EBA400; }

/* 全屏图谱 */
.graph-fullscreen-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.5); display: flex; align-items: center; justify-content: center; z-index: 100; }
.graph-fullscreen-box { width: 85vw; height: 80vh; background: var(--panel-bg, #FEFDFC); border-radius: 14px; display: flex; flex-direction: column; overflow: hidden; }
.graph-fs-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 0.5px solid var(--border-secondary); }
.graph-fs-body { flex: 1; min-height: 0; }

/* 实验详情标题栏 */
.detail-section-header { display: flex; justify-content: space-between; align-items: center; margin: 12px 0 10px; }
.detail-section-header h3 { font-size: 14px; font-weight: 500; margin: 0; }
.expand-detail-btn { border: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); background: none; border-radius: 6px; padding: 4px 6px; cursor: pointer; color: var(--text-tertiary, rgba(0,0,0,.35)); display: flex; align-items: center; }
.expand-detail-btn:hover { background: rgba(0,0,0,.04); color: var(--text-primary, rgba(0,0,0,.7)); }

/* 全屏实验详情弹窗 */
.detail-fullscreen-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.35); display: flex; align-items: center; justify-content: center; z-index: 100; }
.detail-fullscreen-box { width: 720px; max-width: 90vw; height: 85vh; background: var(--panel-bg, #FEFDFC); border-radius: 14px; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 16px 48px rgba(0,0,0,.15); }
.detail-fs-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; border-bottom: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); flex-shrink: 0; }
.detail-fs-header h2 { font-size: 16px; font-weight: 600; margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; margin-right: 12px; }
.detail-fs-body { flex: 1; overflow-y: auto; padding: 20px 24px; min-height: 0; scroll-behavior: smooth; }

/* 锚点导航栏 */
.detail-fs-nav { display: flex; align-items: center; gap: 10px; padding: 8px 24px; border-bottom: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); flex-shrink: 0; background: var(--panel-bg, #FEFDFC); }
.fs-nav-pills { display: flex; gap: 4px; flex-shrink: 0; }
.fs-nav-pill { padding: 4px 12px; font-size: 12px; border: none; border-radius: 14px; background: transparent; color: var(--text-secondary, rgba(0,0,0,.5)); cursor: pointer; white-space: nowrap; transition: all .15s; }
.fs-nav-pill:hover { background: rgba(0,0,0,.05); color: var(--text-primary); }
.fs-nav-pill.active { background: var(--accent, #F3A04C); color: #fff; font-weight: 500; }
.fs-nav-search { margin-left: auto; display: flex; align-items: center; gap: 6px; }
.fs-search-input { width: 140px; height: 28px; border: 0.5px solid var(--border-secondary, rgba(0,0,0,.1)); border-radius: 14px; padding: 0 10px; font-size: 12px; outline: none; background: var(--bg-secondary, rgba(0,0,0,.03)); transition: width .2s; }
.fs-search-input:focus { width: 200px; border-color: var(--accent, #F3A04C); background: #fff; }
.fs-search-info { font-size: 11px; color: var(--text-tertiary, rgba(0,0,0,.4)); white-space: nowrap; display: flex; align-items: center; gap: 2px; }
.fs-search-info.fs-no-match { color: #E74C3C; }
.fs-search-arrow { background: none; border: none; cursor: pointer; font-size: 16px; color: var(--text-secondary, rgba(0,0,0,.5)); padding: 0 3px; line-height: 1; }
.fs-search-arrow:hover { color: var(--accent, #F3A04C); }

/* 搜索高亮 */
mark.fs-hl { background: #FFF3C4; color: inherit; padding: 0 1px; border-radius: 2px; }
mark.fs-hl-active { background: var(--accent, #F3A04C); color: #fff; border-radius: 2px; }

/* section 滚动锚点偏移 */
.fs-section[id] { scroll-margin-top: 8px; }

/* 全屏区块 */
.fs-section { margin-bottom: 24px; }
.fs-section-title { font-size: 14px; font-weight: 600; margin: 0 0 12px; padding-bottom: 8px; border-bottom: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); display: flex; align-items: center; gap: 8px; }
.fs-meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 24px; }
.fs-meta-item { display: flex; justify-content: space-between; font-size: 13px; padding: 4px 0; color: var(--text-secondary, rgba(0,0,0,.5)); gap: 12px; }
.fs-meta-item > span:last-child { text-align: right; word-break: break-all; }
.fs-field { margin-bottom: 14px; }
.fs-field .detail-label { display: block; margin-bottom: 4px; font-size: 12px; }
.fs-field p { font-size: 13px; line-height: 1.7; color: var(--text-primary, rgba(0,0,0,.8)); margin: 0; }
.fs-code-list { display: flex; flex-direction: column; gap: 4px; }
.fs-code-list code { display: block; font-family: ui-monospace, monospace; font-size: 12px; padding: 6px 10px; background: rgba(0,0,0,.04); border-radius: 6px; word-break: break-all; line-height: 1.5; }
.fs-empty-hint { font-size: 12px; color: var(--text-tertiary, rgba(0,0,0,.35)); padding: 10px 0; text-align: center; background: var(--bg-secondary, rgba(0,0,0,.03)); border-radius: 8px; }
.fs-trace-list { display: flex; flex-direction: column; gap: 4px; }
.fs-trace-item { display: flex; align-items: center; gap: 8px; font-size: 12px; padding: 6px 10px; background: var(--bg-secondary, rgba(0,0,0,.03)); border-radius: 6px; }
.fs-trace-idx { width: 20px; height: 20px; border-radius: 50%; background: rgba(0,0,0,.06); display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 600; color: var(--text-secondary, rgba(0,0,0,.5)); flex-shrink: 0; }
.fs-trace-detail { font-size: 11px; color: var(--text-tertiary, rgba(0,0,0,.35)); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; min-width: 0; }
.fs-report-body { font-size: 13px; line-height: 1.8; color: var(--text-primary, rgba(0,0,0,.8)); }
.fs-report-body :deep(h1) { font-size: 18px; font-weight: 600; margin: 16px 0 8px; padding-bottom: 6px; border-bottom: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); }
.fs-report-body :deep(h2) { font-size: 15px; font-weight: 600; margin: 14px 0 6px; }
.fs-report-body :deep(h3) { font-size: 13px; font-weight: 600; margin: 10px 0 4px; color: var(--text-secondary); }
.fs-report-body :deep(code) { font-family: ui-monospace, monospace; font-size: 12px; background: rgba(0,0,0,.05); padding: 1px 5px; border-radius: 3px; }
.fs-report-body :deep(pre) { background: rgba(0,0,0,.04); padding: 10px 14px; border-radius: 8px; overflow-x: auto; margin: 8px 0; }
.fs-report-body :deep(pre code) { background: none; padding: 0; }
.fs-report-body :deep(ul), .fs-report-body :deep(ol) { padding-left: 20px; margin: 6px 0; }
.fs-report-body :deep(li) { margin: 3px 0; }
.fs-report-body :deep(table) { border-collapse: collapse; font-size: 12px; margin: 8px 0; width: 100%; }
.fs-report-body :deep(th), .fs-report-body :deep(td) { border: 0.5px solid var(--border-secondary, rgba(0,0,0,.08)); padding: 6px 10px; text-align: left; }
.fs-report-body :deep(blockquote) { border-left: 3px solid #F3A04C; padding-left: 12px; margin: 8px 0; color: var(--text-secondary); }

@media (max-width: 1200px) { .three-col-layout { grid-template-columns: 240px 1fr 280px; } }
@media (max-width: 900px) { .three-col-layout { grid-template-columns: 1fr; } .col-left { max-height: 35vh; } .col-right { max-height: 35vh; } }

/* 流式输出光标动画 */
.msg-bubble.is-streaming .msg-text::after {
  content: '';
  display: inline-block;
  width: 2px;
  height: 1em;
  background: var(--accent, #F3A04C);
  margin-left: 2px;
  vertical-align: text-bottom;
  animation: blink-cursor 0.8s step-end infinite;
}
@keyframes blink-cursor {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
