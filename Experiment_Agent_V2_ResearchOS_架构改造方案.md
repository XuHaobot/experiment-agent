# Experiment Agent V2：从实验助手到 AI 原生科研实验操作系统

> 项目仓库：<https://github.com/XuHaobot/experiment-agent>
>
> 目标：在现有 Experiment Agent 基础上迭代，而不是推倒重做；优先复用成熟开源项目，把项目从“实验记录/复盘助手”逐步升级为“AI 原生科研实验操作系统（Research OS）”。

---

## 1. 项目重新定位

### 当前定位

当前项目已经具备：

- FastAPI + Vue3 基础架构
- Function Calling Agent
- 混合检索
- 对话记忆
- SSE 流式响应
- 实验记录管理
- 实验知识图谱
- 多文件分析
- 数据分析
- 报告生成
- 实验复盘与下一步建议

当前更接近：

> **Experiment Memory / Experiment Copilot**

即：帮助科研人员记录、搜索、理解和复盘已经发生的实验。

### V2 目标定位

将项目升级为：

> **ResearchOS —— AI 原生科研实验操作系统**

核心不是“让 AI 回答科研问题”，而是让 AI 参与科研闭环：

```text
Research Question
        ↓
Hypothesis
        ↓
Experiment Design
        ↓
Experiment Execution
        ↓
Data
        ↓
Analysis
        ↓
Evidence
        ↓
Conclusion
        ↓
Next Experiment
        ↺
```

最终目标：

> 从“AI 帮科研人员管理实验”，升级到“AI 与科研人员共同推进实验”。

---

# 2. 最重要的产品判断

不要把项目继续做成：

```text
AI Chat
+ PDF
+ RAG
+ Experiment CRUD
+ Graph
```

这种模式容易变成“功能很多的科研聊天工具”。

真正应该形成的是：

```text
Research Project
      ↓
Research Question
      ↓
Hypothesis
      ↓
Experiment
      ↓
Observation
      ↓
Analysis
      ↓
Conclusion
      ↓
Next Experiment
```

其中：

> **Research Loop 是整个产品的核心。**

---

# 3. V2 核心产品结构

建议将产品拆成 6 个核心域：

```text
ResearchOS
│
├── Research Project
│
├── Research Knowledge
│   ├── Papers
│   ├── Experiments
│   ├── Datasets
│   └── Research Graph
│
├── Research Agent
│   ├── Literature Agent
│   ├── Hypothesis Agent
│   ├── Experiment Designer
│   ├── Data Analyst
│   └── Research Reviewer
│
├── Experiment Workspace
│
├── Data & Analysis
│
└── Research Memory
```

---

# 4. 现有项目哪些应该保留

原则：

> **已有功能优先保留，V2 做上层抽象和重组，而不是重写所有底层能力。**

## 4.1 Agent

现有 Function Calling Agent 保留。

当前工具体系可以继续作为底层 Tool Layer：

```text
search_records
search_graph
analyze_data
generate_report
list_records
evaluate_answer
```

后续不是删除，而是增加新的 Agent Orchestrator。

---

## 4.2 混合检索

当前 Keyword + Vector 的混合检索保留。

建议未来扩展为：

```text
Research Knowledge
│
├── Personal Experiment Memory
├── Literature Knowledge
└── External Scientific Knowledge
```

检索层统一：

```text
Keyword Search
+
Vector Search
+
Graph Search
+
Metadata Filter
+
Reranking
```

---

## 4.3 实验知识图谱

这是当前项目最值得保留并重点升级的资产。

不要把 Graph 当成一个“展示功能”。

应该把 Graph 升级为：

> **Research Graph**

---

# 5. Research Graph 数据模型

当前实验实体和关系可以继续使用，但需要向科研生命周期扩展。

## 核心实体

```text
ResearchProject
ResearchQuestion
Hypothesis
Experiment
ExperimentRun
Dataset
Artifact
Parameter
Observation
Analysis
Evidence
Conclusion
NextStep
Paper
Author
Method
Model
Metric
```

## 核心关系

