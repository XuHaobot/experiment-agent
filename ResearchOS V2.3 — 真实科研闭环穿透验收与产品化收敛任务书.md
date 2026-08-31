# ResearchOS V2.3 — 真实科研闭环穿透验收与产品化收敛任务书

> **版本：V2.3**
> **任务性质：验收 + 收敛 + 必要修复**
> **基准版本：ResearchOS V2.2 — Open Research Stack**
> **核心原则：不推倒重做、不无脑加功能，先审计、再穿透测试、最后只修真实断点。**

---

# 0. 本阶段最高目标

ResearchOS V2.2 已经完成：

* Local-First 架构
* Domain 层解耦
* OpenAlex / arXiv / Semantic Scholar
* DuckDB / SQLite fallback
* Jupyter Notebook
* MLflow
* RestrictedPython / DockerRunner 抽象
* ToolRegistry
* Paper / Dataset
* Literature API
* Research Graph
* Research Memory
* Evidence / Artifact 扩展

因此，**V2.3 不再以“增加能力数量”为目标。**

本阶段唯一核心目标：

> **证明 ResearchOS 已经能够围绕一个真实科研问题，完成“文献 → 证据 → 假说 → 实验 → 数据 → Run → Artifact → 结论 → 下一实验”的真实闭环，并且每一个关键结论都可以追溯到真实来源。**

最终必须能够回答：

> **“ResearchOS 到底是不是一个真正的科研工作台，而不是一个把论文、数据集、Agent、Graph 拼在一起的 Demo？”**

---

# 1. ⚠️ 最高级开发原则

## 1.1 禁止推倒重做

不得：

* 重写 Domain
* 重构现有 Agent 架构
* 替换 LangGraph
* 替换 Local-First 存储
* 替换 ToolRegistry
* 替换 Research Graph
* 替换现有 Literature Adapter
* 为了“更漂亮”而重写已有稳定代码

只有在发现**真实数据断点、数据一致性问题或安全问题**时才允许局部修改。

---

# 2. 🚫 本阶段禁止新增大型功能

以下全部冻结：

```text
MCP Server
Multi-Agent Framework
Agent Swarm
复杂 Workflow Builder
云端数据库
用户系统
团队协作
在线 JupyterLab
复杂插件市场
论文全文爬虫
大规模向量数据库
复杂 RAG 基础设施
```

特别注意：

> **不要因为发现 PaperQA2、MCP、LangChain、LlamaIndex 等技术而主动集成。**

本阶段不是技术栈扩张阶段。

---

# 3. V2.3 核心验收链路

必须验证以下完整链路：

```text
Project
   │
   ├── Paper
   │
   ▼
Literature Search
   │
   ▼
Paper Saved
   │
   ▼
Evidence
   │
   ▼
Hypothesis
   │
   ▼
Experiment
   │
   ▼
Dataset
   │
   ▼
Execution / Run
   │
   ▼
Artifact
   │
   ▼
Conclusion
   │
   ▼
NextExperiment
   │
   └──────────────→ 新 Hypothesis / Experiment
```

目标不是每个模块“API 返回 200”。

而是：

> **同一个真实 Project 中，所有对象必须互相建立真实关系。**

---

# 4. 第一阶段：全项目只读审计

## 4.1 先不要修改代码

首先对当前 V2.2 代码进行只读审计。

检查：

```text
backend/domain/
backend/integrations/
backend/agents/
backend/tools/
backend/api/
backend/graph/
backend/memory/
frontend/
tests/
data/
```

输出：

```text
docs/V2.3_PRE_AUDIT.md
```

---

# 5. 审计必须回答以下 15 个问题

## Q1

`Project` 是否可以真实关联：

```text
Paper
Dataset
Hypothesis
Experiment
Run
Artifact
Evidence
Conclusion
NextExperiment
```

不能只存在字段定义。

必须检查实际写入和读取。

---

## Q2

Paper 保存以后：

```text
Project
   ↓
Paper
```

是否能够反向查询？

---

## Q3

Paper 能否真正形成 Evidence？

要求：

```text
Paper
 ↓
Evidence
 ↓
source_type = paper
 ↓
source_id = paper_id
```

---

## Q4

Evidence 能否支持 Hypothesis？

必须存在真实关系：

```text
Hypothesis
 ↓
Evidence
```

不能只是文本中提到 Paper。

---

## Q5

Hypothesis 是否能进入 Experiment？

要求：

```text
Hypothesis
 ↓
Experiment
```

