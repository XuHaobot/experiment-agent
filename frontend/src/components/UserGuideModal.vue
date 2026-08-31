<template>
  <div v-if="visible" class="guide-modal-backdrop" @click.self="$emit('close')">
    <div class="guide-modal-dialog">
      <!-- 弹窗顶栏 -->
      <div class="guide-modal-header">
        <div class="guide-header-title">
          <i class="fa-solid fa-book-open" style="color: #3b82f6; font-size: 18px;"></i>
          <div>
            <h3 class="title-text">{{ lang === 'en-US' ? 'ResearchOS Interactive User & API Guide' : 'ResearchOS 系统内置使用与 API 接入开发指南' }}</h3>
            <p class="subtitle-text">{{ lang === 'en-US' ? 'Local-First Scientific Research Workspace Manual & Live Reference' : '本地优先个人科研工作台操作手册与全量 API 接入示例' }}</p>
          </div>
        </div>
        <div class="guide-header-actions">
          <span class="version-tag">V2.6.0 Stable</span>
          <button class="btn-close" @click="$emit('close')">✕</button>
        </div>
      </div>

      <!-- 弹窗主体：左侧分类导航 + 右侧详细图文/代码 -->
      <div class="guide-modal-body">
        <!-- 左侧章节导航 -->
        <div class="guide-sidebar">
          <a
            v-for="item in navItems"
            :key="item.id"
            class="guide-nav-item"
            :class="{ active: currentSection === item.id }"
            @click="currentSection = item.id"
          >
            <i :class="item.icon"></i>
            <span>{{ lang === 'en-US' ? item.titleEn : item.titleZh }}</span>
          </a>
        </div>

        <!-- 右侧内容展示区 -->
        <div class="guide-content">
          <!-- 1. 30秒极速上手 -->
          <div v-if="currentSection === 'quickstart'" class="section-block">
            <h2 class="section-title">🚀 30 秒极速科研闭环上手</h2>
            <p class="section-desc">无需复杂配置，ResearchOS 遵循本地优先原则，所有数据沉淀在本地 <code>data/</code> 目录。</p>
            
            <div class="guide-steps">
              <div class="step-card">
                <div class="step-num">1</div>
                <div class="step-info">
                  <h4>确立核心问题与假说</h4>
                  <p>在左侧导航进入「Hypotheses」，点击「+ 新建科学问题」，记录机理疑问并提出 8 态科研假说。</p>
                </div>
              </div>
              <div class="step-card">
                <div class="step-num">2</div>
                <div class="step-info">
                  <h4>执行实验方案与多次 Runs</h4>
                  <p>在「Experiments」设计参数模板，或在「Runs」中一键导入外部自动化训练产生的 CSV 结果。</p>
                </div>
              </div>
              <div class="step-card">
                <div class="step-num">3</div>
                <div class="step-info">
                  <h4>横向对比与证据沉淀</h4>
                  <p>勾选多个 Run 唤起对比矩阵，提取最优参数拐点，将关键发现标记为假说的「支持」或「反驳」证据。</p>
                </div>
              </div>
              <div class="step-card">
                <div class="step-num">4</div>
                <div class="step-info">
                  <h4>主动探索与下一轮推演</h4>
                  <p>进入「🧭 科学探索」面板，查看 Type A/B/C/D 候选实验组合与假说判决矩阵，一键批准转化为新实验方案。</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 2. 核心科研闭环 -->
          <div v-if="currentSection === 'workflow'" class="section-block">
            <h2 class="section-title">🔬 核心科研闭环 (Question → Hypothesis → Run → Evidence → Conclusion)</h2>
            <p class="section-desc">严谨科研拒绝无据证明。所有结论均必须由客观运行数据或文献切片支撑。</p>
            
            <div class="info-callout">
              <b>假说认知状态机 (8 态生命周期):</b>
              <div class="status-grid">
                <span class="status-chip active">ACTIVE: 活跃验证中</span>
                <span class="status-chip supported">SUPPORTED: 获得充分实证</span>
                <span class="status-chip weakened">WEAKENED: 受到反面挑战</span>
                <span class="status-chip refuted">REFUTED: 被明确否定</span>
                <span class="status-chip testing">TESTING: 实验进行中</span>
                <span class="status-chip stale">STALE: 证据停滞</span>
              </div>
            </div>

            <h4>从数据到科学结论 (Evidence Ledger)</h4>
            <ul>
              <li><strong>支持证据 (Supporting)</strong>：证明假说成立的实验指标（如峰值准确率、收敛速度）。</li>
              <li><strong>反驳证据 (Contradicting)</strong>：展现模型性能暴跌、梯度异常或过平滑等负向结果。</li>
              <li><strong>证据天平</strong>：实时呈现 Positive / Negative / Unknown 比例，杜绝确认偏误 (Confirmation Bias)。</li>
            </ul>
          </div>

          <!-- 3. 主动探索引擎 -->
          <div v-if="currentSection === 'exploration'" class="section-block">
            <h2 class="section-title">🧭 主动科学探索引擎 (Active Exploration Engine)</h2>
            <p class="section-desc">基于认识论多目标组合，提供通俗可解释的实验推荐与假说区分度判决。</p>

            <div class="explore-types-grid">
              <div class="type-box">
                <span class="type-badge exploit">Type A · EXPLOIT (极值精调)</span>
                <p>围绕历史已知最优参数（如 k=20）进行细粒度微调，精准锁定极值拐点坐标。</p>
              </div>
              <div class="type-box">
                <span class="type-badge discriminate">Type B · DISCRIMINATE (假说判决)</span>
                <p>专门设计用于产生预测分歧的解耦实验，一次性排除相互矛盾的竞争性解释。</p>
              </div>
              <div class="type-box">
                <span class="type-badge explore">Type C · EXPLORE (盲区探测)</span>
                <p>跳跃探测未采样的参数未知盲区（如参数跨度 [21, 29]），防止陷入局部极值。</p>
              </div>
              <div class="type-box">
                <span class="type-badge replicate">Type D · REPLICATE (稳定性复现)</span>
                <p>变换随机种子复现关键性能跳变点，量化误差条，排除偶发随机性。</p>
              </div>
            </div>

            <h4 style="margin-top: 16px;">竞争假说区分度矩阵 (Discrimination Matrix)</h4>
            <p>在 Explore 面板中直观对比每个实验在「假说 A」与「假说 B」下的不同理论预测，让每组算力都消耗在最关键的学术分歧上。</p>
          </div>

          <!-- 4. 运行对比与数据分析 -->
          <div v-if="currentSection === 'analysis'" class="section-block">
            <h2 class="section-title">📊 多 Run 横向对比与 DuckDB 数据分析</h2>
            <p class="section-desc">多运行参数横向比对与受控 Python 沙箱分析。</p>
            
            <h4>1. 多运行对比 (Run Comparison)</h4>
            <p>在 Runs 界面中勾选 2 个或多个运行实例，点击「横向对比」，即可查看所有自变量参数与指标的并集矩阵，并自动标出 👑 最优表现。</p>

            <h4>2. DuckDB 结构化分析</h4>
            <p>导入数据集表格后，直接在受控沙箱中使用 SQL 或 Python 执行参数敏感度分析与折线图生成，产出自动绑定 SHA256 与前向因果血缘。</p>
          </div>

          <!-- 5. 科研日记与日常手记 -->
          <div v-if="currentSection === 'diary'" class="section-block">
            <h2 class="section-title">📔 Research Diary 科研日记与工作会话</h2>
            <p class="section-desc">给科研人员随手记录直觉、猜想与每日反思的专属空间。</p>
            <ul>
              <li><strong>USER_BELIEF 标记</strong>：日记内容被系统严格分类为用户主观观察，<strong>AI 绝无权限自动修改、覆盖或伪造日记</strong>。</li>
              <li><strong>Research Session 会话追踪</strong>：一轮连续工作结束时，轻量记录本次会话查看的文献、执行的 Runs 与沉淀的结论。</li>
            </ul>
          </div>

          <!-- 6. 本地 AI 与隐私门禁 -->
          <div v-if="currentSection === 'privacy'" class="section-block">
            <h2 class="section-title">🛡️ 本地 AI (Ollama) 与隐私安全门禁</h2>
            <p class="section-desc">100% 保护科研代码与未公开实验数据。</p>
            
            <h4>四级数据分类与三级隐私门禁</h4>
            <table class="guide-table">
              <thead><tr><th>分类级别</th><th>定义</th><th>默认处置行为</th></tr></thead>
              <tbody>
                <tr><td><code>PUBLIC</code></td><td>公开发表的论文摘要、开源数据集名称</td><td><span class="badge-allow">ALLOW</span> 直接放行</td></tr>
                <tr><td><code>INTERNAL</code></td><td>内部实验 ID、参数键名</td><td><span class="badge-allow">ALLOW</span> 本地模型放行</td></tr>
                <tr><td><code>SENSITIVE</code></td><td>用户本地未公开私有数据集绝对路径</td><td><span class="badge-ask">ASK</span> 弹出确认提示</td></tr>
                <tr><td><code>RESTRICTED</code></td><td>API Key、密码、系统敏感环境变量</td><td><span class="badge-deny">DENY</span> 强制硬拦截阻断</td></tr>
              </tbody>
            </table>
          </div>

          <!-- 7. Obsidian Vault 网桥 -->
          <div v-if="currentSection === 'obsidian'" class="section-block">
            <h2 class="section-title">📚 Obsidian 知识库双向投影 (Vault Bridge)</h2>
            <p class="section-desc">将结构化实验记录无缝投影到 Obsidian 个人第二大脑。</p>
            <ul>
              <li><strong>标准 Markdown 与 Wikilinks</strong>：自动生成 <code>01_Projects</code>, <code>02_Hypotheses</code>, <code>03_Experiments</code>, <code>05_Conclusions</code> 目录；</li>
              <li><strong>100% 笔记段落保护</strong>：采用 <code>&lt;!-- RESEARCHOS:START --&gt;</code> 标记隔离，您在 Obsidian 中撰写的个人手记在重新同步时永远完好保留。</li>
            </ul>
          </div>

          <!-- 8. API 接入手册与代码示例 -->
          <div v-if="currentSection === 'api'" class="section-block">
            <h2 class="section-title">⚡ 全量 REST API 接入与 Python 示例代码</h2>
            <p class="section-desc">后端提供完备的 RESTful API，可无缝与 Python 训练脚本、PyTorch、MLflow 或 Jupyter Notebook 联动。</p>

            <h4>常用 API 端点列表</h4>
            <pre class="code-block font-mono">