```text
Project
  └── HAS_QUESTION → ResearchQuestion

ResearchQuestion
  └── HAS_HYPOTHESIS → Hypothesis

Hypothesis
  └── TESTED_BY → Experiment

Experiment
  └── HAS_RUN → ExperimentRun

ExperimentRun
  ├── USES_DATASET → Dataset
  ├── USES_PARAMETER → Parameter
  ├── PRODUCES → Observation
  └── PRODUCES → Artifact

Observation
  └── ANALYZED_BY → Analysis

Analysis
  └── PRODUCES → Evidence

Evidence
  └── SUPPORTS / REFUTES → Hypothesis

Experiment
  └── REFERENCES → Paper

Experiment
  └── HAS_NEXT_STEP → NextStep

NextStep
  └── GENERATES → Experiment
```

这样 Graph 不再只是：

> “我做过什么实验？”

而可以回答：

> “为什么得出这个结论？”

> “这个结论由哪些实验支持？”

> “这个实验和哪些论文相关？”

> “下一步最值得做什么？”

---

# 6. Research Agent 架构

不要让一个巨大的 Agent 负责所有任务。

建议：

```text
                         Research Agent
                               │
              ┌────────────────┼────────────────┐
              ↓                ↓                ↓
       Literature Agent   Experiment Agent   Data Agent
              │                │                │
              ↓                ↓                ↓
          Paper/RAG        Experiment Graph   Python/Jupyter
              │                │                │
              └────────────────┼────────────────┘
                               ↓
                         Reasoning Layer
                               ↓
                        Research Memory
                               ↓
                         Next Experiment
```

## 6.1 Literature Agent

负责：

- 论文搜索
- PDF 阅读
- 论文总结
- 论文对比
- 方法提取
- 实验条件提取
- 引用关系
- 研究空白分析

推荐开源基础：

- PaperQA2
- OpenAlex
- Semantic Scholar
- Docling
- Zotero

原则：

> PaperQA2 是能力组件，不是整个产品。

---

# 7. 开源项目拼接策略

核心原则：

> **能复用就不要自己造；真正形成差异化的部分才自研。**

## 第一层：学术知识

### OpenAlex

用于：

```text
Paper
Author
Institution
Concept
Citation
```

适合作为 Research Graph 的外部学术数据来源。

### Semantic Scholar

用于：

- 论文搜索
- 作者
- 引用
- 论文元数据
- 学术关系

---

## 第二层：科研论文 RAG

### PaperQA2

定位：

> Literature Agent 的底层科研检索/问答引擎。

架构：

```text
Research Agent
      ↓
Literature Agent
      ↓
PaperQA2
      ↓
Scientific Papers
```

不要把自己的产品绑定成 PaperQA2 的 UI。

---

## 第三层：文档解析

### Docling

用于：

- PDF
- 表格
- 文档结构
- 科研文档解析

统一进入：

```text
Document
    ↓
Structured Document
    ↓
Chunk
    ↓
Embedding
    ↓
Vector DB
```

---

## 第四层：实验记录

### eLabFTW

未来可以作为 ELN 基础设施。

你的产品重点放在：

```text
AI
+
Research Graph
+
Research Agent
```

而不是重复开发完整 ELN。

---

## 第五层：数据分析

推荐：

```text
Jupyter
+
Python
+
Pandas
+
SciPy
+
Scikit-learn
+
Matplotlib
```

Agent 提供受控 Python Tool：

```text
Data
 ↓
Python Sandbox
 ↓
EDA
 ↓
Statistics
 ↓
Visualization
 ↓
Interpretation
```

必须加入：

- 沙箱
- 超时
- CPU/内存限制
- 文件系统隔离
- 禁止任意网络访问
- 执行日志

---

## 第六层：向量数据库

当前 ChromaDB 可以继续用于开发阶段。

未来可以抽象 VectorStore 接口：

```text
VectorStore
├── Chroma
├── Qdrant
└── Milvus
```

这样后续生态化时可以自由替换。

---

## 第七层：知识图谱

开发阶段可以保持当前实现。

如果规模扩大：

```text
GraphStore
├── Neo4j
└── ArangoDB
```

不要让业务代码直接依赖某一个图数据库。

---

## 第八层：模型统一接口

建议增加：

```text
Model Gateway
```

例如使用 LiteLLM 一类的统一模型接口。

让系统支持：

```text
OpenAI
Anthropic
Gemini
Qwen
DeepSeek
Ollama
Local Model
```

产品 Agent 不应该直接写死某一个模型 SDK。

---

# 8. V2 最重要的新功能：Research Project

现在的 Experiment 应该被放进 Project。

结构：

```text
Research Project
│
├── Overview
├── Research Questions
├── Hypotheses
├── Literature
├── Experiments
├── Datasets
├── Analysis
├── Research Graph
├── Reports
└── AI Agent
```