并且能够查询来源假说。

---

## Q6

Experiment 是否能产生 Run？

要求：

```text
Experiment
 ↓
Run
```

Run 必须具有：

* run_id
* experiment_id
* status
* parameters
* metrics
* created_at

---

# 6. Dataset 穿透测试

必须创建一个真实测试 Dataset。

例如：

```csv
sample_id,group,value
1,A,10.2
2,A,11.4
3,A,9.8
4,B,15.1
5,B,14.7
6,B,16.2
```

要求真实写入：

```text
data/datasets/
```

而不是测试时直接构造 Python dict。

---

## Dataset 必须验证

```text
dataset_id
file_path
checksum
columns
row_count
created_at
```

全部真实存在。

---

# 7. DuckDB / SQLite 穿透测试

执行真实查询：

```sql
SELECT group, AVG(value)
FROM dataset
GROUP BY group;
```

要求：

```text
A ≈ 10.47
B ≈ 15.33
```

不得：

* 写死答案
* Mock 查询结果
* LLM 生成结果
* 从 metadata 猜结果

---

# 8. Dataset → Evidence

这是重点。

如果某次分析产生：

```text
Group A mean = 10.47
Group B mean = 15.33
```

必须允许将这个分析结果沉淀为：

```text
Evidence
```

并记录：

```text
source_type = dataset
source_id = dataset_id
query / analysis provenance
```

最终可以回答：

> 这个结论的数据依据是什么？

并返回：

```text
Dataset → Query → Evidence
```

---

# 9. Experiment → Run 穿透测试

使用当前已有的 Experiment / Execution 能力。

不要求复杂机器学习训练。

可以使用最简单的统计实验：

```text
Experiment:
比较 A/B 两组 value 均值

Dataset:
test_dataset.csv

Execution:
Python / RestrictedPython

Output:
mean_A
mean_B
difference
```

必须真实执行。

---

# 10. Run → Artifact

实验执行以后必须产生真实 Artifact。

例如：

```text
results.json
analysis.csv
experiment_output.txt
```

Artifact 必须记录：

```text
artifact_id
run_id
path
mime_type
created_at
checksum
```

验证：

```text
Run
 ↓
Artifact
```

可以反向追踪。

---

# 11. Artifact → Evidence

如果 Artifact 中包含实验结果：

```text
results.json
```

则允许沉淀：

```text
Evidence
source_type = artifact
source_id = artifact_id
```

最终形成：

```text
Dataset
   ↓
Experiment
   ↓
Run
   ↓
Artifact
   ↓
Evidence
```

---

# 12. Conclusion 穿透测试

创建一个真实 Conclusion：

例如：

> “在当前测试数据中，B 组的平均值高于 A 组。”

Conclusion 必须能够引用：

```text
Evidence
```

而不是只有一段字符串。

要求形成：

```text
Evidence
 ↓
Conclusion
```

---

# 13. Conclusion → NextExperiment

这是 V2.3 最重要的产品价值之一。

要求：

```text
Conclusion
 ↓
NextExperiment
```

例如：

```text
当前发现：
B 组均值高于 A 组

下一实验：
扩大样本量并重复实验，
验证差异是否稳定。
```

必须能够：

* 创建
* 保存
* 查询
* 回溯来源

---

# 14. 完整科研闭环测试

最终必须真实执行：

```text
创建 Project
      ↓
搜索 Paper
      ↓
保存 Paper
      ↓
创建 Evidence
      ↓
创建 Hypothesis
      ↓
创建 Experiment
      ↓
创建 Dataset
      ↓
执行真实分析
      ↓
创建 Run
      ↓
生成 Artifact
      ↓
生成 Evidence
      ↓
生成 Conclusion
      ↓
生成 NextExperiment
```

---

# 15. Research Graph 穿透验收

Graph 不允许只是“节点展示”。

必须验证真实数据关系。

至少存在：

```text
Project
 ├─ REFERENCES → Paper
 │
 ├─ HAS_DATASET → Dataset
 │
 ├─ HAS_HYPOTHESIS → Hypothesis
 │
 └─ HAS_EXPERIMENT → Experiment

Paper
 └─ SUPPORTS → Evidence

Evidence
 └─ SUPPORTS → Conclusion

Hypothesis
 └─ TESTED_BY → Experiment

Experiment
 └─ PRODUCES → Run

Run
 └─ PRODUCES → Artifact

Artifact
 └─ SUPPORTS → Evidence

Conclusion
 └─ LEADS_TO → NextExperiment
```