POST   /api/projects                             # 创建课题
POST   /api/projects/{id}/hypotheses             # 提出假说
POST   /api/runs                                 # 记录单次实验运行
POST   /api/runs/compare                         # 横向对比多组运行参数与指标
GET    /api/projects/{id}/exploration/candidates # 获取 Type A/B/C/D 候选实验组合
POST   /api/projects/{id}/exploration/approve    # 批准候选实验生成正式草稿
POST   /api/projects/{id}/diary                  # 记录每日科研手记
POST   /api/projects/{id}/memory/ask             # 结构化零幻觉认知记忆问答
            </pre>

            <h4>Python 快速调用示例 (保存 Run 并横向对比)</h4>
            <pre class="code-block font-mono">
import requests

BASE = "http://127.0.0.1:5001"

# 1. 记录训练结果
run_res = requests.post(f"{BASE}/api/runs", json={
    "experiment_id": "exp_k_sweep",
    "actual_parameters": {"k": 20, "lr": 1e-4},
    "metrics": {"val_accuracy": 0.912, "loss": 0.214},
    "status": "completed"
}).json()
print("Recorded Run ID:", run_res["id"])

# 2. 横向多 Run 对比
compare_res = requests.post(f"{BASE}/api/runs/compare", json={
    "run_ids": ["run_10", "run_20", "run_30"]
}).json()
print("Best Run:", compare_res["best_run_id"])
print("Insights:", compare_res["insights"])
            </pre>
          </div>

          <!-- 9. 常见问题排查 -->
          <div v-if="currentSection === 'faq'" class="section-block">
            <h2 class="section-title">❓ 常见问题排查 (FAQ)</h2>
            <div class="faq-item">
              <b>Q: 本地 Ollama 无法连接如何解决？</b>
              <p>确保终端已执行 <code>ollama serve</code> 并使用 <code>ollama pull qwen2.5-coder:7b</code> 下载了模型。在「AI 设置」中点击测试连接即可。</p>
            </div>
            <div class="faq-item">
              <b>Q: 为什么探索引擎会弹出“⚠️ 伪探索警告”？</b>
              <p>当系统检测到拟测试的参数落在已经密集采样过的饱和区间时，会提醒避免无效微调，将算力分配给 Type B（假说判决）或 Type C（盲区探索）。</p>
            </div>
            <div class="faq-item">
              <b>Q: 假说修剪建议会删除我的数据吗？</b>
              <p>绝对不会。ResearchOS 坚持学术严谨性，修剪建议仅作为研究精力分配参考，系统永远不提供自动物理删除功能。</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 弹窗底栏 -->
      <div class="guide-modal-footer">
        <div class="footer-note">
          <i class="fa-solid fa-circle-info"></i>
          <span>系统完整文档位于项目 <code>docs/USER_AND_API_GUIDE.md</code></span>
        </div>
        <button class="btn-primary-close" @click="$emit('close')">
          {{ lang === 'en-US' ? 'Got It, Close' : '已了解并关闭' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  lang: { type: String, default: 'zh-CN' },
})

