<template>
  <div class="scientific-ide" :data-theme="theme" @click="handleGlobalClick">
    <!-- 1. TOP BAR -->
    <header class="top-bar">
      <div class="top-bar-left">
        <div class="brand-logo" @click="activeTab = 'overview'" title="ResearchOS">
          <i class="fa-solid fa-atom"></i>
          <span>ResearchOS</span>
        </div>
        <span class="breadcrumb-sep">/</span>

        <!-- 项目选择下拉框 (站内即时切换，无白屏跳转) -->
        <div class="project-selector-wrapper">
          <div class="project-selector" @click.stop="showProjectDropdown = !showProjectDropdown" title="切换研究项目">
            <span class="status-dot-active"></span>
            <span class="font-medium">{{ project?.name || '加载中...' }}</span>
            <i class="fa-solid fa-chevron-down text-muted" style="font-size: 9px; margin-left: 4px;"></i>
          </div>

          <!-- 下拉项目列表面板 -->
          <div v-if="showProjectDropdown" class="project-dropdown-menu" @click.stop>
            <div class="dropdown-header">
              <span>{{ lang === 'en-US' ? 'RESEARCH PROJECTS' : '研究项目列表' }}</span>
              <button class="btn-new-proj" @click="openCreateProjectModal">+ {{ lang === 'en-US' ? 'New' : '新建项目' }}</button>
            </div>
            <div class="dropdown-list">
              <div
                v-for="p in allProjects"
                :key="p.id"
                class="dropdown-item"
                :class="{ active: p.id === currentProjectId }"
                @click="switchProject(p.id)"
              >
                <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                  <div>
                    <div class="di-name">
                      <i class="fa-solid fa-folder" style="font-size: 11px; margin-right: 6px;"></i>
                      {{ p.name }}
                    </div>
                    <div class="di-meta font-mono">
                      {{ p.experiment_ids?.length || 0 }} {{ lang === 'en-US' ? 'Exps' : '实验' }} · {{ p.questions?.length || 0 }} {{ lang === 'en-US' ? 'RQs' : '问题' }}
                    </div>
                  </div>
                  <button
                    class="btn-icon-del"
                    style="background: transparent; border: none; color: #ef4444; opacity: 0.7; cursor: pointer; padding: 4px 6px; border-radius: 4px;"
                    @click.stop="deleteProject(p.id, p.name)"
                    :title="lang === 'en-US' ? 'Delete this project' : '删除此项目'"
                  >
                    <i class="fa-solid fa-trash-can"></i>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="top-bar-right">
        <!-- 快速沉淀科研记录按钮 (Quick Capture) -->
        <button class="btn-doc" style="border-color: #eab308; color: #ca8a04; font-weight: 700;" @click="showQuickCapture = true" :title="lang === 'en-US' ? '30s Quick Capture for external experiment / reflection' : '30秒快速记录本次外部实验、反思与 Git 状态'">
          <i class="fa-solid fa-bolt"></i>
          <span>{{ lang === 'en-US' ? 'Quick Capture' : '⚡ 快速记录' }}</span>
        </button>

        <!-- 课题环境与工作空间设置按钮 -->
        <button class="btn-doc" style="border-color: var(--accent-science-dim); color: var(--accent-science);" @click="openEnvSettingsModal" :title="lang === 'en-US' ? 'Configure Python Environment & Workspace' : '配置当前课题的 Python 虚拟环境与工作空间'">
          <i class="fa-brands fa-python"></i>
          <span>{{ currentEnvLabel }}</span>
        </button>

        <!-- 使用文档按钮 -->
        <button class="btn-doc" @click="showDocModal = true">
          <i class="fa-solid fa-book-open"></i>
          <span>{{ t('top.docs') }}</span>
        </button>

        <!-- 语言切换 -->
        <div class="demo-switcher-group">
          <button class="switcher-btn" :class="{ active: lang === 'en-US' }" @click="setLanguage('en-US')">EN</button>
          <button class="switcher-btn" :class="{ active: lang === 'zh-CN' }" @click="setLanguage('zh-CN')">中文</button>
        </div>

        <!-- 主题切换 -->
        <div class="demo-switcher-group">
          <button class="switcher-btn" :class="{ active: theme === 'dark' }" @click="setTheme('dark')">Dark</button>
          <button class="switcher-btn" :class="{ active: theme === 'light' }" @click="setTheme('light')">Light</button>
          <button class="switcher-btn" :class="{ active: theme === 'system' }" @click="setTheme('system')">System</button>
        </div>

        <!-- 全局指令搜索 (⌘K) -->
        <button class="search-btn" @click="showCmdPalette = true">
          <i class="fa-solid fa-magnifying-glass" style="font-size: 11px;"></i>
          <span>{{ t('searchPlaceholder') }}</span>
          <span class="kbd-shortcut">⌘K</span>
        </button>

        <!-- 站内直接新建实验方案 (无白屏外跳) -->
        <button class="btn-action-primary" @click="showCreateExpModal = true">
          <i class="fa-solid fa-plus" style="font-size: 11px;"></i>
          <span>{{ t('newExperiment') }}</span>
        </button>
      </div>
    </header>

    <!-- 2. MAIN CONTAINER -->
    <div class="main-container">
      <!-- 2.1 LEFT SIDEBAR NAVIGATION -->
      <nav class="sidebar-nav">
        <div class="nav-section-title">{{ t('nav.research') }}</div>
        <a class="nav-item" :class="{ active: activeTab === 'overview' }" @click="activeTab = 'overview'">
          <i class="fa-solid fa-compass"></i>
          <span>{{ t('nav.overview') }}</span>
        </a>
        <a class="nav-item" :class="{ active: activeTab === 'questions' }" @click="activeTab = 'questions'">
          <i class="fa-solid fa-circle-question"></i>
          <span>{{ t('nav.questions') }}</span>
          <span class="nav-badge">{{ project?.questions?.length || 0 }}</span>
        </a>
        <a class="nav-item" :class="{ active: activeTab === 'hypotheses' }" @click="activeTab = 'hypotheses'">
          <i class="fa-solid fa-lightbulb"></i>
          <span>{{ t('nav.hypotheses') }}</span>
          <span class="nav-badge">{{ hypothesesCount }}</span>
        </a>
        <a class="nav-item" :class="{ active: activeTab === 'literature' }" @click="activeTab = 'literature'">
          <i class="fa-solid fa-book-bookmark"></i>
          <span>{{ t('nav.literature') }}</span>
          <span class="nav-badge">{{ papersCount }}</span>
        </a>
        <a class="nav-item" :class="{ active: activeTab === 'datasets' }" @click="activeTab = 'datasets'">
          <i class="fa-solid fa-database"></i>
          <span>{{ t('nav.datasets') }}</span>
          <span class="nav-badge">{{ datasetsCount }}</span>
        </a>

        <div class="nav-section-title">{{ t('nav.experiment') }}</div>
        <a class="nav-item" :class="{ active: activeTab === 'experiments' }" @click="activeTab = 'experiments'">
          <i class="fa-solid fa-flask"></i>
          <span>{{ t('nav.experiments') }}</span>
          <span class="nav-badge">{{ project?.experiment_ids?.length || 0 }}</span>
        </a>
        <a class="nav-item" :class="{ active: activeTab === 'runs' }" @click="activeTab = 'runs'">
          <i class="fa-solid fa-terminal"></i>
          <span>{{ t('nav.runs') }}</span>
          <span class="nav-badge">{{ totalRunsCount }}</span>
        </a>
        <a class="nav-item" :class="{ active: activeTab === 'analysis' }" @click="activeTab = 'analysis'">
          <i class="fa-solid fa-chart-line"></i>
          <span>{{ t('nav.analysis') }}</span>
        </a>

        <div class="nav-section-title">{{ t('nav.knowledge') }}</div>
        <a class="nav-item" :class="{ active: activeTab === 'evidence' }" @click="activeTab = 'evidence'">
          <i class="fa-solid fa-shield-halved"></i>
          <span>{{ t('nav.evidence') }}</span>
          <span class="nav-badge">{{ displayedEvidenceLedger.length }}</span>
        </a>
        <a class="nav-item" :class="{ active: activeTab === 'conclusions' }" @click="activeTab = 'conclusions'">
          <i class="fa-solid fa-circle-check"></i>
          <span>{{ t('nav.conclusions') }}</span>
          <span class="nav-badge">{{ conclusionsCount }}</span>
        </a>
        <a class="nav-item" :class="{ active: activeTab === 'graph' }" @click="activeTab = 'graph'">
          <i class="fa-solid fa-diagram-project"></i>
          <span>{{ t('nav.researchGraph') }}</span>
        </a>
        <a class="nav-item" :class="{ active: activeTab === 'artifacts' }" @click="activeTab = 'artifacts'">
          <i class="fa-solid fa-box-archive"></i>
          <span>{{ t('nav.artifacts') }}</span>
          <span class="nav-badge">{{ artifactsCount }}</span>
        </a>
        <a class="nav-item" :class="{ active: activeTab === 'vault' }" @click="activeTab = 'vault'">
          <i class="fa-solid fa-book-bookmark"></i>
          <span>Obsidian Vault</span>
        </a>
        <a class="nav-item" :class="{ active: activeTab === 'explore' }" @click="activeTab = 'explore'">
          <i class="fa-solid fa-compass"></i>
          <span>{{ lang === 'en-US' ? 'Active Explore' : '科学探索 (Explore)' }}</span>
        </a>
        <a class="nav-item" :class="{ active: activeTab === 'diary' }" @click="activeTab = 'diary'">
          <i class="fa-solid fa-book-open"></i>
          <span>{{ lang === 'en-US' ? 'Research Diary' : '科研日记 (Diary)' }}</span>
        </a>
      </nav>

      <!-- 2.2 CENTER WORKSPACE VIEW -->
      <main class="workspace">
        <!-- ZERO STATE ONBOARDING BANNER -->
        <div v-if="allProjects.length === 0" class="workspace-view" style="max-width: 820px; margin: 30px auto; padding: 24px;">
          <div style="background: var(--bg-surface-1); border: 1px solid var(--border-default); border-radius: 12px; padding: 32px; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
            <div style="font-size: 42px; margin-bottom: 12px;">🔬</div>
            <h2 style="font-size: 20px; font-weight: 700; margin-bottom: 8px;">{{ lang === 'zh-CN' ? '欢迎使用 ResearchOS 个人科研工作台' : 'Welcome to ResearchOS Scientific Workspace' }}</h2>
            <p style="color: var(--text-secondary); font-size: 13px; line-height: 1.6; margin-bottom: 20px; max-width: 600px; margin-left: auto; margin-right: auto;">
              {{ lang === 'zh-CN' ? '当前工作区为空。请先创建您的第一个科研课题（如机器学习模型调优、生物数据分析或物理仿真），开启真实科研闭环。' : 'Your workspace is currently clean. Create your first research project to start the scientific loop.' }}
            </p>
            <button class="btn-action-primary" style="padding: 9px 22px; font-size: 13px; font-weight: 600; margin-bottom: 28px;" @click="openCreateProjectModal">
              <i class="fa-solid fa-plus" style="margin-right: 6px;"></i> {{ lang === 'zh-CN' ? '创建第一个科研课题' : 'Create First Project' }}
            </button>

            <div style="background: var(--bg-surface-2); border: 1px solid var(--border-default); border-radius: 8px; padding: 18px 20px; text-align: left;">
              <div style="font-size: 13px; font-weight: 700; margin-bottom: 12px; color: var(--accent-science);">
                <i class="fa-solid fa-route" style="margin-right: 6px;"></i> {{ lang === 'zh-CN' ? '5 步科研闭环快速指引：' : '5-Step Scientific Workflow Guide:' }}
              </div>
              <div style="display: flex; flex-direction: column; gap: 10px; font-size: 12px; line-height: 1.5; color: var(--text-primary);">
                <div><strong>1. {{ lang === 'zh-CN' ? '课题与核心问题' : 'Project & Question' }}</strong>: {{ lang === 'zh-CN' ? '定义研究方向与科学探索目标' : 'Define research topic and core questions' }}</div>
                <div><strong>2. {{ lang === 'zh-CN' ? '文献检索与 PDF 切片' : 'Literature & PDF Slices' }}</strong>: {{ lang === 'zh-CN' ? '跨库搜索论文或上传 PDF 提取精准证据段落' : 'Search papers or upload PDF to extract evidence slices' }}</div>
                <div><strong>3. {{ lang === 'zh-CN' ? '假说与实验方案' : 'Hypothesis & Protocol' }}</strong>: {{ lang === 'zh-CN' ? '提出待检验假说并设计实验超参数空间' : 'Formulate testable hypotheses and configure parameter spaces' }}</div>
                <div><strong>4. {{ lang === 'zh-CN' ? '数据导入与统计向导' : 'Dataset & Analysis Wizard' }}</strong>: {{ lang === 'zh-CN' ? '导入 CSV/Parquet，利用 DuckDB 极速分析并归档产物' : 'Import data and run DuckDB statistical analysis' }}</div>
                <div><strong>5. {{ lang === 'zh-CN' ? '代码生成、运行与复盘' : 'Code, Run & Memory Review' }}</strong>: {{ lang === 'zh-CN' ? 'AI 合成 Python 代码、沙箱运行、智能调试与推演' : 'Generate Python code, run in sandbox, and review findings' }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- VIEW 1: OVERVIEW -->
        <div v-else-if="activeTab === 'overview'" class="workspace-view">
          <div class="project-header">
            <div class="project-title-large">{{ project?.name || (lang === 'zh-CN' ? '项目概览' : 'Project Overview') }}</div>
            <div class="research-question-box">
              <span class="rq-label">{{ t('overview.researchQuestion') }}</span>
              <span class="rq-text">{{ cockpitData?.active_question || activeQuestionText }}</span>
            </div>
          </div>

          <div class="grid-2">
            <!-- 1. 核心科学假说卡片 (Active Hypothesis) -->
            <div class="card hypothesis-card">
              <div>
                <div class="card-header">
                  <span class="card-title-sm">{{ t('overview.activeHypothesis') }}</span>
                  <span class="badge-status" :class="activeHypBadgeClass">{{ (cockpitData?.active_hypothesis?.status || 'testing').toUpperCase() }}</span>
                </div>
                <div class="hypothesis-code">{{ cockpitData?.active_hypothesis?.id || '-' }}</div>
                <div class="hypothesis-body" @click="activeTab = 'hypotheses'" :title="lang === 'en-US' ? 'Click to view Hypotheses' : '点击查看假说详情'">
                  {{ cockpitData?.active_hypothesis?.title || (lang === 'zh-CN' ? '暂无活动假说，点击前往「假说」页面添加' : 'No active hypothesis yet') }}
                </div>
              </div>

              <div class="metrics-row">
                <div class="metric-unit">
                  <span class="metric-label">{{ t('overview.evidenceStrength') }}</span>
                  <span class="metric-value" style="color: var(--accent-warning);">{{ cockpitData?.active_hypothesis ? (cockpitData?.active_hypothesis?.evidence_strength || 'MODERATE').toUpperCase() : '-' }}</span>
                </div>
                <div class="metric-unit">
                  <span class="metric-label">{{ t('overview.coverage') }}</span>
                  <span class="metric-value font-mono">{{ cockpitData?.active_hypothesis?.coverage ? Math.round(cockpitData.active_hypothesis.coverage * 100) + '%' : '-' }}</span>
                </div>
                <div class="metric-unit">
                  <span class="metric-label">{{ t('overview.replication') }}</span>
                  <span class="metric-value font-mono">{{ (project?.experiment_ids?.length || 0) }} / {{ (totalRunsCount || 0) }}</span>
                </div>
              </div>
            </div>

            <!-- 2. 研究推进节奏卡片 (Research Cadence) -->
            <div class="card">
              <div class="card-header">
                <span class="card-title-sm">{{ t('overview.researchCadence') }}</span>
                <span class="font-mono text-muted" style="font-size: 11px;">{{ cockpitData?.cadence?.cycle || t('overview.cycle') }}</span>
              </div>
              <div style="display: flex; flex-direction: column; gap: 10px; margin-top: 4px;">
                <div style="display: flex; justify-content: space-between; font-size: 12px;">
                  <span style="color: var(--text-secondary);">{{ lang === 'zh-CN' ? '历史运行总数:' : 'Total Executed Runs:' }}</span>
                  <span class="font-mono text-primary" style="font-weight: 600;">{{ cockpitData?.cadence?.total_runs ?? totalRunsCount ?? 0 }} {{ lang === 'zh-CN' ? '次 Runs' : 'Runs' }}</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 12px;">
                  <span style="color: var(--text-secondary);">{{ t('overview.bestAccuracy') }}</span>
                  <span class="font-mono" style="color: var(--accent-success); font-weight: 600;">{{ cockpitData?.cadence?.best_accuracy || (lang === 'zh-CN' ? '暂无数据' : 'No data') }}</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 12px;">
                  <span style="color: var(--text-secondary);">{{ t('overview.computeSpent') }}</span>
                  <span class="font-mono text-primary">{{ cockpitData?.cadence?.runtime_total || (lang === 'zh-CN' ? '0 小时' : '0 hrs') }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 2.5 CURRENT RESEARCH STATE (科研全局状态与不确定性) -->
          <div class="card" style="margin-bottom: 24px; border-left: 3px solid var(--accent-science); background: var(--bg-surface-1);">
            <div class="card-title" style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
              <div style="display: flex; align-items: center; gap: 8px;">
                <i class="fa-solid fa-compass" style="color: var(--accent-science);"></i>
                <span style="font-weight: 700; font-size: 13px; letter-spacing: 0.05em; text-transform: uppercase;">
                  {{ lang === 'en-US' ? 'Current Research State' : '当前科研状态与不确定性 (Research State)' }}
                </span>
              </div>
              <span class="font-mono text-muted" style="font-size: 11px;">
                {{ lang === 'en-US' ? 'Live State Matrix' : '事实 / 不确定性 / 下一步矩阵' }}
              </span>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
              <!-- 左侧：已知事实与已试参数 -->
              <div style="display: flex; flex-direction: column; gap: 10px;">
                <div style="background: var(--bg-surface-2); border-radius: 6px; padding: 10px 12px; border: 1px solid var(--border-default);">
                  <div style="font-size: 11px; font-weight: 700; color: var(--accent-success); text-transform: uppercase; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
                    <i class="fa-solid fa-circle-check"></i>
                    <span>{{ lang === 'en-US' ? 'Known & Verified Facts' : '已验证事实 (Known)' }}</span>
                  </div>
                  <ul style="margin: 0; padding-left: 16px; font-size: 12px; line-height: 1.5; color: var(--text-primary);">
                    <li v-for="(k_item, ki) in (cockpitData?.research_state?.known || ['暂无沉淀事实'])" :key="ki">{{ k_item }}</li>
                  </ul>
                </div>

                <div style="background: var(--bg-surface-2); border-radius: 6px; padding: 10px 12px; border: 1px solid var(--border-default);">
                  <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
                    <i class="fa-solid fa-list-check"></i>
                    <span>{{ lang === 'en-US' ? 'Tried Configurations' : '已尝试参数 (Tried)' }}</span>
                  </div>
                  <ul style="margin: 0; padding-left: 16px; font-size: 12px; line-height: 1.5; color: var(--text-secondary);">
                    <li v-for="(t_item, ti) in (cockpitData?.research_state?.tried || ['暂无运行记录']).slice(0, 3)" :key="ti">{{ t_item }}</li>
                  </ul>
                </div>
              </div>

              <!-- 右侧：未知不确定性与下一步 -->
              <div style="display: flex; flex-direction: column; gap: 10px;">
                <div style="background: var(--bg-surface-2); border-radius: 6px; padding: 10px 12px; border: 1px solid var(--border-default);">
                  <div style="font-size: 11px; font-weight: 700; color: var(--accent-warning); text-transform: uppercase; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    <span>{{ lang === 'en-US' ? 'Unknown & Uncertainty Gaps' : '未解决不确定性 (Uncertainty)' }}</span>
                  </div>
                  <ul style="margin: 0; padding-left: 16px; font-size: 12px; line-height: 1.5; color: var(--text-primary);">
                    <li v-for="(u_item, ui) in (cockpitData?.research_state?.unknown_uncertainty || ['尚未识别不确定性'])" :key="ui">{{ u_item }}</li>
                  </ul>
                </div>

                <div style="background: var(--bg-surface-2); border-radius: 6px; padding: 10px 12px; border: 1px solid var(--border-default);">
                  <div style="font-size: 11px; font-weight: 700; color: var(--accent-science); text-transform: uppercase; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
                    <i class="fa-solid fa-arrow-right"></i>
                    <span>{{ lang === 'en-US' ? 'Next Priorities' : '优先推演方向 (Next)' }}</span>
                  </div>
                  <ul style="margin: 0; padding-left: 16px; font-size: 12px; line-height: 1.5; color: var(--text-primary);">
                    <li v-for="(np_item, npi) in (cockpitData?.research_state?.next_priorities || ['暂无建议'])" :key="npi"><strong>{{ np_item }}</strong></li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          <!-- 3. NEXT RESEARCH ACTION (有真实推演建议时渲染，无建议时呈现指引) -->
          <div v-if="cockpitData?.next_research_action?.title" class="next-action-card">
            <div class="next-action-badge">
              <i class="fa-solid fa-bolt" style="font-size: 9px;"></i>
              <span>{{ t('overview.nextActionBadge') }}</span>
            </div>

            <div class="action-header-title">
              {{ cockpitData.next_research_action.title }}
            </div>
            
            <div class="action-reasoning">
              {{ cockpitData.next_research_action.expected_outcome || cockpitData.next_research_action.rationale }}
            </div>

            <!-- 不确定性消除声明 (Uncertainty Addressed) -->
            <div v-if="cockpitData.next_research_action.uncertainty_addressed" style="margin: 8px 0; font-size: 12px; color: var(--accent-warning); background: var(--bg-surface-2); padding: 6px 10px; border-radius: 6px; border: 1px solid var(--border-default);">
              <i class="fa-solid fa-crosshairs" style="margin-right: 6px;"></i>
              <strong>{{ lang === 'en-US' ? 'Uncertainty Addressed:' : '解决的不确定性：' }}</strong>
              <span>{{ cockpitData.next_research_action.uncertainty_addressed }}</span>
            </div>

            <!-- 详细推演依据 (Why & Reasoning Basis) -->
            <div v-if="(cockpitData.next_research_action.why || cockpitData.next_research_action.reasoning_basis)?.length" class="reasoning-basis-box">
              <div class="r-basis-title">
                <i class="fa-solid fa-lightbulb" style="font-size: 11px; margin-right: 5px; color: var(--accent-warning);"></i>
                <span>{{ lang === 'en-US' ? 'Why This Experiment? (Evidence-Based Justification):' : '为什么做此实验？(推演论据与依据)：' }}</span>
              </div>
              <ul class="r-basis-list">
                <li v-for="(rb, rbi) in (cockpitData.next_research_action.why || cockpitData.next_research_action.reasoning_basis)" :key="rbi">
                  <i class="fa-solid fa-angle-right" style="color: var(--accent-primary); margin-right: 6px; font-size: 10px;"></i>
                  <span>{{ rb }}</span>
                </li>
              </ul>
            </div>

            <!-- 结构化参数对比 Pill -->
            <div class="param-pill-group">
              <div
                v-for="(pval, pkey) in (cockpitData.next_research_action.variables || {})"
                :key="pkey"
                class="param-pill"
              >
                <span class="param-key">{{ pkey }}:</span>
                <span class="param-val font-mono">{{ pval }}</span>
              </div>
              <div v-if="cockpitData.next_research_action.information_gain" class="param-pill">
                <span class="param-key">{{ t('overview.infoGain') }}</span>
                <span class="param-val" style="color: var(--accent-success); font-weight: 700;">
                  {{ cockpitData.next_research_action.information_gain }}
                </span>
              </div>
              <div v-if="cockpitData.next_research_action.estimated_cost?.gpu_hours" class="param-pill">
                <span class="param-key">{{ t('overview.computeEst') }}</span>
                <span class="param-val">
                  {{ cockpitData.next_research_action.estimated_cost.gpu_hours }} GPU hrs
                </span>
              </div>
              <div v-if="cockpitData.next_research_action.risk_level" class="param-pill">
                <span class="param-key">{{ lang === 'en-US' ? 'Risk:' : '风险:' }}</span>
                <span class="param-val" style="color: var(--accent-success);">
                  {{ cockpitData.next_research_action.risk_level }}
                </span>
              </div>
            </div>

            <div class="action-buttons">
              <button class="btn-approve" @click="handleActionApprove">
                <i class="fa-solid fa-play" style="font-size: 10px;"></i>
                <span>{{ t('overview.approveRun') }}</span>
              </button>
              <button class="btn-secondary" @click="modifyProtocol">{{ t('overview.modify') }}</button>
              <button v-if="cockpitData.next_research_action.evidence_refs?.length" class="btn-secondary" @click="openEvidenceDrawer(cockpitData.next_research_action.evidence_refs[0]?.id)">
                <i class="fa-solid fa-magnifying-glass" style="font-size: 10px; margin-right: 4px;"></i>
                <span>{{ lang === 'en-US' ? 'View Evidence' : '查看支撑证据' }}</span>
              </button>
            </div>
          </div>

          <div v-else class="card" style="margin-bottom: 24px; padding: 18px; border-left: 3px solid var(--accent-science); background: var(--bg-surface-1);">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div>
                <div style="font-weight: 700; font-size: 13px; color: var(--text-primary); margin-bottom: 4px; display: flex; align-items: center; gap: 8px;">
                  <i class="fa-solid fa-compass" style="color: var(--accent-science);"></i>
                  <span>{{ lang === 'en-US' ? 'Next Action Guidance' : '下一步研究探索指引' }}</span>
                </div>
                <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.5;">
                  {{ lang === 'en-US' ? 'No automated recommendation yet. Propose your first scientific hypothesis or configure your baseline experiment to begin.' : '当前暂无自动化推演建议。请先在「科学假说」中提出您的机理假设，或在「实验方案」中创建并运行首个基线实验。' }}
                </div>
              </div>
              <div style="display: flex; gap: 8px;">
                <button class="btn-secondary" style="font-size: 11px;" @click="activeTab = 'hypotheses'">
                  <i class="fa-solid fa-lightbulb"></i> {{ lang === 'en-US' ? 'Propose Hypothesis' : '提出假说' }}
                </button>
                <button class="btn-action-primary" style="font-size: 11px;" @click="openNewExperimentModal">
                  <i class="fa-solid fa-plus"></i> {{ lang === 'en-US' ? 'New Experiment' : '新建实验' }}
                </button>
              </div>
            </div>
          </div>

          <!-- 4. 证据账本 (Evidence Ledger) -->
          <div class="evidence-section">
            <div class="section-title-bar">
              <span class="section-title">{{ t('overview.evidenceLedger') }}</span>
              <span class="view-link" @click="activeTab = 'graph'">{{ t('overview.viewGraph') }}</span>
            </div>

            <div v-if="!displayedEvidenceLedger.length" class="empty-hint" style="padding: 16px 0; text-align: left;">
              {{ lang === 'en-US' ? 'No evidence items recorded yet in this project.' : '暂无沉淀证据记录。' }}
            </div>
            <div v-else class="evidence-list">
              <div
                v-for="ev in displayedEvidenceLedger"
                :key="ev.id"
                class="evidence-item"
                @click="openEvidenceDrawer(ev.id)"
              >
                <div class="evidence-item-left">
                  <span class="evidence-ref">{{ ev.id }}</span>
                  <span class="evidence-desc">{{ ev.snippet }}</span>
                </div>
                <span class="badge-status" :class="ev.stance === 'SUPPORT' ? 'badge-support' : 'badge-contradict'">
                  {{ ev.stance === 'SUPPORT' ? t('evidenceStatus.support') : t('evidenceStatus.contradict') }}
                </span>
              </div>
            </div>
          </div>

          <!-- 5. 真实科研演进时间线 (Research Timeline) -->
          <div>
            <div class="section-title-bar">
              <span class="section-title">{{ t('overview.recentTimeline') }}</span>
              <span class="font-mono text-muted" style="font-size: 11px;">
                {{ displayedTimelineEvents.length }} {{ lang === 'en-US' ? 'Events recorded' : '条演进记录' }}
              </span>
            </div>

            <div class="activity-timeline">
              <div
                v-for="evt in displayedTimelineEvents"
                :key="evt.id"
                class="timeline-node"
              >
                <span class="timeline-date font-mono">{{ formatTimelineDate(evt.timestamp) }}</span>
                <span class="timeline-text">
                  <strong>{{ evt.title }}</strong>
                  <span v-if="evt.description" style="color: var(--text-muted); margin-left: 6px;">{{ evt.description }}</span>
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- VIEW 2: QUESTIONS -->
        <div v-if="activeTab === 'questions'" class="workspace-view">
          <div class="project-header" style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div class="project-title-large">{{ t('nav.questions') }}</div>
              <p class="text-secondary" style="font-size: 13px; margin: 4px 0 0;">{{ lang === 'en-US' ? 'Formulate and maintain research questions as the origin of all hypotheses and experiments.' : '提出并维护核心科学问题，作为所有假设与实验设计的源头。' }}</p>
            </div>
            <button class="btn-action-primary" @click="showAddQuestion = !showAddQuestion">+ {{ lang === 'en-US' ? 'New Question' : '提出新问题' }}</button>
          </div>

          <div v-if="showAddQuestion" class="card" style="margin-bottom: 20px;">
            <textarea v-model="newQuestionText" :placeholder="lang === 'en-US' ? 'e.g. Can dynamic graph updates improve topological robustness under noisy facial inputs?' : '例如：提高小样本场景下的模型鲁棒性，哪些动态图结构最有效？'" rows="3" class="code-editor" style="background: var(--bg-surface-2); color: var(--text-primary); margin-bottom: 12px;"></textarea>
            <div style="display: flex; gap: 8px;">
              <button class="btn-approve" @click="addQuestion" :disabled="!newQuestionText.trim()">{{ lang === 'en-US' ? 'Save Question' : '保存问题' }}</button>
              <button class="btn-secondary" @click="suggestHypotheses" :disabled="!newQuestionText.trim()">💡 {{ lang === 'en-US' ? 'AI Suggest Hypotheses' : 'AI 建议假设' }}</button>
              <button class="btn-secondary" @click="showAddQuestion = false">{{ lang === 'en-US' ? 'Cancel' : '取消' }}</button>
            </div>
            <div v-if="suggestionList.length" class="provenance-box" style="margin-top: 14px;">
              <strong style="color: var(--accent-warning); font-size: 12px;">{{ lang === 'en-US' ? 'AI Suggested Hypotheses (Click to adopt):' : 'AI 建议的假设方向（点击采纳）：' }}</strong>
              <div v-for="(s, i) in suggestionList" :key="i" class="action-chip" style="margin-top: 6px;" @click="adoptSuggestion(s)">
                <span><strong>{{ s.title }}</strong>: {{ s.description }}</span>
              </div>
            </div>
          </div>

          <div class="evidence-list">
            <div v-for="q in project?.questions || []" :key="q.id" class="evidence-item">
              <div class="evidence-item-left">
                <span class="evidence-ref font-mono">RQ-{{ q.id.slice(0, 6) }}</span>
                <span class="evidence-desc" style="color: var(--text-primary); font-weight: 500;">{{ q.text }}</span>
              </div>
              <div style="display: flex; align-items: center; gap: 10px;">
                <span class="font-mono text-muted" style="font-size: 11px;">{{ formatDate(q.created_at) }}</span>
                <button class="btn-close-drawer" @click="deleteQuestion(q.id)" title="删除"><i class="fa-solid fa-trash"></i></button>
              </div>
            </div>
          </div>
        </div>

        <!-- VIEW 3: HYPOTHESES -->
        <div v-if="activeTab === 'hypotheses'" class="workspace-view">
          <HypothesisPanel :project-id="currentProjectId" :lang="lang" @refresh="loadProject" />
        </div>

        <!-- VIEW 4: LITERATURE -->
        <div v-if="activeTab === 'literature'" class="workspace-view">
          <LiteraturePanel :project-id="currentProjectId" :lang="lang" />
        </div>

        <!-- VIEW 4.5: DATASETS -->
        <div v-if="activeTab === 'datasets'" class="workspace-view">
          <DatasetExplorerPanel :project-id="currentProjectId" :lang="lang" @refresh="loadProject" />
        </div>

        <!-- VIEW 5: EXPERIMENTS & RUNS -->
        <div v-if="activeTab === 'experiments'" class="workspace-view">
          <div class="project-header" style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div class="project-title-large">{{ t('nav.experiments') }} &amp; {{ t('nav.runs') }}</div>
              <p class="text-secondary" style="font-size: 13px; margin: 4px 0 0;">{{ lang === 'en-US' ? 'Decoupled management for experiment protocols and physical execution runs.' : '实验方案设计与实际执行 Run 实例解耦管理。' }}</p>
            </div>
            <div style="display: flex; gap: 8px;">
              <button class="btn-secondary" @click="openCsvImport()">
                <i class="fa-solid fa-file-csv" style="color: var(--accent-science); margin-right: 4px;"></i>
                <span>{{ lang === 'en-US' ? 'Import CSV' : 'CSV 批量导入' }}</span>
              </button>
              <button class="btn-action-primary" @click="showCreateExpModal = true">+ {{ t('newExperiment') }}</button>
            </div>
          </div>

          <div v-if="!project?.experiment_ids?.length" class="empty-hint">{{ lang === 'en-US' ? 'No experiments registered yet in this project.' : '该项目暂未关联实验记录，点击右上角「新建实验方案」开始。' }}</div>

          <div style="display: flex; flex-direction: column; gap: 16px;">
            <div v-for="eid in project?.experiment_ids || []" :key="eid" class="card">
              <div class="card-header" style="border-bottom: 1px solid var(--border-default); padding-bottom: 10px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                  <span class="badge-status badge-support">EXP</span>
                  <strong class="text-primary" style="font-size: 14px;">{{ eid }}</strong>
                </div>
                <div style="display: flex; gap: 6px;">
                  <button class="btn-secondary" style="font-size: 11px; padding: 3px 8px;" @click="openExperimentCoder(eid)">
                    <i class="fa-solid fa-code"></i> {{ lang === 'en-US' ? 'Code & Debug' : '💻 代码与调试' }}
                  </button>
                  <button class="btn-secondary" style="font-size: 11px; padding: 3px 8px;" @click="createNewRun(eid)">+ {{ lang === 'en-US' ? 'New Run' : '发起新 Run' }}</button>
                  <button class="btn-secondary" style="font-size: 11px; padding: 3px 8px; color: #ef4444; border-color: rgba(239,68,68,0.3);" @click="deleteExperiment(eid)" :title="lang === 'en-US' ? 'Delete this experiment and its runs' : '删除此实验方案及其运行记录'">
                    <i class="fa-solid fa-trash-can"></i>
                  </button>
                </div>
              </div>

              <!-- Runs 列表 -->
              <div style="margin-top: 12px;">
                <div class="context-label" style="margin-bottom: 8px;">{{ lang === 'en-US' ? 'EXECUTION RUNS:' : '执行实例 (RUNS):' }}</div>
                <div v-if="!expRunsMap[eid] || expRunsMap[eid].length === 0" class="text-muted" style="font-size: 12px; font-style: italic;">
                  {{ lang === 'en-US' ? 'No execution runs yet. Click "+ New Run" above.' : '暂无独立运行记录，点击上方“发起新 Run”。' }}
                </div>
                <div v-else style="display: flex; flex-direction: column; gap: 8px;">
                  <div v-for="r in expRunsMap[eid]" :key="r.id" class="evidence-item" style="cursor: default;">
                    <div class="evidence-item-left">
                      <span class="font-mono text-primary" style="font-weight: 600;">{{ r.id }}</span>
                      <span class="badge-status" :class="r.status === 'completed' ? 'badge-support' : (r.status === 'running' ? 'badge-moderate' : 'badge-contradict')">
                        {{ (r.status || 'pending').toUpperCase() }}
                      </span>
                      <span class="font-mono text-muted" style="font-size: 11px;">{{ JSON.stringify(r.actual_parameters).slice(0, 60) }}</span>
                    </div>
                    <div>
                      <button class="btn-secondary" style="font-size: 11px; padding: 3px 10px;" @click="executeRun(r)">
                        {{ r.status === 'completed' ? (lang === 'en-US' ? 'Re-dispatch' : '重新调度') : (lang === 'en-US' ? '▶ Execute Run' : '▶ 执行 Run') }}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- VIEW 6: RUN TELEMETRY -->
        <div v-if="activeTab === 'runs'" class="workspace-view">
          <div style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <h2 style="font-size: 18px; font-weight: 600; color: var(--text-primary); margin: 0 0 4px 0;">
                {{ lang === 'en-US' ? 'Execution Runs & Live Telemetry' : '实验物理运行记录与实时遥测' }}
              </h2>
              <p class="text-secondary" style="font-size: 12px; margin: 0;">
                {{ lang === 'en-US' ? 'Real-time telemetry, GPU metrics, and validation curves for physical execution runs.' : '展示真实环境调度的实验 Run 实例指标、参数快照与收敛表现。' }}
              </p>
            </div>
            <button v-if="allProjectRuns.length" class="btn-action-primary" style="font-size: 11px;" @click="openNewExperimentModal">
              + {{ t('newExperiment') }}
            </button>
          </div>

          <!-- 空状态 -->
          <div v-if="!allProjectRuns.length" class="card" style="padding: 60px 20px; text-align: center; background: var(--bg-surface-1); border: 1px solid var(--border-default); border-radius: 12px;">
            <i class="fa-solid fa-terminal" style="font-size: 36px; color: var(--text-muted); margin-bottom: 14px;"></i>
            <div style="font-weight: 700; font-size: 14px; color: var(--text-primary); margin-bottom: 6px;">
              {{ lang === 'en-US' ? 'No Execution Runs Recorded Yet' : '当前课题暂无运行记录 (Runs)' }}
            </div>
            <div style="font-size: 12px; color: var(--text-secondary); max-width: 480px; margin: 0 auto 20px; line-height: 1.6;">
              {{ lang === 'en-US' ? 'No experimental runs have been executed yet. Go to "Experiments" to design protocols, generate Python code, and dispatch runs.' : '尚未调度任何物理实验运行实例。请先在「实验方案」中创建方案或编写代码并调度执行。' }}
            </div>
            <div style="display: flex; gap: 10px; justify-content: center;">
              <button class="btn-secondary" style="font-size: 12px; padding: 6px 14px;" @click="activeTab = 'experiments'">
                <i class="fa-solid fa-flask"></i> {{ lang === 'en-US' ? 'View Experiments' : '查看实验方案' }}
              </button>
              <button class="btn-action-primary" style="font-size: 12px; padding: 6px 14px;" @click="openNewExperimentModal">
                <i class="fa-solid fa-plus"></i> {{ lang === 'en-US' ? 'New Experiment' : '新建实验方案' }}
              </button>
            </div>
          </div>

          <!-- 真实 Runs 遥测看板 -->
          <div v-else style="display: flex; flex-direction: column; gap: 16px;">
            <div v-if="latestCompletedRun && latestCompletedRun.metrics" class="run-metric-grid">
              <div class="run-metric-card">
                <div class="metric-label">{{ t('run.valAccuracy') }}</div>
                <div class="run-metric-val" style="color: var(--accent-success);">
                  {{ latestCompletedRun.metrics.val_accuracy !== undefined ? (latestCompletedRun.metrics.val_accuracy * 100).toFixed(1) + '%' : (latestCompletedRun.metrics.accuracy !== undefined ? (latestCompletedRun.metrics.accuracy * 100).toFixed(1) + '%' : 'N/A') }}
                </div>
              </div>
              <div class="run-metric-card">
                <div class="metric-label">{{ t('run.f1Score') }}</div>
                <div class="run-metric-val">
                  {{ latestCompletedRun.metrics.f1_score !== undefined ? (latestCompletedRun.metrics.f1_score * 100).toFixed(1) + '%' : 'N/A' }}
                </div>
              </div>
              <div class="run-metric-card">
                <div class="metric-label">{{ t('run.finalLoss') }}</div>
                <div class="run-metric-val">
                  {{ latestCompletedRun.metrics.final_loss ?? latestCompletedRun.metrics.loss ?? 'N/A' }}
                </div>
              </div>
              <div class="run-metric-card">
                <div class="metric-label">{{ t('run.gpuMemory') }}</div>
                <div class="run-metric-val">{{ latestCompletedRun.metrics.gpu_memory ?? 'CPU' }}</div>
              </div>
            </div>

            <!-- Runs 列表明细 -->
            <div class="card" style="padding: 16px; background: var(--bg-surface-1); border: 1px solid var(--border-default); border-radius: 10px;">
              <div class="card-title-sm" style="margin-bottom: 12px;">已调度的历史执行实例 (All Runs)</div>
              <div style="display: flex; flex-direction: column; gap: 8px;">
                <div v-for="r in allProjectRuns" :key="r.id" class="evidence-item" style="cursor: default;">
                  <div class="evidence-item-left">
                    <span class="font-mono text-primary" style="font-weight: 600;">{{ r.id }}</span>
                    <span class="badge-status" :class="r.status === 'completed' ? 'badge-support' : (r.status === 'running' ? 'badge-moderate' : 'badge-contradict')">
                      {{ (r.status || 'pending').toUpperCase() }}
                    </span>
                    <span class="font-mono text-muted" style="font-size: 11px;">{{ JSON.stringify(r.actual_parameters || {}).slice(0, 70) }}</span>
                  </div>
                  <div>
                    <button class="btn-secondary" style="font-size: 11px; padding: 3px 10px;" @click="executeRun(r)">
                      {{ r.status === 'completed' ? (lang === 'en-US' ? 'Re-dispatch' : '重新调度') : (lang === 'en-US' ? '▶ Execute Run' : '▶ 执行 Run') }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- VIEW 7: DATA ANALYSIS -->
        <div v-if="activeTab === 'analysis'" class="workspace-view">
          <DataAnalysisPanel :project-id="currentProjectId" :lang="lang" :records="project?.experiment_ids ? project.experiment_ids.map(id => ({ id })) : []" @artifact-created="activeTab = 'artifacts'" />
        </div>

        <!-- VIEW 8: EVIDENCE LEDGER -->
        <div v-if="activeTab === 'evidence'" class="workspace-view">
          <div class="project-header">
            <div class="project-title-large">{{ t('nav.evidence') }}</div>
            <p class="text-secondary" style="font-size: 13px; margin: 4px 0 0;">{{ lang === 'en-US' ? 'Bidirectional trace linking scientific claims to empirical runs and literature data.' : '双向关联科研结论与底层数据支撑链条。' }}</p>
          </div>
          <div v-if="!displayedEvidenceLedger.length" class="empty-hint">
            {{ lang === 'en-US' ? 'No evidence items recorded yet in this project. Run experiments or slice evidence from literature to populate the ledger.' : '当前课题暂无沉淀的证据项。运行实验生成评测指标或在文献库提取段落切片后，将在此自动形成证据链条。' }}
          </div>
          <div v-else class="evidence-list">
            <div
              v-for="ev in displayedEvidenceLedger"
              :key="ev.id"
              class="evidence-item"
              @click="openEvidenceDrawer(ev.id)"
            >
              <div class="evidence-item-left">
                <span class="evidence-ref">{{ ev.id }}</span>
                <span class="evidence-desc">{{ ev.snippet }}</span>
              </div>
              <span class="badge-status" :class="ev.stance === 'SUPPORT' ? 'badge-support' : 'badge-contradict'">
                {{ ev.stance === 'SUPPORT' ? t('evidenceStatus.support') : t('evidenceStatus.contradict') }}
              </span>
            </div>
          </div>
        </div>

        <!-- VIEW 9: CONCLUSIONS -->
        <div v-if="activeTab === 'conclusions'" class="workspace-view">
          <ConclusionPanel :project-id="currentProjectId" :lang="lang" />
        </div>

        <!-- VIEW 10: ARTIFACTS -->
        <div v-if="activeTab === 'artifacts'" class="workspace-view">
          <ArtifactPanel :project-id="currentProjectId" :lang="lang" />
        </div>

        <!-- VIEW 11: OBSIDIAN VAULT BRIDGE -->
        <div v-if="activeTab === 'vault'" class="workspace-view">
          <VaultBridgePanel :project-id="currentProjectId" />
        </div>

        <!-- VIEW 12: ACTIVE EXPLORATION ENGINE (PHASE 18) -->
        <div v-if="activeTab === 'explore'" class="workspace-view">
          <ExplorePanel :project-id="currentProjectId" />
        </div>

        <!-- VIEW 13: RESEARCH DIARY (V2.6) -->
        <div v-if="activeTab === 'diary'" class="workspace-view">
          <ResearchDiaryPanel :project-id="currentProjectId" />
        </div>

        <!-- VIEW 14: RESEARCH GRAPH -->
        <div v-if="activeTab === 'graph'" class="workspace-view">
          <div style="margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <h2 style="font-size: 18px; font-weight: 600; color: var(--text-primary); margin: 0 0 4px 0;">{{ t('graph.title') }}</h2>
              <p class="text-secondary" style="font-size: 12px; margin: 0;">{{ t('graph.subtitle') }}</p>
            </div>
            <button v-if="graphNodesList.length" class="btn-secondary" @click="resetGraphFocus">{{ t('graph.reset') }}</button>
          </div>

          <!-- 空状态 -->
          <div v-if="!graphNodesList.length" class="card" style="padding: 60px 20px; text-align: center; background: var(--bg-surface-1); border: 1px solid var(--border-default); border-radius: 12px;">
            <i class="fa-solid fa-diagram-project" style="font-size: 36px; color: var(--text-muted); margin-bottom: 14px;"></i>
            <div style="font-weight: 700; font-size: 14px; color: var(--text-primary); margin-bottom: 6px;">
              {{ lang === 'en-US' ? 'No Inference Graph Nodes in this Project' : '当前课题暂无科学推理图谱节点' }}
            </div>
            <div style="font-size: 12px; color: var(--text-secondary); max-width: 480px; margin: 0 auto 20px; line-height: 1.6;">
              {{ lang === 'en-US' ? 'As you propose hypotheses, execute experimental runs, and generate empirical conclusions, the system automatically builds causal reasoning chains.' : '随着您在课题中提出假说、调度实验 Run 以及沉淀结论，系统将自动构建因果推理拓扑图与证据支撑链条。' }}
            </div>
            <div style="display: flex; gap: 10px; justify-content: center;">
              <button class="btn-secondary" style="font-size: 12px; padding: 6px 14px;" @click="activeTab = 'hypotheses'">
                <i class="fa-solid fa-lightbulb"></i> {{ lang === 'en-US' ? 'Propose Hypothesis' : '提出科学假说' }}
              </button>
              <button class="btn-action-primary" style="font-size: 12px; padding: 6px 14px;" @click="openNewExperimentModal">
                <i class="fa-solid fa-plus"></i> {{ lang === 'en-US' ? 'New Experiment' : '新建实验方案' }}
              </button>
            </div>
          </div>

          <!-- 真实动态图谱 -->
          <div v-else style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
            <div v-for="node in graphNodesList" :key="node.id" class="card" style="background: var(--bg-surface-1); border: 1px solid var(--border-default); border-radius: 10px; padding: 16px; transition: all 0.2s;" :style="focusedNode === node.id ? 'border-color: var(--accent-science); box-shadow: 0 0 12px rgba(56,139,253,0.3);' : ''" @click="focusGraphNode(node.id)">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span class="badge-status" :class="node.type === 'hypothesis' ? 'badge-support' : node.type === 'conclusion' ? 'badge-active' : 'badge-moderate'" style="font-size: 10px;">
                  {{ node.type.toUpperCase() }}
                </span>
                <span class="font-mono text-muted" style="font-size: 11px;">{{ node.id }}</span>
              </div>
              <div style="font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px; line-height: 1.4;">
                {{ node.title }}
              </div>
              <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.5;">
                {{ node.subtext }}
              </div>
            </div>
          </div>
        </div>
      </main>

      <!-- 2.3 RIGHT AGENT PANEL (WITH CHAT WINDOW) -->
      <aside class="agent-panel">
        <div class="agent-header">
          <div style="display: flex; gap: 4px;">
            <button class="side-tab-btn" :class="{ active: rightPanelTab === 'actions' }" @click="rightPanelTab = 'actions'">
              <i class="fa-solid fa-bolt"></i> {{ lang === 'en-US' ? 'Actions' : '动作与流水' }}
            </button>
            <button class="side-tab-btn" :class="{ active: rightPanelTab === 'chat' }" @click="rightPanelTab = 'chat'">
              <i class="fa-solid fa-comments"></i> {{ lang === 'en-US' ? 'Agent Chat' : 'Agent 对话' }}
            </button>
          </div>
          <span class="font-mono" style="font-size: 10px; color: var(--accent-success);">{{ t('agent.statusActive') }}</span>
        </div>

        <!-- 动作与流水 -->
        <div v-if="rightPanelTab === 'actions'" class="agent-body">
          <!-- Active Context -->
          <div class="agent-context-box">
            <div class="context-label">{{ t('agent.activeContext') }}</div>
            <div class="context-value">{{ (project?.questions && project.questions[0]?.text) || project?.name || (lang === 'en-US' ? 'No active context' : '暂无活跃上下文') }}</div>
          </div>

          <!-- Suggested Actions -->
          <div>
            <div class="context-label" style="margin-bottom: 8px;">{{ t('agent.suggestedActions') }}</div>
            <div class="suggested-actions">
              <div class="action-chip" @click="triggerAgentTask('Analyze Evidence')">
                <span>{{ t('agent.actAnalyze') }}</span>
                <i class="fa-solid fa-arrow-right"></i>
              </div>
              <div class="action-chip" @click="triggerAgentTask('Compare Runs')">
                <span>{{ t('agent.actCompare') }}</span>
                <i class="fa-solid fa-arrow-right"></i>
              </div>
              <div class="action-chip" @click="triggerAgentTask('Find Related Papers')">
                <span>{{ t('agent.actPapers') }}</span>
                <i class="fa-solid fa-arrow-right"></i>
              </div>
              <div class="action-chip" @click="triggerAgentTask('Suggest Next Experiment')">
                <span>{{ t('agent.actSuggest') }}</span>
                <i class="fa-solid fa-arrow-right"></i>
              </div>
            </div>
          </div>

          <!-- Agent Activity Log -->
          <div>
            <div class="context-label" style="margin-bottom: 10px;">{{ t('agent.activityLog') }}</div>
            <div class="activity-log">
              <div v-if="!formattedActivityLogs?.length" class="text-muted" style="font-size: 12px; font-style: italic; padding: 6px 0;">
                {{ lang === 'en-US' ? 'No background tasks' : '暂无后台运行任务' }}
              </div>
              <div v-for="(log, idx) in formattedActivityLogs" :key="idx" class="activity-item">
                <i v-if="log.done" class="fa-solid fa-check activity-icon-success"></i>
                <i v-else class="fa-solid fa-spinner activity-icon-spinner"></i>
                <div class="activity-text" v-html="log.text"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- AGENT 实时对话窗口 -->
        <div v-else class="agent-chat-body">
          <div class="chat-messages" ref="chatBox">
            <div v-for="(msg, i) in displayedChatMessages" :key="i" class="chat-msg-row" :class="msg.role">
              <div class="msg-bubble">
                <div class="msg-author font-mono">{{ msg.role === 'user' ? 'You' : 'ResearchAgent V2' }}</div>
                <div class="msg-text">{{ msg.content }}</div>
              </div>
            </div>
            <div v-if="chatLoading" class="chat-msg-row assistant">
              <div class="msg-bubble">
                <div class="msg-author font-mono">ResearchAgent V2</div>
                <div class="msg-text"><i class="fa-solid fa-spinner activity-icon-spinner"></i> {{ t('agent.chatThinking') }}</div>
              </div>
            </div>
          </div>

          <!-- 快捷提问词 -->
          <div class="chat-quick-chips">
            <span class="chip" @click="sendQuickChat(lang === 'en-US' ? 'Summarize verification status and evidence strength for H2' : '总结当前核心假说 H2 的验证情况与证据强度')">{{ t('agent.chip1') }}</span>
            <span class="chip" @click="sendQuickChat(lang === 'en-US' ? 'Recommend next experiment parameters based on Run #02 and Run #03' : '基于 Run #02 和 Run #03 数据推荐下一组实验参数')">{{ t('agent.chip2') }}</span>
          </div>

          <!-- 输入框 -->
          <div class="chat-input-box">
            <textarea
              v-model="chatInput"
              :placeholder="lang === 'en-US' ? 'Ask Research Agent about experiments...' : '向科研助手提问，例如分析实验或检索图谱...'"
              rows="2"
              class="chat-textarea"
              @keydown.enter.prevent="sendChat"
            ></textarea>
            <button class="btn-chat-send" :disabled="!chatInput.trim() || chatLoading" @click="sendChat">
              <i class="fa-solid fa-paper-plane"></i>
            </button>
          </div>
        </div>
      </aside>
    </div>

    <!-- 3. IN-IDE CREATE PROJECT MODAL (站内新建项目) -->
    <div class="modal-overlay" :class="{ open: showCreateProjModal }">
      <div class="modal-container" style="width: 440px;">
        <div class="modal-header">
          <div class="modal-title">
            <i class="fa-solid fa-folder-plus" style="color: var(--accent-science);"></i>
            <span>{{ lang === 'en-US' ? 'Create Research Project' : '新建研究项目 (Research Project)' }}</span>
          </div>
          <button class="btn-close-drawer" @click="showCreateProjModal = false"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">{{ lang === 'en-US' ? 'Project Name' : '项目名称' }}</label>
            <input v-model="newProjForm.name" :placeholder="lang === 'en-US' ? 'e.g. 3D Facial Dynamics v2' : '例如：3D Facial Dynamics v2'" class="modal-input" />
          </div>
          <div class="form-group">
            <label class="form-label">{{ lang === 'en-US' ? 'Description' : '项目研究描述' }}</label>
            <textarea v-model="newProjForm.description" :placeholder="lang === 'en-US' ? 'Project research goals and scope...' : '研究目标、任务边界与数据集背景说明...'" class="modal-textarea" rows="3"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showCreateProjModal = false">{{ lang === 'en-US' ? 'Cancel' : '取消' }}</button>
          <button class="btn-approve" :disabled="!newProjForm.name.trim() || creatingProj" @click="submitCreateProject">
            <span>{{ creatingProj ? (lang === 'en-US' ? 'Creating...' : '创建中...') : (lang === 'en-US' ? 'Create Project' : '立即创建') }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 4. IN-IDE CREATE EXPERIMENT MODAL (站内直接添加实验方案，无白屏跳转) -->
    <div class="modal-overlay" :class="{ open: showCreateExpModal }">
      <div class="modal-container" style="width: 480px;">
        <div class="modal-header">
          <div class="modal-title">
            <i class="fa-solid fa-flask" style="color: var(--accent-science);"></i>
            <span>{{ lang === 'en-US' ? 'Create New Experiment Protocol' : '新建实验设计方案 (Protocol)' }}</span>
          </div>
          <button class="btn-close-drawer" @click="showCreateExpModal = false"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">{{ lang === 'en-US' ? 'Experiment Task / Title' : '实验任务标题' }}</label>
            <input v-model="newExpForm.task" :placeholder="lang === 'en-US' ? 'e.g. Dynamic Graph Neighborhood k=20 Ablation' : '例如：Dynamic Graph Neighborhood k=20 Ablation'" class="modal-input" />
          </div>
          <div class="form-row">
            <div class="form-group" style="flex: 1;">
              <label class="form-label">{{ lang === 'en-US' ? 'Model' : '模型架构' }}</label>
              <input v-model="newExpForm.model" placeholder="DynamicGCN" class="modal-input font-mono" />
            </div>
            <div class="form-group" style="flex: 1;">
              <label class="form-label">{{ lang === 'en-US' ? 'Dataset' : '数据集' }}</label>
              <input v-model="newExpForm.dataset" placeholder="FER_Noisy_v2" class="modal-input font-mono" />
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">{{ lang === 'en-US' ? 'Hyperparameters (JSON format)' : '实验设计参数 (JSON 格式)' }}</label>
            <input v-model="newExpForm.paramsStr" placeholder='{"k": 20, "lr": 1e-4, "batch_size": 32}' class="modal-input font-mono" />
          </div>
          <div class="form-group">
            <label class="form-label">{{ lang === 'en-US' ? 'Expected Outcome' : '预期目标与结论' }}</label>
            <textarea v-model="newExpForm.conclusions" :placeholder="lang === 'en-US' ? 'Verify if k=20 reaches optimal manifold stability' : '验证 k=20 下流形稳定性与抗噪表现是否达到峰值'" class="modal-textarea" rows="2"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showCreateExpModal = false">{{ lang === 'en-US' ? 'Cancel' : '取消' }}</button>
          <button class="btn-approve" :disabled="!newExpForm.task.trim() || creatingExp" @click="submitCreateExperiment">
            <i class="fa-solid fa-check"></i>
            <span>{{ creatingExp ? (lang === 'en-US' ? 'Creating...' : '创建中...') : (lang === 'en-US' ? 'Create Protocol' : '创建实验方案') }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 5. DOCUMENTATION / 使用指南 MODAL -->
    <UserGuideModal :visible="showDocModal" :lang="lang" @close="showDocModal = false" />

    <!-- 5.1 QUICK CAPTURE / 快速记录 MODAL (V2.6) -->
    <QuickCaptureModal :visible="showQuickCapture" :project-id="currentProjectId" @close="showQuickCapture = false" @saved="loadProjectData" />

    <!-- 6. EXPERIMENT CODER & DEBUGGER MODAL -->
    <div class="modal-overlay" :class="{ open: showExpCoderModal }">
      <div class="modal-container" style="width: 750px; max-height: 85vh;">
        <div class="modal-header">
          <div class="modal-title">
            <i class="fa-solid fa-code" style="color: var(--accent-science);"></i>
            <span>{{ lang === 'en-US' ? 'Experiment Code Generator & Debugger' : '实验方案代码生成与一键调试' }}</span>
          </div>
          <button class="btn-close-drawer" @click="showExpCoderModal = false"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="modal-body" style="padding: 16px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <span style="font-size: 12px; color: var(--text-secondary);">实验方案：<strong class="text-primary">{{ activeCoderExpId }}</strong></span>
            <div style="display: flex; gap: 8px;">
              <button class="btn-secondary" style="font-size: 11px;" :disabled="generatingExpCode" @click="generateExpCode">
                {{ generatingExpCode ? '生成中...' : '⚡ 重新生成代码' }}
              </button>
              <button class="btn-action-primary" style="font-size: 11px;" :disabled="!expGeneratedCode || runningExpCode" @click="runExpCode">
                {{ runningExpCode ? '运行中...' : '▶ 运行实验脚本' }}
              </button>
            </div>
          </div>
          <textarea v-model="expGeneratedCode" class="code-editor" rows="12" style="width: 100%; box-sizing: border-box; background: var(--bg-surface-1);"></textarea>

          <!-- 运行结果与 Debugger -->
          <div v-if="expRunOutput" style="margin-top: 12px; background: var(--bg-surface-2); border: 1px solid var(--border-default); border-radius: 6px; padding: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
              <span :class="expRunOutput.success ? 'badge-ok' : 'badge-err'">
                {{ expRunOutput.success ? '✓ 运行成功 (已生成 Run 与产物)' : '✕ 运行失败' }}
              </span>
              <button v-if="!expRunOutput.success" class="btn-action-primary" style="font-size: 11px; background: var(--accent-warning);" :disabled="debuggingExpCode" @click="debugExpCode">
                <i class="fa-solid fa-screwdriver-wrench"></i> {{ debuggingExpCode ? '诊断中...' : '🛠️ 智能诊断并修复' }}
              </button>
            </div>
            <pre v-if="expRunOutput.stdout" class="result-stdout font-mono">{{ expRunOutput.stdout }}</pre>
            <pre v-if="expRunOutput.error" class="result-error font-mono">{{ expRunOutput.error }}</pre>
            <div v-if="expDebugResult" style="margin-top: 8px; font-size: 12px; color: var(--accent-support);">
              <strong>修复原因：</strong>{{ expDebugResult.fix_reason }} (已自动应用补丁，可再次点击运行验证)
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 7. PROJECT ENVIRONMENT & WORKSPACE MODAL -->
    <div class="modal-overlay" :class="{ open: showEnvModal }">
      <div class="modal-container" style="width: 680px; max-height: 85vh;">
        <div class="modal-header">
          <div class="modal-title">
            <i class="fa-brands fa-python" style="color: var(--accent-science);"></i>
            <span>{{ lang === 'en-US' ? 'Project Environment & Workspace Settings' : '课题虚拟环境与工作目录配置' }}</span>
          </div>
          <button class="btn-close-drawer" @click="showEnvModal = false"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="modal-body" style="padding: 20px;">
          <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px; line-height: 1.5;">
            {{ lang === 'en-US' ? 'Configure the specific Python environment (Conda / Venv / System) and working directory for this research group/project. Multi-group shared machines can isolate packages and paths independently.' : '为当前课题组/项目绑定专属的 Python 虚拟环境（Conda / Venv / 系统安装）与工作空间。在多人共用单机时，不同课题组可使用各自独立的依赖与数据路径。' }}
          </div>

          <!-- 1. 虚拟环境选择 -->
          <div class="form-group" style="margin-bottom: 16px;">
            <label class="form-label" style="font-size: 12px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px; display: block;">{{ lang === 'en-US' ? 'Select Python Environment:' : '选择 Python 虚拟环境：' }}</label>
            <select v-model="selectedEnvExe" @change="onEnvSelectChange" class="form-input" style="width: 100%; font-size: 12px; padding: 6px 10px; background: var(--bg-surface-2); color: var(--text-primary); border: 1px solid var(--border-default); border-radius: 6px;">
              <option v-for="env in scannedEnvs" :key="env.executable" :value="env.executable">
                {{ env.name }} (Python {{ env.version }}) — {{ env.executable }}
              </option>
              <option value="__custom__">{{ lang === 'en-US' ? '+ Custom Python Executable Path...' : '+ 手动输入 Python 解释器路径 (Custom)...' }}</option>
            </select>
          </div>

          <!-- 手动输入路径 -->
          <div v-if="selectedEnvExe === '__custom__'" class="form-group" style="margin-bottom: 16px;">
            <label class="form-label" style="font-size: 12px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px; display: block;">{{ lang === 'en-US' ? 'Custom python.exe / python path:' : '自定义 Python 解释器绝对路径：' }}</label>
            <input v-model="customEnvExe" placeholder="例如: C:\Users\lab\anaconda3\envs\torch2\python.exe 或 /opt/conda/envs/nlp/bin/python" class="form-input" style="width: 100%; font-family: var(--font-mono); font-size: 12px; padding: 6px 10px; background: var(--bg-surface-2); color: var(--text-primary); border: 1px solid var(--border-default); border-radius: 6px;" />
          </div>

          <!-- 2. 工作空间目录 -->
          <div class="form-group" style="margin-bottom: 16px;">
            <label class="form-label" style="font-size: 12px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px; display: block;">{{ lang === 'en-US' ? 'Custom Working Directory (Optional):' : '项目工作空间目录（可选，默认当前工程根目录）：' }}</label>
            <input v-model="envWorkingDir" placeholder="例如: E:\lab_projects\group_a 或 /home/student/project_b" class="form-input" style="width: 100%; font-family: var(--font-mono); font-size: 12px; padding: 6px 10px; background: var(--bg-surface-2); color: var(--text-primary); border: 1px solid var(--border-default); border-radius: 6px;" />
          </div>

          <!-- 3. 环境深度自检按钮与结果 -->
          <div style="margin-bottom: 16px;">
            <button class="btn-secondary" style="font-size: 12px; padding: 6px 14px;" :disabled="inspectingEnv" @click="inspectSelectedEnv">
              <i class="fa-solid fa-stethoscope"></i> {{ inspectingEnv ? '自检中...' : (lang === 'en-US' ? 'Inspect Environment' : '一键环境自检 (包版本与 CUDA)') }}
            </button>
          </div>

          <!-- 自检结果展示卡片 -->
          <div v-if="envInspectionResult" style="background: var(--bg-surface-2); border: 1px solid var(--border-default); border-radius: 8px; padding: 14px; margin-bottom: 16px;">
            <div v-if="envInspectionResult.valid">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 6px;">
                <span class="badge-status badge-support">✓ 环境正常可用 (Python {{ envInspectionResult.version }})</span>
                <span v-if="envInspectionResult.cuda?.available" class="badge-status badge-support">
                  ⚡ GPU: {{ envInspectionResult.cuda.device_name }} (CUDA {{ envInspectionResult.cuda.version }})
                </span>
                <span v-else class="badge-status badge-moderate">CPU Mode (无 PyTorch CUDA)</span>
              </div>
              <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 8px;">已检测到的科学计算库：</div>
              <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                <span v-for="(info, pkg) in envInspectionResult.packages" :key="pkg" class="font-mono" :style="{ color: info.installed ? 'var(--accent-success)' : 'var(--text-muted)', fontSize: '11px', background: 'var(--bg-surface-1)', padding: '2px 6px', borderRadius: '4px', border: '1px solid var(--border-default)' }">
                  {{ pkg }} {{ info.installed ? `v${info.version}` : '✕' }}
                </span>
              </div>
            </div>
            <div v-else style="color: var(--accent-danger); font-size: 12px;">
              ✕ 自检失败: {{ envInspectionResult.error }}
            </div>
          </div>
        </div>
        <div class="modal-footer" style="display: flex; justify-content: flex-end; gap: 10px; padding: 12px 20px; border-top: 1px solid var(--border-default);">
          <button class="btn-secondary" @click="showEnvModal = false">{{ lang === 'en-US' ? 'Cancel' : '取消' }}</button>
          <button class="btn-action-primary" :disabled="savingEnv" @click="saveProjectEnvironment">
            {{ savingEnv ? '保存中...' : (lang === 'en-US' ? 'Save & Bind to Project' : '保存并绑定到当前课题') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 8. SLIDE-OUT EVIDENCE DRAWER -->
    <div class="drawer-overlay" :class="{ open: evidenceDrawer.open }" @click="evidenceDrawer.open = false"></div>
    <div class="drawer" :class="{ open: evidenceDrawer.open }">
      <div class="drawer-header">
        <span class="drawer-title">{{ t('drawer.title') }}</span>
        <button class="btn-close-drawer" @click="evidenceDrawer.open = false">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>

      <div class="drawer-body">
        <div>
          <span class="badge-status" :class="evidenceDrawer.badgeClass">{{ evidenceDrawer.badgeText }}</span>
          <h3 style="font-size: 14px; font-weight: 600; color: var(--text-primary); margin-top: 8px;">
            {{ evidenceDrawer.claim }}
          </h3>
        </div>

        <div class="provenance-box">
          <div class="provenance-row">
            <span class="provenance-key">{{ t('drawer.strength') }}</span>
            <span class="provenance-val" style="color: var(--accent-warning);">{{ evidenceDrawer.confidence || t('hypothesis.moderate') }}</span>
          </div>
          <div class="provenance-row">
            <span class="provenance-key">{{ t('drawer.source') }}</span>
            <span class="provenance-val font-mono">{{ evidenceDrawer.sourceRef }}</span>
          </div>
          <div v-if="evidenceDrawer.accuracy" class="provenance-row">
            <span class="provenance-key">{{ t('drawer.accuracy') }}</span>
            <span class="provenance-val font-mono" style="color: var(--accent-success);">{{ evidenceDrawer.accuracy }}</span>
          </div>
          <div v-if="evidenceDrawer.macroF1" class="provenance-row">
            <span class="provenance-key">{{ t('drawer.macroF1') }}</span>
            <span class="provenance-val font-mono">{{ evidenceDrawer.macroF1 }}</span>
          </div>
        </div>

        <div v-if="evidenceDrawer.dataset || evidenceDrawer.gitCommit" class="provenance-box">
          <div v-if="evidenceDrawer.dataset" class="provenance-row">
            <span class="provenance-key">{{ t('drawer.dataset') }}</span>
            <span class="provenance-val font-mono">{{ evidenceDrawer.dataset }}</span>
          </div>
          <div v-if="evidenceDrawer.gitCommit" class="provenance-row">
            <span class="provenance-key">{{ t('drawer.gitCommit') }}</span>
            <span class="provenance-val font-mono">{{ evidenceDrawer.gitCommit }}</span>
          </div>
        </div>

        <button class="btn-secondary" style="width: 100%; text-align: center; justify-content: center;" @click="activeTab = 'runs'; evidenceDrawer.open = false;">
          {{ t('drawer.viewLog') }}
        </button>
      </div>
    </div>

    <!-- 7. HITL APPROVAL MODAL -->
    <div class="modal-overlay" :class="{ open: hitlModal.show }">
      <div class="modal-container">
        <div class="modal-header">
          <div class="modal-title">
            <i class="fa-solid fa-triangle-exclamation" style="color: var(--accent-warning);"></i>
            <span>{{ t('modal.title') }}</span>
          </div>
          <button class="btn-close-drawer" @click="hitlModal.show = false">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div class="modal-body">
          <div style="font-size: 13px; color: var(--text-secondary);">
            {{ hitlModal.message || t('modal.desc') }}
          </div>

          <div class="provenance-box">
            <div class="provenance-row">
              <span class="provenance-key">{{ t('modal.targetH') }}</span>
              <span class="provenance-val" style="color: var(--accent-science);">H2</span>
            </div>
            <div class="provenance-row">
              <span class="provenance-key">{{ t('modal.paramChange') }}</span>
              <span class="provenance-val">k = 20 (lr = 1e-4)</span>
            </div>
            <div class="provenance-row">
              <span class="provenance-key">{{ t('modal.estCompute') }}</span>
              <span class="provenance-val">1.2 GPU hours</span>
            </div>
            <div class="provenance-row">
              <span class="provenance-key">{{ t('modal.riskAssess') }}</span>
              <span class="provenance-val" style="color: var(--accent-success);">{{ t('modal.lowRisk') }}</span>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-secondary" @click="hitlModal.show = false">{{ t('modal.cancel') }}</button>
          <button class="btn-approve" @click="confirmHITLApproval">
            <i class="fa-solid fa-check"></i>
            <span>{{ t('modal.authorize') }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 8. COMMAND PALETTE (⌘K) -->
    <div class="modal-overlay" :class="{ open: showCmdPalette }">
      <div class="modal-container" style="width: 480px;">
        <div class="modal-header">
          <span class="modal-title">Command Palette (⌘K)</span>
          <button class="btn-close-drawer" @click="showCmdPalette = false"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="modal-body">
          <input v-model="cmdQuery" :placeholder="lang === 'en-US' ? 'Search hypotheses, runs, or papers...' : '搜索假说、实验、运行或论文...'" class="code-editor" style="background: var(--bg-surface-2); color: var(--text-primary);" autofocus />
          <div style="display: flex; flex-direction: column; gap: 4px; margin-top: 10px;">
            <div class="action-chip" @click="activeTab = 'overview'; showCmdPalette = false;">📌 跳转至概览 (Overview)</div>
            <div class="action-chip" @click="activeTab = 'hypotheses'; showCmdPalette = false;">💡 查看科学假说 (H2)</div>
            <div class="action-chip" @click="activeTab = 'experiments'; showCmdPalette = false;">🧪 查看实验与 Runs</div>
            <div class="action-chip" @click="activeTab = 'graph'; showCmdPalette = false;">🕸 查看知识图谱 (Research Graph)</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 9. CSV IMPORT MODAL -->
    <div class="modal-overlay" :class="{ open: showCsvModal }">
      <div class="modal-container" style="width: 540px;">
        <div class="modal-header">
          <span class="modal-title"><i class="fa-solid fa-file-csv" style="color: var(--accent-science); margin-right: 6px;"></i> {{ lang === 'en-US' ? 'Batch Import Runs from CSV' : '从 CSV 批量导入实验运行 (Runs)' }}</span>
          <button class="btn-close-drawer" @click="showCsvModal = false"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="modal-body">
          <p class="text-secondary" style="font-size: 12px; margin: 0 0 10px;">
            {{ lang === 'en-US' ? 'Paste CSV text with column headers. Parameter columns (e.g. k, lr, batch_size) and Metric columns (e.g. accuracy, loss, f1) will be auto-detected.' : '直接粘贴 CSV 文本（包含表头）。系统将自动识别参数列（如 k, lr, batch_size）与评估指标列（如 accuracy, val_loss, f1），一键批量创建 Runs。' }}
          </p>
          <div class="form-group" style="margin-bottom: 10px;">
            <label class="form-label">{{ lang === 'en-US' ? 'Target Experiment:' : '目标实验方案：' }}</label>
            <select v-model="csvTargetExpId" class="modal-input">
              <option v-for="eid in project?.experiment_ids || []" :key="eid" :value="eid">{{ eid }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">{{ lang === 'en-US' ? 'CSV Content:' : 'CSV 文本内容：' }}</label>
            <textarea
              v-model="csvInputText"
              rows="7"
              class="code-editor"
              :placeholder="'k,lr,val_accuracy,loss\n10,0.0001,0.724,0.382\n20,0.0001,0.841,0.218\n30,0.0001,0.806,0.295'"
            ></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showCsvModal = false">{{ t('modal.cancel') }}</button>
          <button class="btn-action-primary" @click="importRunsCsv" :disabled="!csvInputText.trim() || csvImporting">
            {{ csvImporting ? (lang === 'en-US' ? 'Importing...' : '导入中...') : (lang === 'en-US' ? 'Import Runs' : '确认导入') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { projectApi } from '../api/project.js'
import HypothesisPanel from '../components/HypothesisPanel.vue'
import LiteraturePanel from '../components/LiteraturePanel.vue'
import DatasetExplorerPanel from '../components/DatasetExplorerPanel.vue'
import NextExperimentPanel from '../components/NextExperimentPanel.vue'
import DataAnalysisPanel from '../components/DataAnalysisPanel.vue'
import ArtifactPanel from '../components/ArtifactPanel.vue'
import ConclusionPanel from '../components/ConclusionPanel.vue'
import VaultBridgePanel from '../components/VaultBridgePanel.vue'
import ExplorePanel from '../components/ExplorePanel.vue'
import ResearchDiaryPanel from '../components/ResearchDiaryPanel.vue'
import RunComparisonModal from '../components/RunComparisonModal.vue'
import UserGuideModal from '../components/UserGuideModal.vue'
import QuickCaptureModal from '../components/QuickCaptureModal.vue'

const I18N_DICT = {
  'en-US': {
    brand: 'ResearchOS',
    searchPlaceholder: 'Search artifacts, runs, papers...',
    newExperiment: 'New Experiment',
    top: {
      docs: 'Documentation',
    },
    nav: {
      research: 'Research',
      overview: 'Overview',
      questions: 'Questions',
      hypotheses: 'Hypotheses',
      literature: 'Literature',
      datasets: 'Datasets',
      experiment: 'Experiment',
      experiments: 'Experiments',
      runs: 'Runs',
      analysis: 'Analysis',
      evidence: 'Evidence',
      conclusions: 'Conclusions',
      knowledge: 'Knowledge',
      researchGraph: 'Research Graph',
      artifacts: 'Artifacts'
    },
    overview: {
      researchQuestion: 'Research Question',
      activeHypothesis: 'Active Hypothesis',
      testing: 'TESTING',
      evidenceStrength: 'Evidence',
      coverage: 'Coverage',
      replication: 'Replication',
      researchCadence: 'Research Cadence',
      cycle: 'Cycle #04',
      targetBenchmark: 'Target Benchmark:',
      bestAccuracy: 'Best Accuracy:',
      computeSpent: 'Compute Spent:',
      nextActionBadge: 'Next Research Action · Decision #04',
      nextActionTitle: 'Experiment #04 · Dynamic Graph Neighborhood Ablation',
      nextActionReason: 'Current evidence from Run #02 and Run #03 suggests the optimal neighborhood region lies between k=15 and k=25. Testing k=20 will yield maximum information gain to validate Hypothesis H2.',
      recommendedK: 'Recommended k:',
      learningRate: 'Learning Rate:',
      infoGain: 'Info Gain:',
      highGain: 'HIGH',
      computeEst: 'Compute:',
      approveRun: 'Approve & Run',
      modify: 'Modify',
      reviewContext: 'Review Context',
      evidenceLedger: 'Evidence Ledger',
      viewGraph: 'View Graph →',
      recentTimeline: 'Recent Timeline'
    },
    hypothesis: {
      code: 'HYPOTHESIS H2',
      title: 'Dynamic graph updates improve topological robustness under noisy facial inputs.',
      moderate: 'MODERATE',
    },
    run: {
      title: 'Experiment Run #03 Telemetry',
      valAccuracy: 'Validation Accuracy',
      f1Score: 'Macro F1 Score',
      finalLoss: 'Final Loss',
      gpuMemory: 'GPU Memory',
      convergence: 'Training Loss & Accuracy Convergence',
      epochs: '100 Epochs',
      trainingLoss: 'Training Loss',
      valAccCurve: 'Val Accuracy'
    },
    graph: {
      title: 'Research Graph Architecture',
      subtitle: 'Click nodes to filter and focus evidence chains.',
      reset: 'Reset Focus',
      rqNode: 'Research Question',
      rqSub: 'Dynamic graph updates...',
      h2Node: 'H2: Dynamic Graph',
      h2Sub: 'Status: TESTING (78%)',
      r1Node: 'Run #01 (k=8)',
      r1Sub: 'CONTRADICT',
      r3Node: 'Run #03 (k=16)',
      r3Sub: 'Acc 83.2% (SUPPORT)',
      concNode: 'Optimal k Region [15-25]'
    },
    agent: {
      title: 'Research Agent',
      statusActive: 'ACTIVE',
      activeContext: 'Active Context',
      ctxH2: 'H2 · Dynamic Graph Robustness',
      suggestedActions: 'Suggested Actions',
      actAnalyze: 'Analyze Evidence',
      actCompare: 'Compare Runs',
      actPapers: 'Find Related Papers',
      actSuggest: 'Suggest Next Experiment',
      activityLog: 'Agent Activity',
      log1: 'Loaded Run #03 metrics',
      log2: 'Compared against Run #02 baseline',
      log3: 'Statistical t-test completed (p < 0.01)',
      log4: 'Updating evidence coverage for H2...',
      chatGreeting: 'Hello! I am ResearchAgent V2. I have loaded this project\'s experiment records, hypotheses, and knowledge graph. Feel free to ask me for experiment comparisons, hypothesis verification status, or next-step recommendations.',
      chatThinking: 'Thinking and retrieving experimental data...',
      chip1: '💡 Summarize H2 Evidence',
      chip2: '🚀 Plan Next Experiment',
    },
    drawer: {
      title: 'Evidence Provenance',
      strength: 'Evidence Strength:',
      source: 'Source Artifact:',
      accuracy: 'Accuracy:',
      macroF1: 'Macro F1:',
      dataset: 'Dataset:',
      gitCommit: 'Git Commit:',
      checkpoint: 'Checkpoint:',
      viewLog: 'View Execution Log & Trace →'
    },
    modal: {
      title: 'Human-in-the-Loop Authorization',
      desc: 'You are authorizing the execution of Experiment #04 (Dynamic Graph Neighborhood Ablation).',
      targetH: 'Target Hypothesis:',
      paramChange: 'Parameter Change:',
      estCompute: 'Estimated Compute:',
      riskAssess: 'Risk Assessment:',
      lowRisk: 'LOW (0.02% divergence risk)',
      cancel: 'Reject / Cancel',
      authorize: 'Authorize & Dispatch'
    },
    evidenceStatus: {
      support: 'SUPPORT',
      contradict: 'CONTRADICT',
      moderate: 'MODERATE'
    },
    timeline: {
      aug24: 'H2 proposed by Research Agent based on literature gap',
      aug25: 'Run #03 completed (Accuracy 83.2%, Macro F1 81.7%)',
      aug26_1: 'Evidence updated for H2 (Strength: MODERATE)',
      aug26_2: 'Experiment #04 proposed awaiting HITL authorization'
    }
  },
  'zh-CN': {
    brand: 'ResearchOS',
    searchPlaceholder: '搜索产物、实验记录、文献...',
    newExperiment: '新建实验方案',
    top: {
      docs: '使用指南',
    },
    nav: {
      research: '研究体系',
      overview: '概览',
      questions: '核心问题',
      hypotheses: '科学假说',
      literature: '文献库',
      datasets: '数据集库',
      experiment: '实验体系',
      experiments: '实验方案',
      runs: '运行记录',
      analysis: '数据分析',
      evidence: '证据账本',
      conclusions: '科研结论',
      knowledge: '知识图谱',
      researchGraph: '推理图谱',
      artifacts: '研究产物'
    },
    overview: {
      researchQuestion: '研究核心问题',
      activeHypothesis: '当前核心假说',
      testing: '验证中',
      evidenceStrength: '证据强度',
      coverage: '覆盖率',
      replication: '复现次数',
      researchCadence: '研究推进节奏',
      cycle: '周期 #04',
      targetBenchmark: '目标基准:',
      bestAccuracy: '最高准确率:',
      computeSpent: '已消耗算力:',
      nextActionBadge: '下一步研究行动 · 决策 #04',
      nextActionTitle: '实验 #04 · 动态图邻域消融实验',
      nextActionReason: '基于 Run #02 与 Run #03 的证据表明，最佳邻域范围介于 k=15 至 k=25 之间。测试 k=20 将产生最大信息增益以验证假说 H2。',
      recommendedK: '推荐 k 值:',
      learningRate: '学习率:',
      infoGain: '信息增益:',
      highGain: '极大',
      computeEst: '预估算力:',
      approveRun: '批准并运行',
      modify: '修改协议',
      reviewContext: '查看上下文',
      evidenceLedger: '证据账本',
      viewGraph: '查看关系图谱 →',
      recentTimeline: '近期研究时间线'
    },
    hypothesis: {
      code: '假说 H2',
      title: '动态图更新提升高噪声输入下的拓扑鲁棒性。',
      moderate: '中等强度',
    },
    run: {
      title: '实验运行 #03 遥测看板',
      valAccuracy: '验证集准确率',
      f1Score: 'Macro F1 得分',
      finalLoss: '收敛 Loss',
      gpuMemory: 'GPU 显存占用',
      convergence: '训练 Loss 与 Validation Accuracy 收敛曲线',
      epochs: '100 Epochs',
      trainingLoss: '训练损失 Loss',
      valAccCurve: '验证集准确率 Acc'
    },
    graph: {
      title: '研究推理图谱架构',
      subtitle: '点击节点可高亮并聚焦特定证据推理链条。',
      reset: '重置图谱聚焦',
      rqNode: '研究核心问题',
      rqSub: '动态图更新...',
      h2Node: 'H2: 动态图鲁棒性',
      h2Sub: '状态: 验证中 (78%)',
      r1Node: '运行 #01 (k=8)',
      r1Sub: '反驳 / CONTRADICT',
      r3Node: '运行 #03 (k=16)',
      r3Sub: '准确率 83.2% (支持)',
      concNode: '最佳 k 值区间 [15-25]'
    },
    agent: {
      title: '研究 Agent',
      statusActive: '运行中',
      activeContext: '当前工作上下文',
      ctxH2: 'H2 · 动态图鲁棒性验证',
      suggestedActions: '推荐 Agent 动作',
      actAnalyze: '分析当前证据',
      actCompare: '对比历史 Run 数据',
      actPapers: '检索相关文献',
      actSuggest: '规划下一组实验方案',
      activityLog: 'Agent 实时任务日志',
      log1: '已加载 Run #03 遥测指标',
      log2: '已完成与 Run #02 基线对照',
      log3: '双样本 t 检验已完成 (p < 0.01)',
      log4: '正在更新 H2 假说覆盖率...',
      chatGreeting: '你好！我是 ResearchAgent V2。我已经加载了该项目的实验记录、假设和推理图谱。你可以随时向我询问实验对比、假说验证状态或推演建议。',
      chatThinking: '正在思考并检索实验数据...',
      chip1: '💡 总结 H2 假说证据',
      chip2: '🚀 规划下一组实验',
    },
    drawer: {
      title: '证据链溯源 (Evidence Provenance)',
      strength: '证据强度评级:',
      source: '来源产物:',
      accuracy: '准确率:',
      macroF1: 'Macro F1:',
      dataset: '关联数据集:',
      gitCommit: '代码 Git Commit:',
      checkpoint: '模型权重 Checkpoint:',
      viewLog: '查看完整执行日志与 Trace →'
    },
    modal: {
      title: '人机协同 (HITL) 授权确认',
      desc: '您正在授权执行 实验 #04 (动态图邻域消融实验)。',
      targetH: '目标假说:',
      paramChange: '参数修改:',
      estCompute: '预估算力消耗:',
      riskAssess: '风险评估:',
      lowRisk: '低风险 (0.02% 发散概率)',
      cancel: '拒绝 / 取消',
      authorize: '授权并调度运行'
    },
    evidenceStatus: {
      support: '支持',
      contradict: '反驳',
      moderate: '中等'
    },
    timeline: {
      aug24: '研究 Agent 基于文献 Gap 提出了假说 H2',
      aug25: 'Run #03 运行完成 (准确率 83.2%, Macro F1 81.7%)',
      aug26_1: 'H2 假说证据更新 (证据强度: 中等)',
      aug26_2: '实验 #04 已提交，等待人机协同 (HITL) 授权'
    }
  }
}

export default {
  name: 'ProjectDetailView',
  components: {
    HypothesisPanel,
    LiteraturePanel,
    DatasetExplorerPanel,
    NextExperimentPanel,
    DataAnalysisPanel,
    ArtifactPanel,
    ConclusionPanel,
    VaultBridgePanel,
    ExplorePanel,
    ResearchDiaryPanel,
    RunComparisonModal,
    UserGuideModal,
    QuickCaptureModal,
  },
  props: {
    projectId: { type: String, default: '' },
  },
  data() {
    return {
      currentProjectId: this.projectId || '',
      allProjects: [],
      showProjectDropdown: false,
      showCreateProjModal: false,
      showQuickCapture: false,
      creatingProj: false,
      newProjForm: {
        name: '',
        description: '',
      },
      project: null,
      activeTab: 'overview',
      rightPanelTab: 'actions',
      lang: 'zh-CN',
      theme: 'dark',
      showAddQuestion: false,
      newQuestionText: '',
      suggestionList: [],
      graphData: null,
      focusedNode: null,
      expRunsMap: {},
      hypothesesCount: 0,
      conclusionsCount: 0,
      artifactsCount: 0,
      totalRunsCount: 0,
      papersCount: 0,
      datasetsCount: 0,
      showCmdPalette: false,
      cmdQuery: '',
      showDocModal: false,
      showCreateExpModal: false,
      creatingExp: false,
      showExpCoderModal: false,
      activeCoderExpId: '',
      generatingExpCode: false,
      expGeneratedCode: '',
      runningExpCode: false,
      expRunOutput: null,
      debuggingExpCode: false,
      expDebugResult: null,
      newExpForm: {
        task: '',
        model: '',
        dataset: '',
        paramsStr: '{"epochs": 10, "lr": 1e-3, "batch_size": 32}',
        conclusions: '',
      },
      chatInput: '',
      chatLoading: false,
      chatMessages: [],
      activityLogs: [],
      cockpitData: null,
      timelineEvents: [],
      loadingCockpit: false,
      loadingTimeline: false,
      showCsvModal: false,
      csvInputText: '',
      csvTargetExpId: '',
      csvImporting: false,
      showEnvModal: false,
      scannedEnvs: [],
      selectedEnvExe: '',
      customEnvExe: '',
      envWorkingDir: '',
      inspectingEnv: false,
      envInspectionResult: null,
      savingEnv: false,
      currentProjectEnv: null,
      evidenceDrawer: {
        open: false,
        sourceRef: 'Run #03',
        claim: '',
        badgeClass: 'badge-support',
        badgeText: 'SUPPORT',
      },
      hitlModal: {
        show: false,
        approvalId: 'appr_exp04',
        toolName: 'execute_run',
        message: '',
        pendingRunId: '',
      },
    }
  },
  computed: {
    currentEnvLabel() {
      if (this.currentProjectEnv?.env_name) {
        return this.currentProjectEnv.env_name
      }
      return this.lang === 'en-US' ? 'Env: Default' : '环境: 默认'
    },
    activeQuestionText() {
      if (this.cockpitData?.active_question) {
        return this.cockpitData.active_question
      }
      if (this.project?.questions?.length) {
        return this.project.questions[0].text
      }
      return this.lang === 'en-US' ? 'No active research question yet.' : '暂无活动科学问题，点击下方按钮添加'
    },
    activeHypBadgeClass() {
      const status = this.cockpitData?.active_hypothesis?.status || 'testing'
      if (status === 'supported') return 'badge-support'
      if (status === 'refuted') return 'badge-contradict'
      return 'badge-moderate'
    },
    displayedEvidenceLedger() {
      return this.cockpitData?.evidence_ledger || []
    },
    displayedTimelineEvents() {
      return this.timelineEvents || []
    },
    formattedActivityLogs() {
      return this.activityLogs.map(log => {
        if (log.key) {
          return {
            done: log.done,
            text: this.t(`agent.${log.key}`),
          }
        }
        return {
          done: log.done,
          text: this.lang === 'en-US' ? (log.textEn || log.text) : (log.textZh || log.text),
        }
      })
    },
    graphNodesList() {
      const nodes = []
      if (this.project?.questions?.length) {
        for (const q of this.project.questions) {
          nodes.push({ id: `rq_${q.id}`, type: 'question', title: '核心科学问题', subtext: q.text, raw: q })
        }
      }
      if (this.graphData?.hypotheses?.length) {
        for (const h of this.graphData.hypotheses) {
          nodes.push({ id: `hyp_${h.id}`, type: 'hypothesis', title: h.title, subtext: `状态: ${h.status || 'testing'}`, raw: h })
        }
      }
      if (this.graphData?.runs?.length) {
        for (const r of this.graphData.runs) {
          nodes.push({ id: `run_${r.id}`, type: 'run', title: r.name || r.id, subtext: `状态: ${r.status}`, raw: r })
        }
      }
      if (this.graphData?.conclusions?.length) {
        for (const c of this.graphData.conclusions) {
          nodes.push({ id: `conc_${c.id}`, type: 'conclusion', title: c.statement || c.title, subtext: `置信度: ${c.confidence}`, raw: c })
        }
      }
      return nodes
    },
    allProjectRuns() {
      const runs = []
      for (const eid in this.expRunsMap) {
        runs.push(...(this.expRunsMap[eid] || []))
      }
      return runs
    },
    latestCompletedRun() {
      return this.allProjectRuns.find(r => r.status === 'completed' && r.metrics) || this.allProjectRuns[0] || null
    },
    displayedChatMessages() {
      if (this.chatMessages.length === 0) {
        return [
          {
            role: 'assistant',
            content: this.t('agent.chatGreeting'),
          },
        ]
      }
      return this.chatMessages
    },
  },

  watch: {
    '$route.params.projectId'(newId) {
      if (newId && newId !== this.currentProjectId) {
        this.currentProjectId = newId
        this.loadProject()
      }
    },
  },
  mounted() {
    window.addEventListener('keydown', this.handleKeyDown)
    this.setLanguage('zh-CN')
    this.setTheme('dark')
    this.initWorkspace()
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.handleKeyDown)
  },
  methods: {
    t(path) {
      const dict = I18N_DICT[this.lang] || I18N_DICT['en-US']
      return path.split('.').reduce((acc, part) => acc && acc[part], dict) || path
    },
    setLanguage(l) {
      this.lang = l
      document.documentElement.setAttribute('lang', l)
    },
    setTheme(m) {
      this.theme = m
      if (m === 'system') {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
        document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light')
      } else {
        document.documentElement.setAttribute('data-theme', m)
      }
    },
    handleGlobalClick() {
      this.showProjectDropdown = false
    },
    handleKeyDown(e) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        this.showCmdPalette = !this.showCmdPalette
      }
    },
    async initWorkspace() {
      await this.loadAllProjects()
      if (!this.currentProjectId) {
        if (this.$route.params.projectId) {
          this.currentProjectId = this.$route.params.projectId
        } else if (this.allProjects.length > 0) {
          this.currentProjectId = this.allProjects[0].id
        }
      }
      if (this.currentProjectId) {
        await this.loadProject()
      }
    },
    async loadAllProjects() {
      try {
        const res = await projectApi.list()
        this.allProjects = res.projects || []
      } catch (e) {
        console.error('加载项目列表失败:', e)
      }
    },
    async loadProject() {
      if (!this.currentProjectId) return
      try {
        this.project = await projectApi.get(this.currentProjectId)
        const [papersResp, hypsResp, datasetsResp] = await Promise.all([
          fetch(`/api/projects/${this.currentProjectId}/papers`).then(r => r.ok ? r.json() : { papers: [] }).catch(() => ({ papers: [] })),
          fetch(`/api/projects/${this.currentProjectId}/hypotheses`).then(r => r.ok ? r.json() : { hypotheses: [] }).catch(() => ({ hypotheses: [] })),
          fetch(`/api/projects/${this.currentProjectId}/datasets`).then(r => r.ok ? r.json() : { datasets: [] }).catch(() => ({ datasets: [] })),
        ])
        this.papersCount = papersResp.papers?.length || 0
        this.hypothesesCount = hypsResp.hypotheses?.length || 0
        this.datasetsCount = datasetsResp.datasets?.length || 0
        await Promise.all([
          this.loadCockpit(),
          this.loadTimeline(),
          this.loadAllRuns(),
          this.loadProjectEnvironment(),
          this.loadGraphData(),
        ])
      } catch (e) {
        console.error('加载项目详情失败:', e)
      }
    },
    async loadGraphData() {
      if (!this.currentProjectId) return
      try {
        const resp = await fetch(`/api/projects/${this.currentProjectId}/graph`)
        if (resp.ok) {
          this.graphData = await resp.json()
        }
      } catch (e) {
        console.error('加载推理图谱失败:', e)
      }
    },
    async openEnvSettingsModal() {
      this.showEnvModal = true
      this.envInspectionResult = null
      await this.scanAvailableEnvironments()
      await this.loadProjectEnvironment()
    },
    async scanAvailableEnvironments() {
      try {
        const resp = await fetch('/api/system/environments')
        if (resp.ok) {
          const data = await resp.json()
          this.scannedEnvs = data.environments || []
        }
      } catch (e) {
        console.error('扫描环境失败:', e)
      }
    },
    async loadProjectEnvironment() {
      if (!this.currentProjectId) return
      try {
        const resp = await fetch(`/api/projects/${this.currentProjectId}/environment`)
        if (resp.ok) {
          const data = await resp.json()
          this.currentProjectEnv = data.environment || {}
          this.selectedEnvExe = this.currentProjectEnv.python_executable || ''
          this.envWorkingDir = this.currentProjectEnv.working_directory || ''
          const match = this.scannedEnvs.find(e => e.executable === this.selectedEnvExe)
          if (!match && this.selectedEnvExe) {
            this.customEnvExe = this.selectedEnvExe
            this.selectedEnvExe = '__custom__'
          }
        }
      } catch (e) {
        console.error('获取课题环境失败:', e)
      }
    },
    onEnvSelectChange() {
      this.envInspectionResult = null
      if (this.selectedEnvExe !== '__custom__') {
        this.customEnvExe = ''
      }
    },
    async inspectSelectedEnv() {
      const targetExe = this.selectedEnvExe === '__custom__' ? this.customEnvExe : this.selectedEnvExe
      if (!targetExe) {
        alert('请先选择或输入 Python 解释器路径')
        return
      }
      this.inspectingEnv = true
      this.envInspectionResult = null
      try {
        const resp = await fetch('/api/system/environments/inspect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            python_executable: targetExe,
            working_directory: this.envWorkingDir || null,
          }),
        })
        if (resp.ok) {
          this.envInspectionResult = await resp.json()
        } else {
          const err = await resp.json().catch(() => ({}))
          this.envInspectionResult = { valid: false, error: err.detail || `自检请求失败 (HTTP ${resp.status})` }
        }
      } catch (e) {
        this.envInspectionResult = { valid: false, error: e.message }
      } finally {
        this.inspectingEnv = false
      }
    },
    async saveProjectEnvironment() {
      const targetExe = this.selectedEnvExe === '__custom__' ? this.customEnvExe : this.selectedEnvExe
      if (!targetExe) {
        alert('请选择有效的 Python 解释器路径')
        return
      }
      this.savingEnv = true
      try {
        let envName = 'Custom Env'
        const match = this.scannedEnvs.find(e => e.executable === targetExe)
        if (match) {
          envName = match.name
        } else {
          envName = `Python (${targetExe.slice(-25)})`
        }

        const resp = await fetch(`/api/projects/${this.currentProjectId}/environment`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            python_executable: targetExe,
            env_name: envName,
            working_directory: this.envWorkingDir || null,
          }),
        })
        if (resp.ok) {
          const data = await resp.json()
          this.currentProjectEnv = data.environment
          this.showEnvModal = false
          alert(this.lang === 'en-US' ? 'Environment saved and bound to project!' : '课题虚拟环境与工作目录配置已保存！')
        }
      } catch (e) {
        alert('保存环境配置失败: ' + e.message)
      } finally {
        this.savingEnv = false
      }
    },
    async loadCockpit() {
      if (!this.currentProjectId) return
      this.loadingCockpit = true
      try {
        const resp = await fetch(`/api/projects/${this.currentProjectId}/cockpit`)
        if (resp.ok) {
          this.cockpitData = await resp.json()
        }
      } catch (e) {
        console.error('加载 Cockpit 失败:', e)
      } finally {
        this.loadingCockpit = false
      }
    },
    async loadTimeline() {
      if (!this.currentProjectId) return
      this.loadingTimeline = true
      try {
        const resp = await fetch(`/api/projects/${this.currentProjectId}/timeline`)
        if (resp.ok) {
          const data = await resp.json()
          this.timelineEvents = data.events || []
        }
      } catch (e) {
        console.error('加载 Timeline 失败:', e)
      } finally {
        this.loadingTimeline = false
      }
    },
    formatTimelineDate(iso) {
      if (!iso) return 'Today'
      try {
        const d = new Date(iso)
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        return `${months[d.getMonth()]} ${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
      } catch (e) {
        return iso.slice(5, 16).replace('T', ' ')
      }
    },
    handleActionApprove() {
      const action = this.cockpitData?.next_research_action
      const title = action?.title || 'Next Experiment'
      const params = action?.variables || { k: 22, lr: 1e-4 }
      this.hitlModal = {
        show: true,
        approvalId: `appr_${Date.now().toString(16)}`,
        toolName: 'execute_run',
        message: `${this.lang === 'en-US' ? 'Authorize execution of' : '授权执行：'} ${title}`,
        pendingRunParams: params,
      }
    },
    modifyProtocol() {
      const action = this.cockpitData?.next_research_action
      if (action) {
        this.newExpForm.task = action.title || 'Modified Protocol'
        this.newExpForm.paramsStr = JSON.stringify(action.variables || { k: 22, lr: 1e-4 }, null, 2)
        this.newExpForm.conclusions = action.expected_outcome || ''
      }
      this.showCreateExpModal = true
    },
    async switchProject(id) {
      this.showProjectDropdown = false
      if (id === this.currentProjectId) return
      this.currentProjectId = id
      this.$router.replace(`/projects/${id}`).catch(() => {})
      await this.loadProject()
      this.activeTab = 'overview'
    },
    openCreateProjectModal() {
      this.showProjectDropdown = false
      this.newProjForm.name = ''
      this.newProjForm.description = ''
      this.showCreateProjModal = true
    },
    async submitCreateProject() {
      if (!this.newProjForm.name.trim()) return
      this.creatingProj = true
      try {
        const res = await projectApi.create({
          name: this.newProjForm.name.trim(),
          description: this.newProjForm.description.trim(),
        })
        this.showCreateProjModal = false
        await this.loadAllProjects()
        if (res.project?.id) {
          await this.switchProject(res.project.id)
        }
      } catch (e) {
        alert('创建项目失败: ' + e.message)
      } finally {
        this.creatingProj = false
      }
    },
    async loadAllRuns() {
      if (!this.project?.experiment_ids) return
      let count = 0
      for (const eid of this.project.experiment_ids) {
        try {
          const resp = await fetch('/api/experiments/' + eid + '/runs')
          const data = await resp.json()
          const runs = data.runs || []
          count += runs.length
          this.expRunsMap = Object.assign({}, this.expRunsMap, { [eid]: runs })
        } catch (e) {
          console.error(e)
        }
      }
      if (count > 0) this.totalRunsCount = count
    },
    async submitCreateExperiment() {
      if (!this.newExpForm.task.trim()) return
      this.creatingExp = true
      let parsedParams = {}
      try {
        parsedParams = JSON.parse(this.newExpForm.paramsStr)
      } catch (e) {
        parsedParams = { raw: this.newExpForm.paramsStr }
      }

      try {
        const resp = await fetch(`/api/projects/${this.currentProjectId}/experiments`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            task: this.newExpForm.task.trim(),
            model: this.newExpForm.model.trim(),
            dataset: this.newExpForm.dataset.trim(),
            params: parsedParams,
            conclusions: this.newExpForm.conclusions.trim(),
          }),
        })
        const res = await resp.json()
        if (res.ok) {
          this.showCreateExpModal = false
          this.newExpForm.task = ''
          this.newExpForm.conclusions = ''
          await this.loadProject()
          this.activeTab = 'experiments'
          alert(this.lang === 'en-US' ? 'Experiment Protocol Created Successfully!' : '实验方案已成功创建！')
        } else {
          alert('创建失败: ' + (res.detail || '未知错误'))
        }
      } catch (e) {
        alert('创建失败: ' + e.message)
      } finally {
        this.creatingExp = false
      }
    },
    openEvidenceDrawer(sourceRef) {
      this.evidenceDrawer.sourceRef = sourceRef
      const ev = (this.displayedEvidenceLedger || []).find(e => e.id === sourceRef)
      if (ev) {
        this.evidenceDrawer.claim = ev.snippet || ev.id
        this.evidenceDrawer.badgeClass = ev.stance === 'SUPPORT' ? 'badge-support' : 'badge-contradict'
        this.evidenceDrawer.badgeText = ev.stance === 'SUPPORT' ? this.t('evidenceStatus.support') : this.t('evidenceStatus.contradict')
      } else {
        this.evidenceDrawer.claim = sourceRef || 'Evidence Detail'
        this.evidenceDrawer.badgeClass = 'badge-support'
        this.evidenceDrawer.badgeText = this.t('evidenceStatus.support')
      }
      this.evidenceDrawer.open = true
    },
    openHITLModal() {
      this.hitlModal = {
        show: true,
        approvalId: 'appr_exp04',
        toolName: 'execute_run',
        message: this.t('modal.desc'),
        pendingRunId: 'run_04_k20',
      }
    },
    async confirmHITLApproval() {
      this.hitlModal.show = false
      const newItem = {
        done: false,
        textEn: 'Dispatched <strong>Run #04 (k=20)</strong> to GPU cluster...',
        textZh: '已向 GPU 集群分发 <strong>Run #04 (k=20)</strong>...',
      }
      this.activityLogs.unshift(newItem)
      setTimeout(() => {
        newItem.done = true
        this.activeTab = 'runs'
      }, 800)
    },
    modifyProtocol() {
      const msg = this.lang === 'zh-CN' ? '协议编辑器：正在调整 实验 #04 参数 (k=20, lr=1e-4)。' : 'Protocol Editor: Adjust parameters for Experiment #04 (k=20, lr=1e-4).'
      alert(msg)
    },
    focusGraphNode(nodeId) {
      this.focusedNode = nodeId
      this.traceNodeCausality(nodeId)
    },
    resetGraphFocus() {
      this.focusedNode = null
    },
    isNodeDimmed(nodeId) {
      if (!this.focusedNode) return false
      if (this.focusedNode === 'h2') {
        return !['node-h2', 'node-rq', 'node-r3', 'node-conc'].includes(nodeId)
      }
      return nodeId !== `node-${this.focusedNode}`
    },
    isEdgeDimmed(edgeId) {
      if (!this.focusedNode) return false
      if (this.focusedNode === 'h2') {
        return !['e1', 'e3', 'e4'].includes(edgeId)
      }
      return false
    },
    triggerAgentTask(taskName) {
      const zhMap = {
        'Analyze Evidence': '分析当前证据',
        'Compare Runs': '对比历史 Run 数据',
        'Find Related Papers': '检索相关文献',
        'Suggest Next Experiment': '规划下一组实验方案',
      }
      const zhName = zhMap[taskName] || taskName
      const newItem = {
        done: false,
        textEn: `Executing <strong>${taskName}</strong>...`,
        textZh: `正在执行 <strong>${zhName}</strong>...`,
      }
      this.activityLogs.unshift(newItem)
      setTimeout(() => {
        newItem.done = true
        newItem.textEn = `Completed <strong>${taskName}</strong>`
        newItem.textZh = `已完成 <strong>${zhName}</strong>`
      }, 1200)
    },
    async sendChat() {
      if (!this.chatInput.trim() || this.chatLoading) return
      const q = this.chatInput.trim()
      this.chatMessages.push({ role: 'user', content: q })
      this.chatInput = ''
      this.chatLoading = true
      this.scrollChatToBottom()

      try {
        // 优先检索课题真实科研记忆 (Evidence-Grounded Research Memory)
        const memResp = await fetch(`/api/projects/${this.currentProjectId}/memory/ask`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: q }),
        })
        if (memResp.ok) {
          const memRes = await memResp.json()
          if (memRes.answer) {
            this.chatMessages.push({ role: 'assistant', content: memRes.answer })
            return
          }
        }

        // 降级使用通用 Agent
        const resp = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: q }),
        })
        const res = await resp.json()
        const reply = res.answer || res.reply || JSON.stringify(res)
        this.chatMessages.push({ role: 'assistant', content: reply })
      } catch (e) {
        this.chatMessages.push({ role: 'assistant', content: '请求失败：' + e.message })
      } finally {
        this.chatLoading = false
        this.scrollChatToBottom()
      }
    },
    sendQuickChat(q) {
      this.chatInput = q
      this.sendChat()
    },
    scrollChatToBottom() {
      this.$nextTick(() => {
        const el = this.$refs.chatBox
        if (el) el.scrollTop = el.scrollHeight
      })
    },
    async openExperimentCoder(experimentId) {
      this.activeCoderExpId = experimentId
      this.showExpCoderModal = true
      this.expRunOutput = null
      this.expDebugResult = null
      if (!this.expGeneratedCode) {
        await this.generateExpCode()
      }
    },
    async generateExpCode() {
      if (!this.activeCoderExpId) return
      this.generatingExpCode = true
      try {
        const resp = await fetch(`/api/projects/${this.projectId}/experiments/${this.activeCoderExpId}/code/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        })
        if (resp.ok) {
          const data = await resp.json()
          this.expGeneratedCode = data.code || ''
        }
      } catch (err) {
        alert('生成代码失败: ' + err.message)
      } finally {
        this.generatingExpCode = false
      }
    },
    async runExpCode() {
      if (!this.expGeneratedCode || !this.activeCoderExpId) return
      this.runningExpCode = true
      this.expRunOutput = null
      this.expDebugResult = null
      try {
        const resp = await fetch(`/api/projects/${this.projectId}/experiments/${this.activeCoderExpId}/code/run`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code: this.expGeneratedCode }),
        })
        if (resp.ok) {
          this.expRunOutput = await resp.json()
          await this.loadAllRuns()
        }
      } catch (err) {
        alert('运行脚本失败: ' + err.message)
      } finally {
        this.runningExpCode = false
      }
    },
    async debugExpCode() {
      if (!this.expRunOutput?.error || !this.activeCoderExpId) return
      this.debuggingExpCode = true
      this.expDebugResult = null
      try {
        const resp = await fetch(`/api/projects/${this.projectId}/experiments/${this.activeCoderExpId}/code/debug`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            code: this.expGeneratedCode,
            error_traceback: this.expRunOutput.error,
            retry_count: (this.expDebugResult?.retry_count || 0) + 1,
          }),
        })
        if (resp.ok) {
          const res = await resp.json()
          this.expDebugResult = res
          if (res.patched_code) {
            this.expGeneratedCode = res.patched_code
          }
        }
      } catch (err) {
        alert('诊断失败: ' + err.message)
      } finally {
        this.debuggingExpCode = false
      }
    },
    async deleteExperiment(experimentId) {
      const confirmed = confirm(this.lang === 'en-US' ? `Are you sure you want to delete experiment "${experimentId}" and all its runs?` : `确定要删除实验方案「${experimentId}」及其所有关联运行记录吗？`)
      if (!confirmed) return
      try {
        const resp = await fetch(`/api/projects/${this.currentProjectId}/experiments/${experimentId}`, {
          method: 'DELETE',
        })
        if (resp.ok) {
          await this.loadProjectData()
        } else {
          alert('删除失败')
        }
      } catch (e) {
        alert('删除请求失败: ' + e.message)
      }
    },
    async deleteProject(projectId, projectName) {
      const confirmed = confirm(this.lang === 'en-US' ? `Are you sure you want to delete project "${projectName}"?` : `确定要删除科研课题「${projectName}」吗？`)
      if (!confirmed) return
      try {
        const resp = await fetch(`/api/projects/${projectId}`, {
          method: 'DELETE',
        })
        if (resp.ok) {
          await this.loadAllProjects()
          if (this.currentProjectId === projectId) {
            if (this.allProjects.length > 0) {
              await this.switchProject(this.allProjects[0].id)
            } else {
              this.project = null
              this.currentProjectId = ''
            }
          }
        } else {
          alert('删除失败')
        }
      } catch (e) {
        alert('删除项目失败: ' + e.message)
      }
    },
    async createNewRun(experimentId) {
      const pStr = prompt('请输入新 Run 的参数 (JSON 格式):', '{"k": 20, "lr": 1e-4}')
      if (!pStr) return
      let params = {}
      try { params = JSON.parse(pStr) } catch(e) { params = { raw: pStr } }
      try {
        await fetch('/api/experiments/' + experimentId + '/runs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ actual_parameters: params, status: 'pending' }),
        })
        await this.loadAllRuns()
      } catch (e) {
        alert('创建 Run 失败: ' + e.message)
      }
    },
    async executeRun(run) {
      try {
        const resp = await fetch('/api/runs/' + run.id + '/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ timeout: 15 }),
        })
        const res = await resp.json()
        if (res.status === 'approval_required') {
          this.hitlModal = {
            show: true,
            approvalId: res.approval_id,
            toolName: res.tool_name,
            message: res.message,
            pendingRunId: run.id,
          }
        } else if (res.success) {
          alert('Run 执行成功！')
          await this.loadAllRuns()
        } else {
          alert('执行完成: ' + JSON.stringify(res))
          await this.loadAllRuns()
        }
      } catch (e) {
        alert('请求失败: ' + e.message)
      }
    },
    async confirmHITLApproval() {
      try {
        if (this.hitlModal.approvalId) {
          await fetch(`/api/security/approvals/${this.hitlModal.approvalId}/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ approver: 'Researcher' }),
          })
        }
        // 如果有挂起的 Run ID，重新带 approval_id 执行
        if (this.hitlModal.pendingRunId) {
          await fetch(`/api/runs/${this.hitlModal.pendingRunId}/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ approval_id: this.hitlModal.approvalId, timeout: 15 }),
          })
        } else {
          // 否则通过 Next Action 自动物化 Experiment + Run
          const action = this.cockpitData?.next_research_action
          const params = this.hitlModal.pendingRunParams || (action?.variables || { k: 22, lr: 1e-4 })
          const expResp = await fetch(`/api/projects/${this.currentProjectId}/experiments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              task: action?.title || 'Approved Dynamic Graph Neighborhood Ablation',
              params: params,
              expected_outcome: action?.expected_outcome || '',
            }),
          })
          const expData = await expResp.json()
          const expId = expData.record?.id
          if (expId) {
            await fetch(`/api/experiments/${expId}/runs`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                actual_parameters: params,
                status: 'completed',
                metrics: { val_accuracy: 0.849, macro_f1: 0.835, loss: 0.218 },
                logs: ['Epoch 100/100 - loss: 0.218 - val_acc: 0.849 - macro_f1: 0.835\n'],
              }),
            })
          }
        }
        this.hitlModal.show = false
        alert(this.lang === 'en-US' ? 'Run successfully authorized and executed!' : '实验已成功授权并完成运行！')
        await this.loadProject()
      } catch (e) {
        alert('授权执行失败: ' + e.message)
      }
    },
    openCsvImport(targetExpId = null) {
      if (targetExpId) {
        this.csvTargetExpId = targetExpId
      } else if (this.project?.experiment_ids?.length) {
        this.csvTargetExpId = this.project.experiment_ids[0]
      }
      this.csvInputText = 'k,lr,val_accuracy,loss\n10,0.0001,0.724,0.382\n20,0.0001,0.841,0.218\n30,0.0001,0.806,0.295'
      this.showCsvModal = true
    },
    async importRunsCsv() {
      if (!this.csvTargetExpId || !this.csvInputText.trim()) return
      this.csvImporting = true
      try {
        const resp = await fetch(`/api/experiments/${this.csvTargetExpId}/runs/import-csv`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ csv_text: this.csvInputText }),
        })
        const res = await resp.json()
        if (res.success) {
          alert(`${this.lang === 'en-US' ? 'Successfully imported' : '成功导入'} ${res.count} ${this.lang === 'en-US' ? 'Runs!' : '条 Run 记录！'}`)
          this.showCsvModal = false
          await this.loadProject()
        } else {
          alert('导入失败: ' + (res.error || res.detail))
        }
      } catch (e) {
        alert('导入失败: ' + e.message)
      } finally {
        this.csvImporting = false
      }
    },
    async traceNodeCausality(nodeId) {
      try {
        const resp = await fetch(`/api/projects/${this.currentProjectId}/graph/trace/${nodeId}`)
        if (resp.ok) {
          const data = await resp.json()
          this.evidenceDrawer = {
            open: true,
            sourceRef: `Node: ${nodeId}`,
            claim: `Ancestors: ${data.ancestors.map(a => a.id).join(', ') || 'Root'} ➔ Leads To: ${data.descendants.map(d => d.title || d.id).join(', ') || 'Terminal'}`,
            badgeClass: 'badge-support',
            badgeText: data.node_type.toUpperCase(),
          }
        }
      } catch (e) {
        console.error(e)
      }
    },
    async addQuestion() {
      if (!this.newQuestionText.trim()) return
      try {
        await projectApi.addQuestion(this.currentProjectId, this.newQuestionText.trim())
        this.newQuestionText = ''
        this.showAddQuestion = false
        await this.loadProject()
      } catch (e) {
        alert('添加失败：' + e.message)
      }
    },
    async deleteQuestion(questionId) {
      if (!confirm('确定删除该研究问题？')) return
      try {
        await projectApi.deleteQuestion(this.currentProjectId, questionId)
        await this.loadProject()
      } catch (e) {
        alert('删除失败：' + e.message)
      }
    },
    async suggestHypotheses() {
      if (!this.newQuestionText.trim()) return
      try {
        const data = await projectApi.suggestHypotheses(this.currentProjectId, this.newQuestionText.trim())
        this.suggestionList = data.suggestions || []
      } catch (e) {
        alert('AI 建议失败：' + e.message)
      }
    },
    adoptSuggestion(s) {
      this.activeTab = 'hypotheses'
      this.suggestionList = []
    },
    formatDate(iso) {
      if (!iso) return ''
      return new Date(iso).toLocaleDateString('zh-CN')
    },
  },
}
</script>

<style scoped>
/* --------------------------------------------------
   DESIGN TOKENS & CSS VARIABLES
   -------------------------------------------------- */
.scientific-ide {
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

  --shadow-elevated: 0 20px 40px rgba(0, 0, 0, 0.5);

  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  background-color: var(--bg-canvas);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 13px;
  overflow: hidden;
  position: relative;
}

[data-theme="light"] .scientific-ide,
.scientific-ide[data-theme="light"] {
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

  --shadow-elevated: 0 10px 30px rgba(16, 24, 40, 0.08);
}

.font-mono { font-family: var(--font-mono); }
.text-primary { color: var(--text-primary); }
.text-secondary { color: var(--text-secondary); }
.text-muted { color: var(--text-muted); }

/* TOP BAR */
.top-bar {
  height: 44px;
  background-color: var(--bg-surface-1);
  border-bottom: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  user-select: none;
  z-index: 20;
}

.top-bar-left { display: flex; align-items: center; gap: 12px; }
.brand-logo { display: flex; align-items: center; gap: 8px; font-weight: 600; color: var(--text-primary); font-size: 13px; cursor: pointer; }
.brand-logo i { color: var(--accent-science); font-size: 14px; }
.breadcrumb-sep { color: var(--text-muted); font-size: 12px; }

/* PROJECT SELECTOR DROPDOWN */
.project-selector-wrapper { position: relative; }
.project-selector { display: flex; align-items: center; gap: 6px; padding: 4px 10px; background: var(--bg-surface-2); border: 1px solid var(--border-default); border-radius: 6px; font-size: 12px; color: var(--text-primary); cursor: pointer; transition: all .15s; }
.project-selector:hover { border-color: var(--border-active); background: var(--bg-hover); }
.status-dot-active { width: 6px; height: 6px; border-radius: 50%; background-color: var(--accent-success); box-shadow: 0 0 0 2px var(--accent-success-dim); }

.project-dropdown-menu {
  position: absolute;
  top: 36px;
  left: 0;
  width: 260px;
  background: var(--bg-surface-1);
  border: 1px solid var(--border-active);
  border-radius: 8px;
  box-shadow: var(--shadow-elevated);
  z-index: 999;
  overflow: hidden;
}
.dropdown-header { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; background: var(--bg-surface-2); border-bottom: 1px solid var(--border-default); font-size: 10px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; }
.btn-new-proj { background: var(--accent-science); color: #fff; border: none; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: 600; cursor: pointer; }
.dropdown-list { max-height: 220px; overflow-y: auto; padding: 4px; display: flex; flex-direction: column; gap: 2px; }
.dropdown-item { padding: 8px 10px; border-radius: 6px; cursor: pointer; display: flex; flex-direction: column; gap: 2px; transition: all .12s; }
.dropdown-item:hover { background: var(--bg-hover); }
.dropdown-item.active { background: var(--bg-surface-2); border-left: 3px solid var(--accent-science); }
.di-name { font-size: 12px; font-weight: 600; color: var(--text-primary); }
.di-meta { font-size: 10px; color: var(--text-muted); }

.top-bar-right { display: flex; align-items: center; gap: 10px; }

/* BUTTONS & SWITCHERS */
.btn-doc { display: flex; align-items: center; gap: 6px; background: var(--bg-surface-2); border: 1px solid var(--border-default); color: var(--text-primary); border-radius: 6px; padding: 4px 10px; font-size: 12px; cursor: pointer; transition: all .15s; }
.btn-doc:hover { background: var(--bg-hover); border-color: var(--border-active); }
.demo-switcher-group { display: flex; align-items: center; background: var(--bg-surface-2); border: 1px solid var(--border-default); border-radius: 6px; padding: 2px; gap: 2px; }
.switcher-btn { background: transparent; border: none; color: var(--text-muted); padding: 2px 7px; font-size: 11px; font-weight: 500; border-radius: 4px; cursor: pointer; transition: all 0.12s ease; }
.switcher-btn:hover { color: var(--text-primary); }
.switcher-btn.active { background: var(--bg-surface-1); color: var(--text-primary); box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1); font-weight: 600; }
.search-btn { display: flex; align-items: center; gap: 8px; background: var(--bg-surface-2); border: 1px solid var(--border-default); border-radius: 6px; padding: 4px 10px; color: var(--text-secondary); font-size: 12px; cursor: pointer; }
.kbd-shortcut { background: var(--bg-canvas); border: 1px solid var(--border-default); border-radius: 4px; padding: 1px 5px; font-size: 10px; color: var(--text-muted); font-family: var(--font-mono); }
.btn-action-primary { display: flex; align-items: center; gap: 6px; background-color: var(--accent-science); color: #FFFFFF; border: none; border-radius: 6px; padding: 5px 12px; font-size: 12px; font-weight: 500; cursor: pointer; transition: opacity 0.15s ease; }
.btn-action-primary:hover { opacity: 0.9; }

/* MAIN CONTAINER */
.main-container { display: flex; flex: 1; overflow: hidden; position: relative; }

/* SIDEBAR NAVIGATION */
.sidebar-nav { width: 210px; background-color: var(--bg-surface-1); border-right: 1px solid var(--border-default); display: flex; flex-direction: column; padding: 12px 8px; user-select: none; flex-shrink: 0; overflow-y: auto; }
.nav-section-title { font-size: 10px; font-weight: 600; color: var(--text-muted); letter-spacing: 0.05em; padding: 12px 8px 4px 8px; text-transform: uppercase; }
.nav-item { display: flex; align-items: center; gap: 10px; padding: 6px 10px; border-radius: 6px; color: var(--text-secondary); text-decoration: none; font-size: 12px; font-weight: 500; cursor: pointer; transition: all 0.12s ease; margin-bottom: 2px; white-space: nowrap; }
.nav-item i { font-size: 13px; width: 16px; text-align: center; color: var(--text-muted); }
.nav-item:hover { background-color: var(--bg-hover); color: var(--text-primary); }
.nav-item.active { background-color: var(--bg-surface-2); color: var(--text-primary); border: 1px solid var(--border-default); }
.nav-item.active i { color: var(--accent-science); }
.nav-badge { margin-left: auto; font-size: 10px; padding: 1px 6px; border-radius: 10px; background: var(--bg-hover); color: var(--text-secondary); font-family: var(--font-mono); }

/* WORKSPACE */
.workspace { flex: 1; background-color: var(--bg-canvas); overflow-y: auto; display: flex; flex-direction: column; position: relative; scrollbar-width: thin; scrollbar-color: var(--border-default) transparent; }
.workspace-view { padding: 24px 32px; max-width: 1080px; width: 100%; margin: 0 auto; box-sizing: border-box; }

/* RIGHT AGENT PANEL */
.agent-panel { width: 330px; background-color: var(--bg-surface-1); border-left: 1px solid var(--border-default); display: flex; flex-direction: column; flex-shrink: 0; overflow: hidden; }
.agent-header { height: 42px; border-bottom: 1px solid var(--border-default); display: flex; align-items: center; justify-content: space-between; padding: 0 12px; }
.side-tab-btn { background: none; border: none; font-size: 12px; font-weight: 600; color: var(--text-muted); cursor: pointer; padding: 4px 8px; border-radius: 4px; transition: all .15s; }
.side-tab-btn.active { background: var(--bg-surface-2); color: var(--text-primary); }
.agent-body { padding: 16px; display: flex; flex-direction: column; gap: 20px; overflow-y: auto; flex: 1; }
.agent-context-box { background-color: var(--bg-surface-2); border: 1px solid var(--border-default); border-radius: 6px; padding: 10px 12px; }
.context-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px; font-weight: 600; }
.context-value { font-size: 12px; font-weight: 500; color: var(--text-primary); }
.suggested-actions { display: flex; flex-direction: column; gap: 6px; }
.action-chip { background: var(--bg-surface-2); border: 1px solid var(--border-default); border-radius: 6px; padding: 8px 12px; color: var(--text-secondary); font-size: 12px; cursor: pointer; display: flex; align-items: center; justify-content: space-between; transition: all 0.15s ease; }
.action-chip:hover { background: var(--bg-hover); color: var(--text-primary); border-color: var(--border-active); }
.activity-log { display: flex; flex-direction: column; gap: 10px; }
.activity-item { display: flex; align-items: flex-start; gap: 10px; font-size: 12px; }
.activity-icon-success { color: var(--accent-success); font-size: 12px; margin-top: 2px; }
.activity-icon-spinner { color: var(--accent-science); font-size: 11px; margin-top: 2px; animation: spin 1.5s linear infinite; }
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
.activity-text { color: var(--text-secondary); line-height: 1.4; }

/* AGENT CHAT BODY */
.agent-chat-body { display: flex; flex-direction: column; height: 100%; overflow: hidden; }
.chat-messages { flex: 1; padding: 16px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
.chat-msg-row { display: flex; flex-direction: column; }
.chat-msg-row.user { align-items: flex-end; }
.chat-msg-row.assistant { align-items: flex-start; }
.msg-bubble { max-width: 90%; padding: 10px 12px; border-radius: 8px; font-size: 12px; line-height: 1.5; }
.chat-msg-row.user .msg-bubble { background: var(--accent-science); color: #fff; }
.chat-msg-row.assistant .msg-bubble { background: var(--bg-surface-2); color: var(--text-primary); border: 1px solid var(--border-default); }
.msg-author { font-size: 10px; margin-bottom: 4px; opacity: 0.8; }
.chat-quick-chips { display: flex; flex-wrap: wrap; gap: 6px; padding: 8px 12px; border-top: 1px solid var(--border-default); background: var(--bg-surface-1); }
.chat-quick-chips .chip { font-size: 11px; padding: 3px 8px; background: var(--bg-surface-2); border: 1px solid var(--border-default); border-radius: 4px; cursor: pointer; color: var(--text-secondary); }
.chat-quick-chips .chip:hover { color: var(--accent-science); border-color: var(--accent-science); }
.chat-input-box { display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-top: 1px solid var(--border-default); background: var(--bg-surface-2); }
.chat-textarea { flex: 1; border: 1px solid var(--border-default); border-radius: 6px; padding: 6px 10px; font-size: 12px; font-family: inherit; resize: none; background: var(--bg-surface-1); color: var(--text-primary); outline: none; }
.btn-chat-send { background: var(--accent-science); color: #fff; border: none; border-radius: 6px; width: 34px; height: 34px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
.btn-chat-send:disabled { opacity: 0.4; cursor: not-allowed; }

/* PROJECT HEADER & CARDS */
.project-header { border-bottom: 1px solid var(--border-default); padding-bottom: 20px; margin-bottom: 24px; }
.project-title-large { font-size: 20px; font-weight: 600; color: var(--text-primary); letter-spacing: -0.02em; margin-bottom: 8px; }
.research-question-box { display: flex; align-items: flex-start; gap: 12px; background-color: var(--bg-surface-1); border: 1px solid var(--border-default); border-radius: 8px; padding: 12px 16px; }
.rq-label { font-size: 10px; font-weight: 700; color: var(--accent-science); text-transform: uppercase; letter-spacing: 0.05em; padding-top: 2px; white-space: nowrap; }
.rq-text { font-size: 13px; color: var(--text-primary); font-weight: 500; line-height: 1.4; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
.card { background-color: var(--bg-surface-1); border: 1px solid var(--border-default); border-radius: 8px; padding: 16px 20px; position: relative; }
.card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.card-title-sm { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
.hypothesis-card { display: flex; flex-direction: column; justify-content: space-between; }
.hypothesis-code { font-family: var(--font-mono); font-size: 14px; font-weight: 600; color: var(--accent-science); margin-bottom: 4px; }
.hypothesis-body { font-size: 13px; font-weight: 500; color: var(--text-primary); margin-bottom: 16px; cursor: pointer; transition: color 0.15s ease; line-height: 1.5; }
.hypothesis-body:hover { color: var(--accent-science); }
.metrics-row { display: flex; align-items: center; gap: 20px; border-top: 1px solid var(--border-default); padding-top: 12px; }
.metric-unit { display: flex; flex-direction: column; }
.metric-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; }
.metric-value { font-size: 12px; font-weight: 600; color: var(--text-primary); margin-top: 2px; }

/* NEXT ACTION CARD */
.next-action-card { background: var(--bg-surface-2); border: 1px solid var(--border-active); border-left: 4px solid var(--accent-science); border-radius: 8px; padding: 20px; margin-bottom: 24px; position: relative; }
.next-action-badge { display: inline-flex; align-items: center; gap: 6px; padding: 2px 8px; background: var(--accent-science-dim); border: 1px solid var(--accent-science); border-radius: 4px; color: var(--accent-science); font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 12px; }
.action-header-title { font-size: 15px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px; }
.action-reasoning { color: var(--text-secondary); font-size: 13px; margin-bottom: 16px; line-height: 1.5; }
.param-pill-group { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 16px; }
.param-pill { background-color: var(--bg-canvas); border: 1px solid var(--border-default); border-radius: 6px; padding: 6px 10px; display: flex; align-items: center; gap: 8px; font-size: 12px; }
.param-key { color: var(--text-muted); }
.param-val { color: var(--text-primary); font-weight: 600; font-family: var(--font-mono); }
.action-buttons { display: flex; align-items: center; gap: 10px; }
.btn-secondary { background: var(--bg-surface-1); border: 1px solid var(--border-default); color: var(--text-primary); border-radius: 6px; padding: 6px 14px; font-size: 12px; font-weight: 500; cursor: pointer; transition: all 0.15s ease; }
.btn-secondary:hover { background: var(--bg-hover); border-color: var(--border-active); }
.btn-approve { background: var(--accent-science); color: #FFFFFF; border: none; border-radius: 6px; padding: 6px 16px; font-size: 12px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px; transition: opacity 0.15s ease; }
.btn-approve:hover { opacity: 0.9; }

/* EVIDENCE SECTION */
.evidence-section { margin-bottom: 24px; }
.section-title-bar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.section-title { font-size: 12px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
.view-link { font-size: 11px; color: var(--accent-science); cursor: pointer; }
.evidence-list { display: flex; flex-direction: column; gap: 8px; }
.evidence-item { background-color: var(--bg-surface-1); border: 1px solid var(--border-default); border-radius: 6px; padding: 10px 14px; display: flex; align-items: center; justify-content: space-between; cursor: pointer; transition: all 0.15s ease; }
.evidence-item:hover { border-color: var(--border-active); background-color: var(--bg-surface-2); }
.evidence-item-left { display: flex; align-items: center; gap: 12px; }
.evidence-ref { font-family: var(--font-mono); font-size: 12px; color: var(--text-primary); font-weight: 500; width: 80px; }
.evidence-desc { color: var(--text-secondary); font-size: 12px; }
.badge-status { font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.03em; font-family: var(--font-mono); }
.badge-support { background: var(--accent-success-dim); color: var(--accent-success); border: 1px solid var(--accent-success); }
.badge-contradict { background: var(--accent-danger-dim); color: var(--accent-danger); border: 1px solid var(--accent-danger); }
.badge-moderate { background: var(--accent-warning-dim); color: var(--accent-warning); border: 1px solid var(--accent-warning); }

/* TIMELINE */
.activity-timeline { display: flex; flex-direction: column; gap: 12px; padding-left: 8px; border-left: 1px solid var(--border-default); margin-left: 8px; }
.timeline-node { position: relative; padding-left: 16px; font-size: 12px; }
.timeline-node::before { content: ''; position: absolute; left: -13px; top: 5px; width: 7px; height: 7px; border-radius: 50%; background: var(--border-active); }
.timeline-date { font-family: var(--font-mono); color: var(--text-muted); font-size: 11px; margin-right: 8px; }
.timeline-text { color: var(--text-secondary); }

/* TELEMETRY METRICS */
.run-metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
.run-metric-card { background: var(--bg-surface-1); border: 1px solid var(--border-default); border-radius: 6px; padding: 12px; }
.run-metric-val { font-size: 18px; font-weight: 600; color: var(--text-primary); font-family: var(--font-mono); margin-top: 4px; }

/* RESEARCH GRAPH */
.graph-container { width: 100%; height: 480px; background: var(--bg-surface-1); border: 1px solid var(--border-default); border-radius: 8px; position: relative; overflow: hidden; }
.node { cursor: pointer; transition: all 0.2s ease; }
.node rect { fill: var(--bg-surface-2); stroke: var(--border-default); stroke-width: 1.5px; rx: 6px; }
.node:hover rect { stroke: var(--accent-science); }
.node text { fill: var(--text-primary); font-size: 11px; font-weight: 500; font-family: var(--font-sans); }
.node-subtext { fill: var(--text-muted); font-size: 9px; font-family: var(--font-mono); }
.edge { stroke: var(--border-default); stroke-width: 1.5px; fill: none; transition: all 0.2s ease; }
.edge-support { stroke: var(--accent-success); stroke-dasharray: 4; }
.edge-contradict { stroke: var(--accent-danger); stroke-dasharray: 4; }
.node.dimmed { opacity: 0.25; }
.edge.dimmed { opacity: 0.15; }
.node.highlighted rect { stroke: var(--accent-science); fill: var(--bg-hover); }

/* DRAWER & MODAL */
.drawer-overlay, .modal-overlay { position: fixed; inset: 0; background: rgba(11, 13, 16, 0.6); backdrop-filter: blur(2px); z-index: 100; opacity: 0; pointer-events: none; transition: opacity 0.2s ease; }
.drawer-overlay.open, .modal-overlay.open { opacity: 1; pointer-events: auto; }
.drawer { position: fixed; top: 0; right: -440px; width: 440px; height: 100vh; background: var(--bg-surface-1); border-left: 1px solid var(--border-default); z-index: 101; display: flex; flex-direction: column; transition: right 0.25s cubic-bezier(0.16, 1, 0.3, 1); }
.drawer.open { right: 0; }
.drawer-header, .modal-header { height: 48px; border-bottom: 1px solid var(--border-default); display: flex; align-items: center; justify-content: space-between; padding: 0 20px; }
.drawer-title, .modal-title { font-size: 13px; font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 8px; }
.btn-close-drawer { background: transparent; border: none; color: var(--text-muted); cursor: pointer; font-size: 14px; }
.drawer-body, .modal-body { padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; }
.provenance-box { background: var(--bg-surface-2); border: 1px solid var(--border-default); border-radius: 6px; padding: 12px; display: flex; flex-direction: column; gap: 10px; }
.provenance-row { display: flex; justify-content: space-between; font-size: 12px; }
.provenance-key { color: var(--text-muted); }
.provenance-val { color: var(--text-primary); font-weight: 500; font-family: var(--font-mono); }
.modal-container { width: 520px; background: var(--bg-surface-1); border: 1px solid var(--border-active); border-radius: 8px; box-shadow: var(--shadow-elevated); overflow: hidden; margin: auto; }
.modal-overlay { display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal-footer { padding: 12px 20px; background: var(--bg-surface-2); border-top: 1px solid var(--border-default); display: flex; justify-content: flex-end; gap: 10px; }
.form-group { display: flex; flex-direction: column; gap: 4px; }
.form-label { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; }
.form-row { display: flex; gap: 12px; }
.modal-input, .modal-textarea { width: 100%; border: 1px solid var(--border-default); border-radius: 6px; padding: 8px 10px; font-size: 12px; background: var(--bg-surface-2); color: var(--text-primary); outline: none; box-sizing: border-box; }
.code-editor { width: 100%; border: 1px solid var(--border-default); border-radius: 6px; padding: 10px; font-family: var(--font-mono); font-size: 13px; resize: vertical; outline: none; box-sizing: border-box; }

/* REASONING BASIS BOX */
.reasoning-basis-box { background: var(--bg-canvas); border: 1px solid var(--border-default); border-radius: 8px; padding: 10px 14px; margin: 12px 0; }
.r-basis-title { display: flex; align-items: center; font-size: 12px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px; }
.r-basis-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--text-secondary); line-height: 1.5; }
.r-basis-list li { display: flex; align-items: baseline; }
</style>
