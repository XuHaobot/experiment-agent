# ResearchOS V2.6.0 全功能使用指南与 API 接入开发手册

> **版本**：`V2.6.0 (Stable Release)`  
> **适用对象**：科研人员、算法工程师、二次开发集成者  
> **设计原则**：Local-First（本地优先）、严谨实证支撑、零虚构、100% 数据隐私保护

---

# 第一部分：快速启动与系统部署

## 1. 系统要求与环境依赖
* **操作系统**：Windows 10/11、macOS 或 Linux
* **Python**：Python 3.10+（推荐 Python 3.11 / 3.12）
* **Node.js**：Node.js 18+ 与 npm
* **本地 AI 推荐（可选）**：Ollama（用于离线运行 Qwen / Llama 等开源模型）

## 2. 一键启动

### Windows 环境
双击项目根目录下的：
```cmd
start.bat
```
脚本将自动启动：
1. **FastAPI 后端服务**：`http://127.0.0.1:5001`
2. **Vue3 前端应用**：`http://localhost:3000`
3. 并在 3 秒后自动在默认浏览器中打开工作台。

### 手动分步启动
```bash
# 1. 启动后端
cd /path/to/experiment-agent
python -m uvicorn backend.main:app --host 127.0.0.1 --port 5001 --reload

# 2. 启动前端 (另开终端)
cd frontend
npm install
npm run dev
```

---

# 第二部分：核心功能使用指南 (User Guide)

```text
                                  【ResearchOS 核心交互工作流】
                                               
     ① 确立问题与假说      ② 实验设计与多 Run 执行      ③ 数据分析与证据提炼      ④ 主动探索与假说更新
    ┌───────────────┐     ┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
    │ 科学问题      │ ──► │ 设计实验参数        │ ──► │ DuckDB 敏感度分析│ ──► │ Type A/B/C/D 候选组合│
    │ 8态科研假说   │     │ 运行单次/多次 Run   │     │ 提炼正反证据     │     │ 区分竞争假说        │
    │ 正反证据天平  │     │ CSV 批量导入        │     │ 沉淀科学结论     │     │ 一键批准并进入下一轮 │
    └───────────────┘     └─────────────────────┘     └──────────────────┘     └─────────────────────┘
            │                                                                             │
            ▼                                                                             ▼
    【Research Diary 每日手记】 ◄────────────────────────────────────────────── 【Obsidian 长期知识沉淀】
```

---

## 1. 核心科学问题与假说管理 (Questions & Hypotheses)
* **确立科学问题**：进入课题后，点击「+ 新建科学问题」，记录要解决的本质机理（如“图神经网络邻域大小 $k$ 如何影响流形平滑性与泛化度？”）；
* **提出假说与生命周期**：
  * 在问题下提出假说（如 $H_1$: “增大 $k$ 可提升抗噪鲁棒性”）；
  * 假说拥有 8 级认知状态：`ACTIVE`（积极验证中）、`SUPPORTED`（获实证支撑）、`WEAKENED`（被削弱）、`REFUTED`（被否定）、`TESTING`（测试中）、`STALE`（停滞）等；
* **绑定证据**：可直接在假说详情中挂载支撑（Supporting）或反驳（Contradicting）证据。

---

## 2. 学术文献与本地 PDF 精准切片 (Literature & PDF Slicing)
* **多源学术检索**：支持 OpenAlex、arXiv、Semantic Scholar 跨库学术文献检索；
* **一键保存至课题**：将检索到的论文沉淀为课题文献资产；
* **本地 PDF 章节切片**：上传本地 PDF，系统自动提取特定页码与章节段落（`Page X · Sec Y`），直接转化为假说的实证切片。

---

## 3. 实验方案与多 Run 遥测追踪 (Experiments & Runs)
* **方案与运行严格分立**：
  * `Experiment`：代表一个实验方案（如“参数 $k$ 的网格扫描”）；
  * `ExperimentRun`：代表单次真实的参数执行实例（记录具体的参数取值、`val_accuracy`、`loss`、`runtime` 与标准输出日志）；
* **CSV 批量导入**：支持将外部自动化脚本生成的参数/指标 CSV 文件一键导入为多个 Run。

---

## 4. 多 Run 横向对比矩阵 (Run Comparison)
* 在实验运行列表中勾选多个 Run（如 `Run #01`, `Run #02`, `Run #03`），点击「横向对比」；
* 系统自动对齐所有自变量参数与因变量指标，高亮标出最优表现（👑 BEST），直观展现拐点坐标。

---