defineEmits(['close'])

const currentSection = ref('quickstart')

const navItems = [
  { id: 'quickstart', icon: 'fa-solid fa-rocket', titleZh: '30秒极速上手', titleEn: 'Quick Start' },
  { id: 'workflow', icon: 'fa-solid fa-flask-vial', titleZh: '核心科研闭环', titleEn: 'Research Loop' },
  { id: 'exploration', icon: 'fa-solid fa-compass', titleZh: '主动探索引擎', titleEn: 'Active Explore' },
  { id: 'analysis', icon: 'fa-solid fa-chart-pie', titleZh: '运行对比与分析', titleEn: 'Run Compare & Data' },
  { id: 'diary', icon: 'fa-solid fa-book-journal-whills', titleZh: '科研日记与会话', titleEn: 'Diary & Sessions' },
  { id: 'privacy', icon: 'fa-solid fa-shield-halved', titleZh: '本地 AI 与隐私', titleEn: 'Local AI & Privacy' },
  { id: 'obsidian', icon: 'fa-solid fa-gem', titleZh: 'Obsidian 知识库', titleEn: 'Obsidian Vault' },
  { id: 'api', icon: 'fa-solid fa-code', titleZh: 'API 接入与代码', titleEn: 'REST API & Code' },
  { id: 'faq', icon: 'fa-solid fa-circle-question', titleZh: '常见问题排查', titleEn: 'FAQ & Help' },
]
</script>