---

# 16. Graph 双向回溯测试

必须测试：

### 正向

```text
Project
→ Paper
→ Evidence
→ Conclusion
```

### 反向

```text
Conclusion
→ Evidence
→ Paper
→ Project
```

再测试：

```text
Conclusion
→ Evidence
→ Artifact
→ Run
→ Experiment
→ Hypothesis
```

如果任意一条无法回溯：

> 标记为 P0 数据血缘断点。

---

# 17. Research Memory 验收

验证：

```text
get_project_research_memory(project_id)
```

是否真实包含：

```text
papers
datasets
hypotheses
experiments
runs
artifacts
evidence
conclusions
next_experiments
```

---

# 18. Memory 禁止幻觉

创建一个测试：

```text
Project A
```

保存：

```text
Paper A
Dataset A
Conclusion A
```

然后询问 Agent：

> “这个课题目前有哪些证据支持我们的结论？”

Agent 必须只能引用 Project A 中真实存在的数据。

不得凭空产生：

```text
Paper B
Dataset B
实验结果 C
```

---

# 19. Agent 引用规范

如果 Agent 使用科研事实，必须能够指出来源。

推荐格式：

```text
根据 Paper: P-001
根据 Dataset: D-001
根据 Run: R-001
根据 Artifact: A-001
根据 Evidence: E-001
```

不要求 UI 一开始就做得复杂。

但底层数据必须存在。

---

# 20. Agent 回答分级

建立：

```text
SUPPORTED
PARTIALLY_SUPPORTED
UNSUPPORTED
```

### SUPPORTED

有真实 Evidence 支撑。

### PARTIALLY_SUPPORTED

部分事实有证据，部分为推理。

### UNSUPPORTED

项目中不存在可靠依据。

---

# 21. Agent 禁止伪装事实

例如用户问：

> “这个实验已经证明假说了吗？”

如果没有 Run / Evidence：

Agent 必须回答：

```text
目前不能证明。

当前项目中只有：
Hypothesis H-001

尚未找到：
Run
Evidence
Conclusion

因此只能认为该假说处于待验证状态。
```

而不是：

> “实验结果表明……”

---

# 22. Literature 真实数据验收

分别测试：

```text
OpenAlex
arXiv
Semantic Scholar
```

至少各完成一次真实查询。

检查：

```text
title
authors
year
abstract
paper_id
source
url
```

不得使用静态测试数据冒充真实结果。

---

# 23. Literature → Project

验证：

```text
搜索论文
 ↓
保存至项目
 ↓
Project.paper_ids
 ↓
Paper
```

再：

```text
GET /api/projects/{project_id}/papers
```

必须能查回来。

---

# 24. Literature Adapter 故障处理

模拟：

```text
OpenAlex unavailable
arXiv unavailable
Semantic Scholar unavailable
```

检查：

* 是否崩溃
* 是否错误污染 Domain
* 是否泄漏异常
* 是否错误显示“搜索成功”

必须诚实显示：

```text
source unavailable
```

---

# 25. PaperQA2 继续保持可选

本阶段：

```text
PaperQA2 = OPTIONAL
```

禁止为了“功能完整”强制安装。

只验证：

```text
integration interface
documentation
future extension point
```

即可。

---

# 26. Notebook 验收

准备一个最小 Notebook：

```text
test.ipynb
```

至少包含：

```text
Code Cell
Markdown Cell
Output
```

执行：

```text
Notebook Import
```

验证：

```text
Notebook
 ↓
Artifact
```

并保留：

```text
source path
cell count
metadata
```

---

# 27. MLflow 验收

如果本机已有：

```text
mlruns/
```

则测试：

```text
MLflow
 ↓
Run
```

如果不存在：

> 不允许伪造 MLflow 数据。

可以：

```text
SKIPPED — mlruns not available
```

---

# 28. Execution 安全验收

## RestrictedPython

验证：

```text
正常计算
```

以及：

```text
文件访问
系统调用
危险 import
```

是否被限制。

---

# 29. DockerRunner

当前保持：

```text
PARTIAL
```

不要强制要求安装 Docker。

验证：

```text
Docker installed
→ 可执行

Docker unavailable
→ 清晰降级
```

---

# 30. 数据血缘完整性测试

这是本阶段的核心测试。

最终输出一张真实数据血缘：