## 5. 数据分析与受控沙箱 (Dataset & Sandboxed Python)
* **DuckDB 内置查询**：导入数据表格后，直接使用 SQL 执行聚合与过滤；
* **RestrictedPython 受控沙箱**：自动生成分析代码并安全运行，生成图表（Chart）与分析报告（Report），自动附加 SHA256 与前向血缘追溯。

---

## 6. 正反证据天平与结论沉淀 (Evidence Ledger & Conclusions)
* **Evidence Balance 天平**：实时统计 Supporting（支持）、Contradicting（反面矛盾）与 Unknown（未探索）分布；
* **沉淀科学结论**：结论必须明确引用具体 Run 或文献切片，严禁凭空下结论；系统自动根据证据充分度判定置信度（`HIGH` / `MEDIUM` / `LOW`）。

---

## 7. 主动科学探索引擎 (Active Exploration Engine)
进入「🧭 科学探索」面板，系统自动生成多范式候选实验组合：
* **Type A (EXPLOIT · 极值精调)**：围绕历史最佳配置微调以锁定极值坐标；
* **Type B (DISCRIMINATE · 假说判决)**：专门设计用于区分相互矛盾的竞争性假说；
* **Type C (EXPLORE · 盲区探测)**：跳跃至未采样的参数空间未知区域；
* **Type D (REPLICATE · 稳定性复现)**：变换随机种子复现关键拐点，量化误差条；
* **假说区分度矩阵 (Discrimination Matrix)**：直观对比各候选实验在不同假说下的预测差异；
* **伪探索警示**：自动检测密集饱和区间内的微小变体调参；
* **一键批准**：点击「✓ 批准并生成正式实验」，直接转化为 Experiment 草稿。

---

## 8. 科研日记与会话管理 (Research Diary & Sessions)
* **Research Diary**：记录每日直觉、猜想与未证实的观察（严格标记为 `USER_BELIEF`，AI 绝不篡改）；
* **Research Session**：轻量记录一轮连续工作的跨模块足迹（查看了哪些文献、执行了哪些 Run、沉淀了哪些结论）。

---

## 9. 认知记忆问答 (Research Memory 2.0)
* 在科研问答中提问（如“为什么 k=30 准确率下降？”）；
* 系统自动返回结构化事实，严格区分 `OBSERVATION` / `EVIDENCE` / `INTERPRETATION` / `AI_SUGGESTION`，**绝不暴露内部思考过程 (CoT)**。

---

## 10. Obsidian 知识库双向投影 (Vault Bridge)
* 一键将课题导出为 Obsidian 格式（`01_Projects`, `02_Hypotheses`, `03_Experiments`, `05_Conclusions` 等）；
* 导出文件包含稳定 `[[Wikilinks]]` 与 YAML Frontmatter；
* **100% 保护用户笔记**：采用 `<!-- RESEARCHOS:START -->` 隔离技术，用户在 Obsidian 中撰写的个人手记在重新同步时完好无损。

---

## 11. 本地 AI 与隐私门禁 (Local AI & Privacy Gateway)
* **Local Ollama**：在设置中选择本地模型（如 `qwen2.5-coder`），所有推理 100% 在本机完成；
* **三级门禁**：自动识别 `PUBLIC`（放行）、`SENSITIVE`（确认后放行）、`RESTRICTED`（硬拦截），所有决策透明记录至审计日志。

---

# 第三部分：全量 REST API 接入开发手册 (API Reference)

* **Base URL**: `http://127.0.0.1:5001`
* **Content-Type**: `application/json`

---

## 1. 课题与科学问题 (Projects & Questions)

### 1.1 创建研究课题
* **Endpoint**: `POST /api/projects`
* **Request**:
```json
{
  "name": "动态图拓扑鲁棒性研究",
  "description": "探索自适应图卷积网络在噪声下的流形平滑性"
}
```
* **Response**:
```json
{
  "id": "proj_9f81a7b3c2",
  "name": "动态图拓扑鲁棒性研究",
  "description": "探索自适应图卷积网络在噪声下的流形平滑性",
  "questions": [],
  "experiment_ids": [],
  "created_at": "2026-08-31T17:00:00Z"
}
```
* **Python 接入示例**:
```python
import requests

res = requests.post("http://127.0.0.1:5001/api/projects", json={
    "name": "动态图拓扑鲁棒性研究",
    "description": "探索自适应图卷积网络在噪声下的流形平滑性"
})
project = res.json()
print("Created Project ID:", project["id"])
```