<style scoped>
.guide-modal-backdrop {
  position: fixed; inset: 0; background: rgba(0,0,0,0.65); z-index: 2000;
  display: flex; align-items: center; justify-content: center; padding: 24px;
}
.guide-modal-dialog {
  background: var(--bg-surface-1, #fff); border-radius: 12px; width: 100%; max-width: 980px;
  height: 85vh; display: flex; flex-direction: column; box-shadow: 0 20px 50px rgba(0,0,0,0.3);
  overflow: hidden; border: 1px solid var(--border-default, #e2e8f0);
}
.guide-modal-header {
  padding: 16px 20px; border-bottom: 1px solid var(--border-default, #e2e8f0);
  display: flex; justify-content: space-between; align-items: center; background: var(--bg-surface-2, #f8fafc);
}
.guide-header-title { display: flex; align-items: center; gap: 12px; }
.title-text { font-size: 16px; margin: 0; font-weight: 700; color: var(--text-primary, #1e293b); }
.subtitle-text { font-size: 12px; color: var(--text-secondary, #64748b); margin: 2px 0 0 0; }
.guide-header-actions { display: flex; align-items: center; gap: 10px; }
.version-tag { font-size: 11px; font-weight: 700; background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 4px; }
.btn-close { background: none; border: none; font-size: 16px; cursor: pointer; color: var(--text-muted, #94a3b8); }
.btn-close:hover { color: #ef4444; }

.guide-modal-body { display: flex; flex: 1; overflow: hidden; }
.guide-sidebar {
  width: 200px; background: var(--bg-surface-2, #f8fafc); border-right: 1px solid var(--border-default, #e2e8f0);
  padding: 12px 8px; display: flex; flex-direction: column; gap: 4px; overflow-y: auto;
}
.guide-nav-item {
  display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 6px;
  font-size: 12px; font-weight: 600; color: var(--text-secondary, #475569); cursor: pointer; text-decoration: none;
  transition: all 0.15s;
}
.guide-nav-item i { width: 16px; text-align: center; }
.guide-nav-item:hover { background: rgba(59, 130, 246, 0.08); color: #3b82f6; }
.guide-nav-item.active { background: #3b82f6; color: #fff; }

.guide-content { flex: 1; padding: 24px 28px; overflow-y: auto; color: var(--text-primary, #1e293b); line-height: 1.6; }
.section-title { font-size: 18px; margin: 0 0 8px 0; font-weight: 700; color: var(--text-primary, #0f172a); }
.section-desc { font-size: 13px; color: var(--text-secondary, #64748b); margin: 0 0 20px 0; }

.guide-steps { display: flex; flex-direction: column; gap: 12px; margin-top: 16px; }
.step-card { display: flex; gap: 14px; background: var(--bg-surface-2, #f8fafc); border: 1px solid var(--border-default, #e2e8f0); border-radius: 8px; padding: 12px 16px; }
.step-num { width: 28px; height: 28px; border-radius: 50%; background: #3b82f6; color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px; flex-shrink: 0; }
.step-info h4 { margin: 0 0 4px 0; font-size: 13px; font-weight: 700; }
.step-info p { margin: 0; font-size: 12px; color: var(--text-secondary, #64748b); }

.info-callout { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 12px 16px; font-size: 12px; margin-bottom: 16px; }
.status-grid { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.status-chip { font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 600; }
.status-chip.active { background: #dbeafe; color: #1e40af; }
.status-chip.supported { background: #dcfce7; color: #166534; }
.status-chip.weakened { background: #ffedd5; color: #9a3412; }
.status-chip.refuted { background: #fee2e2; color: #991b1b; }
.status-chip.testing { background: #fef9c3; color: #854d0e; }
.status-chip.stale { background: #f1f5f9; color: #475569; }

.explore-types-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.type-box { background: var(--bg-surface-2, #f8fafc); border: 1px solid var(--border-default, #e2e8f0); border-radius: 8px; padding: 12px; }
.type-badge { font-size: 11px; font-weight: 700; padding: 2px 6px; border-radius: 4px; display: inline-block; margin-bottom: 6px; }
.type-badge.exploit { background: #dcfce7; color: #166534; }
.type-badge.discriminate { background: #e0e7ff; color: #3730a3; }
.type-badge.explore { background: #fef08a; color: #854d0e; }
.type-badge.replicate { background: #f1f5f9; color: #334155; }
.type-box p { margin: 0; font-size: 12px; color: var(--text-secondary, #64748b); }

.code-block { background: #0f172a; color: #e2e8f0; border-radius: 8px; padding: 14px; font-size: 12px; overflow-x: auto; line-height: 1.5; margin: 10px 0; }
.guide-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }
.guide-table th, .guide-table td { border: 1px solid var(--border-default, #e2e8f0); padding: 8px 12px; text-align: left; }
.guide-table th { background: var(--bg-surface-2, #f8fafc); font-weight: 600; }
.badge-allow { background: #dcfce7; color: #166534; font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 3px; }
.badge-ask { background: #fef08a; color: #854d0e; font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 3px; }
.badge-deny { background: #fee2e2; color: #991b1b; font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 3px; }

.faq-item { margin-bottom: 14px; }
.faq-item b { font-size: 13px; color: var(--text-primary, #0f172a); }
.faq-item p { margin: 4px 0 0 0; font-size: 12px; color: var(--text-secondary, #64748b); }

.guide-modal-footer {
  padding: 12px 20px; border-top: 1px solid var(--border-default, #e2e8f0);
  display: flex; justify-content: space-between; align-items: center; background: var(--bg-surface-2, #f8fafc);
}
.footer-note { font-size: 12px; color: var(--text-secondary, #64748b); display: flex; align-items: center; gap: 6px; }
.btn-primary-close { background: #3b82f6; color: #fff; border: none; border-radius: 6px; padding: 6px 18px; font-size: 12px; font-weight: 600; cursor: pointer; }
</style>