```text
Project P001

Paper P001
    ↓
Evidence E001
    ↓
Hypothesis H001
    ↓
Experiment EXP001
    ↓
Dataset D001
    ↓
Run R001
    ↓
Artifact A001
    ↓
Evidence E002
    ↓
Conclusion C001
    ↓
NextExperiment N001
```

要求每个 ID 都真实存在。

---

# 31. 数据血缘反向查询

至少支持：

```text
Conclusion
→ Evidence
→ Artifact
→ Run
→ Experiment
→ Dataset
```

以及：

```text
Conclusion
→ Evidence
→ Paper
→ Project
```

---

# 32. 一致性检查

检查：

```text
删除 Paper
删除 Dataset
删除 Experiment
删除 Artifact
```

时是否产生：

```text
孤儿 Evidence
孤儿 Graph Node
孤儿 Memory Reference
```

如果存在：

> 修复引用一致性。

但不要为了这个问题重新设计数据库。

---

# 33. API 验收

现有 API 必须全部跑一次。

重点：

```text
/api/literature/search
/api/literature/paper/{paper_id}

/api/projects/{project_id}/papers
/api/projects/{project_id}/datasets

/api/datasets/{dataset_id}
/api/datasets/{dataset_id}/query
/api/datasets/{dataset_id}/summary

/api/projects/{project_id}/notebooks/import

/api/integrations/mlflow/sync
```

要求：

```text
正常输入
空输入
非法 ID
不存在资源
外部 API 失败
```

都具有明确行为。

---

# 34. 前端验收

重点不是视觉大改。

只验证：

### LiteraturePanel

```text
在线检索
保存至项目
项目文献
提取假说
```

### Dataset

```text
创建
查看
Summary
Query
```

### Research Graph

确认：

```text
Paper
Dataset
Evidence
Experiment
Run
Artifact
Conclusion
```

可以真实显示。

---

# 35. UI 禁止硬编码

检查：

```text
paper count
dataset count
run count
evidence count
conclusion count
score
status
```

不得使用：

```text
3
12
95%
Completed
```

之类硬编码值冒充真实状态。

---

# 36. Mock 扫描

全项目搜索：

```text
mock
Mock
MOCK
fake
Fake
dummy
placeholder
TODO
hardcoded
sample
demo
```

输出：

```text
docs/V2.3_MOCK_AUDIT.md
```

分类：

```text
SAFE
DEMO_ONLY
DANGEROUS
```

---

# 37. Mock 处理原则

### SAFE

测试 fixture：

```text
tests/fixtures/
```

可以保留。

### DEMO_ONLY

明确标记：

```text
Demo Data
```

### DANGEROUS

任何可能让用户误认为是真实科研结果的数据：

> 必须删除。

---

# 38. Fake Scientific Result 禁止

尤其检查：

```text
accuracy
loss
p-value
confidence
sample size
experimental result
paper citation
```

不能存在硬编码“看起来像真实科研结果”的数据。

---

# 39. Test Suite

新增：

```text
tests/test_v23_research_closure.py
```

至少覆盖：

```text
1. Project creation
2. Paper search
3. Paper persistence
4. Paper → Evidence
5. Evidence → Hypothesis
6. Hypothesis → Experiment
7. Dataset creation
8. Dataset query
9. Experiment → Run
10. Run → Artifact
11. Artifact → Evidence
12. Evidence → Conclusion
13. Conclusion → NextExperiment
14. Research Graph
15. Reverse provenance
16. Research Memory
17. Agent citation
18. Unsupported claim rejection
19. Mock scan
20. API error handling
```

---

# 40. 测试分为两层

## Layer A — Offline

不依赖网络：

```text
Domain
Graph
Memory
Dataset
DuckDB/SQLite
Evidence
Execution
```

必须：

```text
100% PASS
```

---

## Layer B — Live

真实访问：

```text
OpenAlex
arXiv
Semantic Scholar
```

如果网络不可用：

```text
SKIPPED
```

不能：

```text
用 Mock 数据冒充 PASS
```

---

# 41. 回归测试

必须继续运行 V2.2：

```bash
.\venv\Scripts\python.exe tests/test_v22_open_research_stack.py
```

```bash
.\venv\Scripts\python.exe tests/test_v21_research_workflow.py
```

```bash
.\venv\Scripts\python.exe tests/test_research_loop_audit.py
```

```bash
.\venv\Scripts\python.exe tests/test_p0_acceptance.py
```

以及：

```bash
.\venv\Scripts\python.exe tests/test_v23_research_closure.py
```