---

# 9. Research Workspace

前端建议从“三栏聊天界面”逐渐升级为科研 Workspace。

推荐：

```text
┌─────────────────────────────────────────────────────┐
│ Research Project                                    │
├──────────────┬──────────────────────────────────────┤
│              │                                      │
│ Overview     │                                      │
│ Questions    │         Research Workspace           │
│ Hypotheses   │                                      │
│ Literature   │                                      │
│ Experiments  │                                      │
│ Datasets     │                                      │
│ Analysis     │                                      │
│ Graph        │                                      │
│ Reports      │                                      │
│              │                                      │
└──────────────┴──────────────────────────────────────┘
```

AI Agent 作为右侧可呼出的 Copilot：

```text
Research Agent
```

而不是让 Chat 占据整个产品。

---

# 10. V2 杀手级功能：Next Experiment

这是项目从“实验管理工具”升级到“科研 Agent”的关键。

当前系统已经有 NextStep。

V2 将其升级为：

> **AI Next Experiment Recommendation**

例如：

```text
Experiment #01
batch = 8
accuracy = 82%

Experiment #02
batch = 16
accuracy = 85%

Experiment #03
batch = 32
accuracy = 81%
```

AI 分析：

```text
当前最优区域：
batch ≈ 16

推荐下一轮：
batch = 12
batch = 16
batch = 20
```

用户确认后：

```text
Create Experiment
```

直接生成：

```text
Experiment #04
```

这一步是产品的核心体验。

---

# 11. 再进一步：Experiment Optimization

后续可以加入：

- Bayesian Optimization
- Hyperparameter Optimization
- Active Learning
- Multi-objective Optimization

形成：

```text
Historical Experiments
        ↓
Optimization Model
        ↓
Candidate Experiments
        ↓
Human Approval
        ↓
Experiment
        ↓
Result
        ↓
Update Model
        ↓
Next Candidate
```

这会让产品从：

> Research Assistant

升级到：

> Research Optimization Agent

---

# 12. 自动实验的长期方向

不要 V2 就直接做硬件自动化。

路线：

### V1

```text
AI
 ↓
实验建议
 ↓
人工执行
```

### V2

```text
AI
 ↓
Experiment Protocol
 ↓
Human Approval
 ↓
人工执行
 ↓
结果回传
```

### V3

```text
AI
 ↓
Protocol
 ↓
Automation Layer
 ↓
Lab Device
 ↓
Experiment
 ↓
Data
 ↓
AI
```

未来可研究：

- Opentrons
- PyLabRobot
- 实验仪器 API
- LIMS/ELN

---

# 13. AI Research Memory

这是长期壁垒之一。

系统需要记住：

```text
Papers
Experiments
Datasets
Parameters
Errors
Solutions
Conclusions
Hypotheses
Code
Reports
```

例如用户问：

> 为什么这个实验失败？

系统应该能够关联：

```text
当前实验
 ↓
相似历史实验
 ↓
历史参数
 ↓
历史错误
 ↓
相关论文
 ↓
可能原因
```

而不是只做向量相似度搜索。

---

# 14. Research Memory 与 Graph 的关系

不要二选一。

两者分工：

### Vector Memory

负责：

> “什么内容和当前问题相似？”

### Graph Memory

负责：

> “这些内容之间是什么关系？”

### Structured Database

负责：

> “准确的数据是什么？”

最终：

```text
Structured DB
      +
Vector DB
      +
Graph DB
      ↓
Research Memory
```

---

# 15. Agent Tool 体系

建议未来统一 Tool Registry：

```text
tools/
├── literature/
│   ├── search_papers
│   ├── read_paper
│   ├── compare_papers
│   └── find_citations
│
├── research/
│   ├── search_experiments
│   ├── search_graph
│   ├── create_hypothesis
│   ├── create_experiment
│   └── recommend_next_experiment
│
├── data/
│   ├── load_dataset
│   ├── analyze_data
│   ├── run_python
│   └── generate_plot
│
├── reporting/
│   ├── generate_report
│   └── generate_summary
│
└── external/
    ├── OpenAlex
    ├── SemanticScholar
    └── other plugins
```

---

# 16. Plugin Architecture

生态化不要从“做很多功能”开始。

应该从：

> **允许别人接入科研能力**

开始。

定义统一 Plugin Protocol：

