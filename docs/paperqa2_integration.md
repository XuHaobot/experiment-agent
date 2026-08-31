# PaperQA2 技术验证与集成评估报告

本文档对开源项目 **PaperQA2** (Future-House/paper-qa) 在 ResearchOS (Experiment Agent) 中的适用性、架构设计及集成路径进行深度技术评估。

---

## 1. PaperQA2 核心原理与能力

PaperQA2 是一款专为学术文献问答与严谨综述设计的开源 Agent 框架：
- **全文解析与分块 (Full-text Parsing & Chunking)**：解析 PDF 与 LaTeX 论文，保留公式、表格与结构化章节；
- **混合检索与重排序 (Hybrid Retrieval & Reranking)**：结合 BM25 关键词检索与 Dense Embedding 语义检索；
- **证据引用生成 (Evidence-Grounded Synthesis)**：要求 LLM 必须为每个结论生成严谨的学术引用标识与原文片段上下文，不产生幻觉；
- **问答树展开 (Tree-Search Summary)**：支持复杂科研问题的分解与多文献综合推演。

---

## 2. 技术依赖与环境要求

| 维度 | 要求与指标 | 对 Local-First ResearchOS 的影响 |
|---|---|---|
| **Python 版本** | Python >= 3.10 | 与现有环境完全兼容。 |
| **外部依赖包** | `pydantic`, `tiktoken`, `pypdf`, `pymupdf` (fitz) | 依赖相对较多，尤其是 PDF 解析与 Tokenizer。 |
| **LLM 依赖** | 高度依赖具备较长上下文和遵循指令能力的大模型 (如 Claude 3.5 Sonnet, GPT-4o, DeepSeek-V3) | 需要配置外部 API Key 或高性能本地模型。 |
| **Embedding 模型** | 需本地或远程 Embedding 模型 (如 `text-embedding-3-small`, `bge-large-en`) | 本地运行需额外加载数百 MB 向量模型。 |
| **硬件要求** | CPU: 2+ Cores, RAM: 4GB+ (纯 API 模式) / 16GB+ (本地模型模式) | 轻量 API 模式下可顺畅运行，本地量化模式需占用额外显存。 |

---

## 3. 集成评估与结论

### 是否适合作为当前强依赖？
**否 (NO)**。
- 强行引入 PaperQA2 会大幅增加安装体积与网络依赖（可能导致 `pip install` 失败），违背 Local-First 的轻量原则；
- 大多数日常科研的第一步是**检索元数据与摘要筛选**，全文深度阅读通常在科研人员保存文献后进行。

### 推荐集成方式：可选扩展服务 (Optional Architecture Adapter)
1. **接口解耦**：在 `backend/integrations/literature/qa.py` 定义 `PaperQAServiceInterface`；
2. **可选依赖加载**：通过 `try ... import paperqa` 动态探测，未安装时优雅降级为基于摘要与元数据的轻量问答；
3. **工作流衔接**：
   $$\text{Research Question} \xrightarrow{\text{Literature Search}} \text{Saved Papers (PDFs)} \xrightarrow{\text{PaperQA2 Adapter}} \text{Evidence Grounded Synthesis} \xrightarrow{} \text{Hypothesis}$$