### 1.2 添加核心科学问题
* **Endpoint**: `POST /api/projects/{project_id}/questions`
* **Request**:
```json
{
  "text": "邻域参数 k 如何在局部连通度与过平滑之间产生平衡？"
}
```
* **Response**:
```json
{
  "id": "q_1a2b3c4d5e",
  "text": "邻域参数 k 如何在局部连通度与过平滑之间产生平衡？",
  "created_at": "2026-08-31T17:01:00Z"
}
```

---

## 2. 科学假说与证据 (Hypotheses & Evidence)

### 2.1 创建科研假说
* **Endpoint**: `POST /api/projects/{project_id}/hypotheses`
* **Request**:
```json
{
  "title": "高阶邻域过平滑假说",
  "description": "当 k > 20 后，特征聚集导致节点表示趋同",
  "question_id": "q_1a2b3c4d5e"
}
```
* **Response**:
```json
{
  "id": "hyp_7a8b9c0d1e",
  "project_id": "proj_9f81a7b3c2",
  "question_id": "q_1a2b3c4d5e",
  "title": "高阶邻域过平滑假说",
  "description": "当 k > 20 后，特征聚集导致节点表示趋同",
  "status": "pending",
  "evidence": []
}
```

### 2.2 挂载证据至假说
* **Endpoint**: `POST /api/hypotheses/{hypothesis_id}/evidence`
* **Request**:
```json
{
  "source": "run_01a2b3c4d5",
  "text": "Run k=30 准确率由 91.0% 下滑至 78.5%",
  "supports": false
}
```
* **Response**:
```json
{
  "id": "ev_5f6e7d8c",
  "source": "run_01a2b3c4d5",
  "text": "Run k=30 准确率由 91.0% 下滑至 78.5%",
  "supports": false,
  "created_at": "2026-08-31T17:02:00Z"
}
```

---

## 3. 实验、运行与横向对比 (Experiments, Runs & Comparison)

### 3.1 创建实验单次运行 (Run)
* **Endpoint**: `POST /api/runs`
* **Request**:
```json
{
  "experiment_id": "exp_grid_sweep",
  "actual_parameters": { "k": 20, "lr": 0.0001, "batch_size": 32 },
  "metrics": { "val_accuracy": 0.912, "loss": 0.214 },
  "status": "completed",
  "logs": ["Epoch 100 finished. val_acc=0.912"]
}
```
* **Response**:
```json
{
  "id": "run_99401a2b3c",
  "experiment_id": "exp_grid_sweep",
  "actual_parameters": { "k": 20, "lr": 0.0001, "batch_size": 32 },
  "metrics": { "val_accuracy": 0.912, "loss": 0.214 },
  "status": "completed",
  "created_at": "2026-08-31T17:03:00Z"
}
```

### 3.2 从 CSV 批量导入 Runs
* **Endpoint**: `POST /api/experiments/{experiment_id}/runs/import-csv`
* **Request**:
```json
{
  "csv_content": "k,lr,val_accuracy,loss\n10,0.0001,0.84,0.32\n20,0.0001,0.91,0.21\n30,0.0001,0.78,0.45\n"
}
```
* **Response**:
```json
{
  "success": true,
  "count": 3,
  "created_runs": [ ... ]
}
```

### 3.3 多 Run 横向对比矩阵
* **Endpoint**: `POST /api/runs/compare`
* **Request**:
```json
{
  "run_ids": ["run_10", "run_20", "run_30"]
}
```
* **Response**:
```json
{
  "runs_count": 3,
  "param_keys": ["batch_size", "k", "lr"],
  "metric_keys": ["loss", "val_accuracy"],
  "best_run_id": "run_20",
  "comparison_matrix": [
    {
      "run_id": "run_20",
      "status": "completed",
      "parameters": { "k": 20, "lr": 0.0001, "batch_size": 32 },
      "metrics": { "val_accuracy": 0.91, "loss": 0.21 },
      "artifacts_count": 1
    }
  ],
  "insights": "已对比 3 个运行实例。最优表现为 run_20 (最高指标: 91.0%)。涉及自变量参数: batch_size, k, lr。"
}
```
* **cURL 示例**:
```bash
curl -X POST http://127.0.0.1:5001/api/runs/compare \
     -H "Content-Type: application/json" \
     -d '{"run_ids": ["run_10", "run_20", "run_30"]}'
```

---

## 4. 科学结论与证据天平 (Conclusions & Evidence Balance)