---

# 42. 前端生产构建

执行：

```bash
cd frontend
npm run build
```

要求：

```text
0 errors
```

---

# 43. 最终 E2E 穿透测试

必须生成：

```text
docs/V2.3_E2E_CLOSURE_REPORT.md
```

至少记录：

```text
Project ID
Paper ID
Evidence ID
Hypothesis ID
Experiment ID
Dataset ID
Run ID
Artifact ID
Conclusion ID
NextExperiment ID
```

---

# 44. 最终验收表

报告必须给出：

| 模块               | 状态  |
| ------------------ | ----- |
| Project            | 🟢/🟡/🔴 |
| Literature         | 🟢/🟡/🔴 |
| Paper              | 🟢/🟡/🔴 |
| Evidence           | 🟢/🟡/🔴 |
| Hypothesis         | 🟢/🟡/🔴 |
| Experiment         | 🟢/🟡/🔴 |
| Dataset            | 🟢/🟡/🔴 |
| Run                | 🟢/🟡/🔴 |
| Artifact           | 🟢/🟡/🔴 |
| Conclusion         | 🟢/🟡/🔴 |
| NextExperiment     | 🟢/🟡/🔴 |
| Research Graph     | 🟢/🟡/🔴 |
| Research Memory    | 🟢/🟡/🔴 |
| Agent Grounding    | 🟢/🟡/🔴 |
| Notebook           | 🟢/🟡/🔴 |
| MLflow             | 🟢/🟡/🔴 |
| Execution Security | 🟢/🟡/🔴 |

---

# 45. 最终评级规则

## 🟢 GREEN

必须满足：

```text
核心科研闭环真实跑通
+
数据血缘完整
+
Graph 可回溯
+
Memory 不产生虚假事实
+
Agent 能引用真实来源
+
没有 P0 Mock
+
V2.2 回归测试全部通过
```

---

## 🟡 YELLOW

存在：

```text
非核心功能 Partial
+
外部服务不可用
+
Docker 环境限制
+
MLflow 本机不存在
```

但：

```text
核心科研闭环真实成立
```

---

## 🔴 RED

出现任意：

```text
Evidence 无法追溯
Paper / Dataset 数据是假数据
Agent 把推测当事实
Graph 只是 UI 假节点
Conclusion 无 Evidence
Run 无 Experiment
Artifact 无 Run
核心数据关系断裂
P0 Mock 冒充真实科研结果
```

---

# 46. 最终产品化收敛原则

如果测试发现问题：

### P0

立即修复。

例如：

```text
数据丢失
数据血缘断裂
错误引用
Agent 幻觉成事实
真实 API 数据没有落地
核心对象无法关联
```

### P1

如果影响核心体验：

> 修复。

否则：

> 记录，不扩张范围。

### P2

全部记录到：

```text
docs/V2.4_BACKLOG.md
```

不要本阶段实现。

---

# 47. 特别禁止 QoderWork 做的事情

⚠️ **非常重要**

在没有发现实际断点前，不允许：

```text
❌ 增加 MCP
❌ 增加 Multi-Agent
❌ 增加新的 LLM
❌ 增加新的向量数据库
❌ 增加新的数据库
❌ 重构 Domain
❌ 重写 Graph
❌ 重写 Agent
❌ 引入 LangChain/LlamaIndex 仅为了“更专业”
❌ 为测试通过制造 Mock
❌ 用硬编码结果替代真实执行
❌ 为了 Green 强行修改验收标准
```

---

# 48. 如果发现现有设计不合理

必须遵循：

```text
发现问题
 ↓
定位实际代码
 ↓
确认是否影响核心闭环
 ↓
给出最小修改方案
 ↓
局部修复
 ↓
运行对应测试
 ↓
运行全部回归测试
```

不要直接大规模重构。

---

# 49. 最终需要提交的文件

执行完成后必须产生：

```text
docs/
├── V2.3_PRE_AUDIT.md
├── V2.3_MOCK_AUDIT.md
├── V2.3_E2E_CLOSURE_REPORT.md
├── V2.3_PROVENANCE_REPORT.md
└── V2.4_BACKLOG.md

tests/
└── test_v23_research_closure.py
```

---

# 50. 最终报告必须回答的 12 个问题

## Q1

一个 Paper 能否真实成为 Evidence？

## Q2

一个 Evidence 能否支撑一个 Hypothesis？

## Q3

一个 Hypothesis 能否进入 Experiment？