```text
Plugin
├── metadata
├── tools
├── data_schema
├── auth
├── permissions
└── lifecycle
```

例如：

```text
plugins/
├── paperqa
├── openalex
├── semantic-scholar
├── zotero
├── elabftw
├── jupyter
├── rdkit
├── biopython
├── pymatgen
├── opentrons
└── custom-lab
```

最终：

> 任何科研工具只要符合 Plugin Protocol，就可以接入 ResearchOS。

---

# 17. MCP 生态

后期可以把 Plugin Tool 暴露成 MCP Server。

形成：

```text
ResearchOS
     ↓
MCP
     ↓
External Scientific Tools
```

这样可以接：

- 文献
- 数据库
- GitHub
- 实验室
- 数据分析
- 云计算
- 本地工具

MCP 应该作为生态层，而不是 V1 的核心业务逻辑。

---

# 18. 数据层建议

建议逐步把数据抽象为：

```text
PostgreSQL / MySQL
       │
       ├── User
       ├── Project
       ├── Experiment
       ├── Dataset
       ├── Hypothesis
       ├── Analysis
       └── Artifact

Vector DB
       │
       └── Semantic Memory

Graph DB
       │
       └── Research Graph

Object Storage
       │
       ├── PDF
       ├── Dataset
       ├── Images
       ├── Experiment Output
       └── Reports
```

---

# 19. Artifact 系统

这是 V2 很值得增加的一层。

科研过程中所有东西都应该成为 Artifact：

```text
Artifact
├── Paper
├── Dataset
├── Code
├── Notebook
├── Image
├── Chart
├── Model
├── Experiment Result
├── Report
└── Protocol
```

每一个 Artifact 都有：

```text
id
type
version
created_at
created_by
source
hash
metadata
relationships
```

这样以后可以实现科研可追溯性。

---

# 20. Experiment Run 与 Experiment 分离

建议不要让 Experiment 同时承担“实验方案”和“实验执行”。

区分：

```text
Experiment
    │
    ├── hypothesis
    ├── protocol
    ├── variables
    └── expected_result

ExperimentRun #01
    ├── actual_parameters
    ├── dataset
    ├── logs
    └── result

ExperimentRun #02
    ├── actual_parameters
    ├── dataset
    ├── logs
    └── result
```

这样以后做自动实验非常重要。

---

# 21. 版本控制

科研实验必须可追溯。

建议：

```text
Experiment
v1
v2
v3

Dataset
v1
v2

Protocol
v1
v2

Analysis
v1
v2
```

最终能够回答：

> 这个结论是基于哪个版本的数据？

> 这个实验使用的参数是什么？

> 这个图表由哪个分析脚本生成？

---

# 22. AI 输出必须 Evidence Grounded

科研 Agent 不应该只输出：

> “我认为……”

应该输出：

```text
Conclusion
    ↓
Evidence
    ├── Experiment #12
    ├── Dataset #03
    └── Paper #27
```

每个关键结论尽可能提供：

```text
Source
Evidence
Confidence
Reasoning Summary
```

注意：

> 不要把内部 Chain-of-Thought 暴露出来；产品展示应提供简洁、可验证的证据摘要，而不是隐藏推理过程。

---

# 23. 科研可信性设计

必须重点解决：

## Hallucination

解决：

```text
Citation
+
Evidence
+
Source
+
Confidence
```

## Data Leakage

解决：

```text
实验数据权限
项目权限
Agent Tool 权限
```

## Python 风险

必须 Sandbox。

## 自动实验风险

必须：

```text
AI Proposal
 ↓
Human Approval
 ↓
Execution
```

至少在早期版本不要允许 AI 无审批执行真实实验。

---

# 24. 第一阶段不要做什么

以下功能暂时不要优先：

- 全领域科研
- 全自动实验室
- 自研大模型
- 自研完整 ELN
- 自研论文数据库
- 自研复杂向量数据库
- 自研完整 Notebook
- 复杂多人协作
- 一开始就支持所有仪器

原因：

> 这些都会严重稀释核心价值。

---

# 25. V2 第一阶段只做 5 件事

## P0-1 Research Project

把：

```text
Experiment
```

提升到：

```text
Research Project
```

---

## P0-2 Research Question + Hypothesis

增加：

```text
Question
Hypothesis
```

并关联到 Experiment。

---

## P0-3 Literature Agent

接入：