### 4.1 获取认知证据天平
* **Endpoint**: `GET /api/projects/{project_id}/memory/balance`
* **Response**:
```json
{
  "project_id": "proj_9f81a7b3c2",
  "supporting": [
    { "id": "run_20", "snippet": "Run k=20 达成高准确率 (acc=91.2%)", "epistemic_status": "OBSERVATION" }
  ],
  "contradicting": [
    { "id": "run_30", "snippet": "Run k=30 准确率显著回落 (acc=78.5%)", "epistemic_status": "OBSERVATION" }
  ],
  "unknown": [
    "参数 'k' 在区间 [21, 29] 内存在中段未测试空隙"
  ],
  "confidence": "medium",
  "total_evidence_count": 2
}
```

### 4.2 创建科学结论
* **Endpoint**: `POST /api/projects/{project_id}/conclusions`
* **Request**:
```json
{
  "text": "邻域参数在 k=20 处取得性能峰值，超出后因过平滑效应性能显著下降。",
  "hypothesis_id": "hyp_7a8b9c0d1e",
  "confidence": "high",
  "evidence_refs": [
    { "type": "run", "id": "run_20", "snippet": "Peak 91.2% at k=20" },
    { "type": "run", "id": "run_30", "snippet": "Drop 78.5% at k=30" }
  ]
}
```

---

## 5. 主动科学探索引擎 (Active Exploration API)

### 5.1 获取多范式候选实验组合
* **Endpoint**: `GET /api/projects/{project_id}/exploration/candidates?max_candidates=4`
* **Response**:
```json
{
  "project_id": "proj_9f81a7b3c2",
  "total_candidates": 4,
  "recommended_balance": {
    "explore_weight": 0.65,
    "exploit_weight": 0.35,
    "strategy": "HIGH_UNCERTAINTY_EXPLORATION"
  },
  "candidates": [
    {
      "candidate_id": "cand_99a8b7c6",
      "candidate_type": "DISCRIMINATE",
      "title": "[Type B · Discriminate] Decoupled Test: k=30 with Scaled LR=2.0e-05",
      "variables": { "k": 30, "lr": 0.00002 },
      "expected_information_gain": "HIGH",
      "epistemic_value": "HIGH",
      "uncertainty_reduction": "判别大 k 下性能下降是由过平滑还是学习率失配导致",
      "is_pseudo_exploration": false,
      "why_this_experiment": "具有最高的假说鉴别力，能一次性排除竞争解释。"
    }
  ]
}
```

### 5.2 获取假说区分度矩阵
* **Endpoint**: `GET /api/projects/{project_id}/exploration/discrimination`
* **Response**:
```json
{
  "project_id": "proj_9f81a7b3c2",
  "hypotheses_evaluated": [
    "hyp_01: 高阶邻域过平滑假说",
    "AI_ALT: 学习率与拓扑规模的协同交互效应"
  ],
  "matrix": [
    {
      "candidate_id": "cand_99a8b7c6",
      "candidate_title": "Decoupled Test k=30 with Scaled LR",
      "candidate_type": "DISCRIMINATE",
      "predictions": {
        "hyp_01: 高阶邻域过平滑假说": "预测准确率随 LR 降低仍无改善 (结构瓶颈)",
        "AI_ALT: 学习率与拓扑规模的协同交互效应": "预测准确率随 LR 减小大幅回升 (参数失配)"
      },
      "discrimination_power": "HIGH",
      "epistemic_value": "HIGH"
    }
  ]
}
```

### 5.3 批准候选实验并生成草稿
* **Endpoint**: `POST /api/projects/{project_id}/exploration/approve`
* **Request**:
```json
{
  "candidate_id": "cand_99a8b7c6"
}
```
* **Response**:
```json
{
  "success": true,
  "experiment_id": "exp_88776655",
  "project_id": "proj_9f81a7b3c2",
  "candidate_id": "cand_99a8b7c6",
  "candidate_type": "DISCRIMINATE",
  "status": "draft"
}
```

---

## 6. 科研日记与工作会话 (Diary & Sessions API)

### 6.1 保存科研日记
* **Endpoint**: `POST /api/projects/{project_id}/diary`
* **Request**:
```json
{
  "title": "关于流形过平滑的直觉观察",
  "content": "今天注意到当 k 从 20 增加到 25 时，高频梯度消失极快，说明拉普拉斯算子在高阶处发生了局部退化。",
  "tags": ["intuition", "laplacian", "gradient"]
}
```
* **Response**:
```json
{
  "success": true,
  "entry": {
    "id": "diary_11223344",
    "title": "关于流形过平滑的直觉观察",
    "epistemic_status": "USER_BELIEF",
    "created_at": "2026-08-31T17:05:00Z"
  }
}
```