## Q4

一个 Experiment 能否产生真实 Run？

## Q5

一个 Run 能否产生真实 Artifact？

## Q6

一个 Artifact 能否形成 Evidence？

## Q7

一个 Evidence 能否支撑 Conclusion？

## Q8

一个 Conclusion 能否产生 NextExperiment？

## Q9

Research Graph 是否可以完整双向回溯？

## Q10

Research Memory 是否只包含真实项目事实？

## Q11

Agent 是否能够明确告诉用户：

> “这句话的证据来自哪里？”

## Q12

一个新用户是否真的可以使用 ResearchOS 完成一次最小科研闭环？

---

# 51. 最终验收输出格式

执行完成后，不要只告诉我：

```text
所有测试通过
```

必须按照下面格式返回：

```text
============================================================
ResearchOS V2.3 — FINAL ACCEPTANCE
============================================================

版本：
V2.3

总体评级：
🟢 GREEN / 🟡 YELLOW / 🔴 RED

核心科研闭环：
Project
→ Paper
→ Evidence
→ Hypothesis
→ Experiment
→ Dataset
→ Run
→ Artifact
→ Evidence
→ Conclusion
→ NextExperiment

状态：
PASS / PARTIAL / FAIL

------------------------------------------------------------
数据血缘
------------------------------------------------------------

Paper → Evidence       PASS
Evidence → Hypothesis PASS
Hypothesis → Experiment PASS
Experiment → Run      PASS
Run → Artifact        PASS
Artifact → Evidence   PASS
Evidence → Conclusion PASS
Conclusion → NextExperiment PASS

------------------------------------------------------------
Research Graph
------------------------------------------------------------

Forward Traversal : PASS / FAIL
Reverse Traversal : PASS / FAIL

------------------------------------------------------------
Research Memory
------------------------------------------------------------

真实事实读取：PASS / FAIL
幻觉阻断：PASS / FAIL
来源引用：PASS / FAIL

------------------------------------------------------------
Agent Grounding
------------------------------------------------------------

Paper Citation    PASS / FAIL
Dataset Citation  PASS / FAIL
Run Citation      PASS / FAIL
Evidence Citation PASS / FAIL
Unsupported Claim PASS / FAIL

------------------------------------------------------------
External Integrations
------------------------------------------------------------

OpenAlex          PASS / FAIL / SKIPPED
arXiv             PASS / FAIL / SKIPPED
Semantic Scholar  PASS / FAIL / SKIPPED
DuckDB            PASS / FAIL
Jupyter           PASS / FAIL
MLflow            PASS / FAIL / SKIPPED
Docker            PASS / PARTIAL / SKIPPED

------------------------------------------------------------
Regression
------------------------------------------------------------

V2.1: PASS / FAIL
V2.2: PASS / FAIL
V2.3: PASS / FAIL

------------------------------------------------------------
Mock Audit
------------------------------------------------------------

Dangerous Mock : 0 / N
Demo Mock      : N
Safe Fixture   : N

------------------------------------------------------------
P0 Issues
------------------------------------------------------------

None / list

------------------------------------------------------------
P1 Issues
------------------------------------------------------------

list

------------------------------------------------------------
P2 Backlog
------------------------------------------------------------

list

------------------------------------------------------------
Final Decision
------------------------------------------------------------

GREEN:
可以进入产品化/演示阶段

YELLOW:
核心闭环成立，但需要处理指定问题

RED:
核心科研闭环仍存在结构性断点
============================================================
```

---

# 52. 最终战略判断

**ResearchOS V2.3 不追求“功能更多”。**

这一阶段真正需要证明的是：

> **ResearchOS 能不能把科研人员已经拥有的论文、数据、实验、运行结果和研究结论，组织成一个可追溯、可验证、可继续推演的科研系统。**

因此最终评价标准不是：

```text
接入了多少开源项目
```

而是：

```text
一个真实研究问题
        ↓
真实论文
        ↓
真实证据
        ↓
真实假说
        ↓
真实实验
        ↓
真实数据
        ↓
真实运行
        ↓
真实产物
        ↓
真实结论
        ↓
下一步实验
```

**如果这一条真正跑通，ResearchOS 的核心产品逻辑就成立。**

其余能力，包括 MCP、Multi-Agent、PaperQA2 全量集成、多用户协作等，全部可以留到 V2.4+。

> **V2.3 的任务不是把 ResearchOS 做“大”，而是把 ResearchOS 做“真”。**