```text
OpenAlex
Semantic Scholar
PaperQA2
```

实现：

```text
Search
Read
Compare
Cite
Research Gap
```

---

## P0-4 Next Experiment

实现：

```text
历史实验
 ↓
AI分析
 ↓
候选实验
 ↓
人工确认
 ↓
创建 Experiment
```

---

## P0-5 Research Graph V2

让 Graph 从：

> Experiment Graph

升级：

> Research Graph

---

# 26. 推荐 V2 开发顺序

```text
Phase 1
Research Project
        ↓
Phase 2
Question / Hypothesis
        ↓
Phase 3
Research Graph V2
        ↓
Phase 4
Literature Agent
        ↓
Phase 5
Next Experiment
        ↓
Phase 6
Data Agent
        ↓
Phase 7
Artifact / Versioning
        ↓
Phase 8
Plugin System
        ↓
Phase 9
MCP
        ↓
Phase 10
Experiment Automation
```

---

# 27. 代码架构建议

建议逐步从：

```text
src/
├── agent
├── tools
├── graph
└── ...
```

演进为：

```text
backend/
├── api/
├── domain/
│   ├── research/
│   ├── experiment/
│   ├── literature/
│   ├── dataset/
│   └── analysis/
│
├── agent/
│   ├── orchestrator/
│   ├── agents/
│   ├── tools/
│   └── memory/
│
├── infrastructure/
│   ├── database/
│   ├── vector/
│   ├── graph/
│   ├── storage/
│   └── model/
│
└── plugins/
    ├── literature/
    ├── analysis/
    └── experiment/
```

前端：

```text
frontend/
├── pages/
│   ├── projects/
│   ├── questions/
│   ├── hypotheses/
│   ├── literature/
│   ├── experiments/
│   ├── datasets/
│   ├── analysis/
│   ├── graph/
│   └── reports/
│
├── components/
├── agent/
└── stores/
```

不要一次性重构全部代码。

---

# 28. API 设计方向

建议未来 API 围绕 Research Domain，而不是 Agent Function。

例如：

```text
/api/projects
/api/projects/{id}/questions
/api/projects/{id}/hypotheses
/api/projects/{id}/experiments
/api/projects/{id}/runs
/api/projects/{id}/datasets
/api/projects/{id}/literature
/api/projects/{id}/graph
/api/projects/{id}/analysis
/api/projects/{id}/reports
/api/projects/{id}/agent
```

Agent Tool 再调用这些 Domain API/Service。

这样 Agent 和业务逻辑解耦。

---

# 29. Agent Orchestrator

最终结构建议：

```text
User
 ↓
Research Agent
 ↓
Intent / Task Router
 ↓
┌──────────────────────────────┐
│ Literature Task              │
│ Experiment Task              │
│ Data Task                    │
│ Analysis Task                │
│ Reporting Task               │
└──────────────────────────────┘
 ↓
Tool Registry
 ↓
External Plugins
```

不要让每个 Agent 自己实现数据库访问。

---

# 30. 生态化路线

## 第一阶段：单体产品

```text
ResearchOS
```

---

## 第二阶段：Plugin

```text
ResearchOS
+
Scientific Plugins
```

---

## 第三阶段：MCP

```text
ResearchOS
+
MCP Scientific Ecosystem
```

---

## 第四阶段：Research Marketplace

未来可以形成：

```text
Plugin Marketplace
│
├── AI Models
├── Literature
├── Datasets
├── Analysis
├── Domain Tools
├── Lab Automation
└── Instruments
```

这才是长期生态。

---

# 31. 最终产品形态

最终希望用户进入系统后不是看到：

> “有什么可以帮你的吗？”

而是：

```text
Good afternoon.

Your research project has 3 active hypotheses.

H1
Transformer scaling improves small-data performance.
Status: Testing

H2
Data augmentation improves robustness.
Status: Supported

H3
Current performance is limited by dataset diversity.
Status: Needs evidence.

Recommended next experiment:
Test augmentation strategy A/B/C.

Estimated information gain: High
Reason: Current evidence is insufficient around augmentation.
```

用户点击：

> **Run Next Experiment**

然后进入实验流程。

这才是 ResearchOS 的产品体验。

---

# 32. 最终技术架构