### 6.2 记录科研工作会话
* **Endpoint**: `POST /api/projects/{project_id}/sessions`
* **Request**:
```json
{
  "title": "Session #01 · 拓扑邻域调参工作轮次",
  "goal": "定位最佳邻域大小并沉淀结论",
  "actions_summary": ["导入 3 组运行遥测", "执行 DuckDB 参数敏感度分析", "沉淀结论 C-01"],
  "executed_runs": ["run_10", "run_20", "run_30"],
  "reached_conclusions": ["conc_01"],
  "next_step": "执行 Type B 假说区分实验"
}
```

---

## 7. 认知记忆与无 CoT 结构化问答 (Research Memory)

* **Endpoint**: `POST /api/projects/{project_id}/memory/ask`
* **Request**:
```json
{
  "question": "为什么我们不继续测试 k=30？"
}
```
* **Response**:
```json
{
  "grounding_level": "SUPPORTED",
  "summary": "根据历史实验记录，使用 k=30 的运行实例准确率为 78.5%，而最优运行 (k=20) 达到了 91.2%。数据显示当 k > 20 后局部特征过度平滑，模型性能呈现单调回落趋势。",
  "evidence": [
    "Run: run_30 -> k=30, Accuracy=78.5%",
    "Run: run_20 -> k=20, Accuracy=91.2%"
  ],
  "reasoning_basis": [
    "k=30 已经过完整实测验证，准确率明显低于 k=20，无需重复进行同参数测试。",
    "当前信息增益最大的方向是在最优区间内进行解耦测试或探索未知盲区。"
  ],
  "alternative_hypotheses": [
    {
      "hypothesis": "高阶邻域过平滑 (Over-smoothing Mechanism)",
      "epistemic_status": "AI_SUGGESTION"
    }
  ],
  "unexplored_space": [
    "参数 'k' 在区间 [21, 29] 内存在中段未测试空隙"
  ],
  "answer": "### 📋 科研事实与解答 `[SUPPORTED]`\n..."
}
```

---

## 8. Obsidian Vault 知识库导出 (Vault Bridge)

* **Endpoint**: `POST /api/projects/{project_id}/vault/export`
* **Request**:
```json
{
  "vault_path": "C:/Users/Researcher/Documents/ObsidianVault"
}
```
* **Response**:
```json
{
  "success": true,
  "vault_path": "C:/Users/Researcher/Documents/ObsidianVault",
  "files_written": 14,
  "manifest_version": 1
}
```

---

# 第四部分：底层数据存储规范 (Data Persistence)

所有数据均以标准 JSON / Markdown 格式保存在项目 `data/` 目录中，完全透明、可复制、易备份：

```text
data/
├── projects/           # 课题元数据 (<project_id>.json)
├── hypotheses/         # 科研假说与关联证据 (<hypothesis_id>.json)
├── records/            # 实验方案草稿 (<record_id>.json)
├── runs/               # 实验运行遥测记录 (<run_id>.json)
├── datasets/           # DuckDB 数据库与元数据 (<dataset_id>.duckdb)
├── artifacts/          # 图表、报告、模型资产 (<artifact_id>)
├── conclusions/        # 沉淀科研结论 (<conclusion_id>.json)
├── diary/              # 科研日记手记 (<project_id>.json)
├── sessions/           # 工作会话足迹 (<project_id>.json)
└── audit/              # 隐私门禁审计日志 (privacy_audit.jsonl)
```

---

# 第五部分：常见问题排查与 FAQ

### Q1: 本地 Ollama 无法连接？
* **检查项**：
  1. 确保在本地终端已启动 `ollama serve`；
  2. 确保在终端执行 `ollama list` 能看到至少一个模型（如 `ollama pull qwen2.5-coder:7b`）；
  3. 前端进入「AI 设置」点击「测试连接」，状态显示 Connected 即就绪。

### Q2: 为什么有些推荐实验被标记为“⚠️ 伪探索警告”？
* **解释**：当系统检测到拟探索的参数（如 $k=20.2$）落在已经密集测试过（已有 $k=19, 20, 21$）的饱和区间时，会自动提示此实验信息增益低，建议将算力分配给 Type B（假说判决）或 Type C（盲区探测）。

### Q3: 为什么假说修剪建议不会自动删除假说？
* **解释**：ResearchOS 坚持“**严谨学术可追溯**”原则。即使假说受到多次反面实验挑战，系统也只会推荐将其状态变更为 `WEAKENED` 或降低探索预算，绝不擅自删除任何历史假说。