```text
                         ┌─────────────────────┐
                         │      ResearchOS     │
                         └──────────┬──────────┘
                                    │
                         ┌──────────▼──────────┐
                         │   Research Agent    │
                         └──────────┬──────────┘
                                    │
             ┌──────────────────────┼──────────────────────┐
             ↓                      ↓                      ↓
      Literature Agent       Experiment Agent        Data Agent
             │                      │                      │
        PaperQA2                Research Graph          Jupyter
        OpenAlex                     │                 Python
        Semantic Scholar             │              Pandas/SciPy
             │                       │                      │
             └───────────────────────┼──────────────────────┘
                                     ↓
                            Research Memory
                                     │
                  ┌──────────────────┼──────────────────┐
                  ↓                  ↓                  ↓
             Structured DB       Vector DB          Graph DB
                  │                  │                  │
                  └──────────────────┼──────────────────┘
                                     ↓
                               Artifact Store
                                     │
                                     ↓
                              Research Loop
                                     │
             ┌───────────────────────┴───────────────────────┐
             ↓                                               ↓
        Human Execution                               Automation
                                                             │
                                                    Opentrons /
                                                    PyLabRobot /
                                                    Instruments
```

---

# 33. 项目真正的核心壁垒

不要把壁垒理解成：

> “用了哪个模型。”

模型会越来越便宜。

真正应该积累：

### 1. Research Graph

知道科研对象之间的关系。

### 2. Research Memory

知道用户过去做过什么。

### 3. Experiment History

知道什么方法成功、什么方法失败。

### 4. Research Loop

知道如何从一个实验进入下一实验。

### 5. Agent Tool Ecosystem

能够调用越来越多的科研工具。

### 6. Research Artifact Lineage

知道每个结论来自什么数据和实验。

---

# 34. 产品一句话

建议最终对外定位：

> **ResearchOS：让 AI 从科研信息助手，进化为能够理解实验、分析证据并推动下一步研究的科研智能操作系统。**

或者更短：

> **AI-native operating system for scientific research.**

---

# 35. 最终判断

当前 Experiment Agent：

```text
实验记录
   ↓
检索
   ↓
知识图谱
   ↓
AI复盘
```

V2：

```text
研究问题
   ↓
假设
   ↓
实验
   ↓
数据
   ↓
分析
   ↓
结论
   ↓
下一实验
```

V3：

```text
研究问题
   ↓
AI提出假设
   ↓
AI设计实验
   ↓
Human Approval
   ↓
自动执行
   ↓
数据分析
   ↓
更新Research Graph
   ↓
AI提出下一实验
```

V4：

```text
ResearchOS
+
Plugin Ecosystem
+
MCP
+
Scientific Tools
+
Lab Automation
```

最终形成：

> **一个不是“帮科研人员聊天”的 AI，而是围绕科研实验生命周期构建的 AI 原生操作系统。**

---

# 36. 开发原则

最后整个项目坚持以下原则：

1. **不推倒重做**
2. **现有 Experiment Agent 作为核心底座**
3. **Graph 从 Experiment Graph 升级为 Research Graph**
4. **Agent 从 Experiment Agent 升级为 Research Agent**
5. **优先复用成熟开源项目**
6. **不重复造 ELN、论文数据库、Notebook 等基础设施**
7. **真正差异化的部分集中在 Research Loop**
8. **所有 AI 结论尽量 Evidence Grounded**
9. **实验执行默认 Human-in-the-loop**
10. **从第一天就考虑 Plugin Architecture**
11. **后期使用 MCP 扩展生态**
12. **先做 AI/计算机科研场景，再扩展到其他学科**
13. **先解决“下一步做什么实验”，再考虑自动实验室**
14. **所有科研结果可追溯、可版本化、可复现**
15. **不要为了“生态”而生态，先形成真实可用的科研闭环**

---

## 37. V2 最终验收标准

V2 不应该以“增加了多少页面”作为完成标准，而应该满足：

```text
用户创建 Research Project
        ↓
提出 Research Question
        ↓
AI 帮助形成 Hypothesis
        ↓
检索相关论文
        ↓
设计 Experiment
        ↓
执行 Experiment
        ↓
上传/生成 Dataset
        ↓
AI 分析结果
        ↓
结果进入 Research Graph
        ↓
形成 Evidence / Conclusion
        ↓
AI 根据历史实验和文献推荐 Next Experiment
        ↓
用户确认
        ↓
一键创建下一轮 Experiment
```

如果这个闭环跑通：

> **Experiment Agent V2 就真正从“实验助手”变成了 ResearchOS 的雏形。**
