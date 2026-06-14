# 基于 Agent 与实验知识图谱的实验记录整理与调参复盘助手

> 一个面向科研/工程实验场景的本地化 AI 复盘工具。**FastAPI + Vue3 + ChromaDB + Function Calling Agent** 全栈实现，支持混合检索、多轮对话记忆、SSE 流式输出、知识图谱可视化。

![GitHub](https://img.shields.io/badge/Python-3.10%2B-blue)
![GitHub](https://img.shields.io/badge/Vue-3.x-green)
![GitHub](https://img.shields.io/badge/FastAPI-0.110%2B-teal)
![GitHub](https://img.shields.io/badge/License-MIT-yellow)

---

## 一、项目背景

实验过程中，训练命令、参数配置、报错信息、调参过程和最终解决方案经常散落在 GPT 聊天记录、终端日志、临时笔记中。时间一长，很难复盘：

- 当时用了什么参数？
- 这次为什么报错？
- 最后怎么解决？
- 下一步打算试什么？

本项目把这些零散信息沉淀成**可检索、可复盘、可扩展**的实验记忆，并通过 AI Agent + RAG + 知识图谱的组合，让你可以像和一位"研究助理"对话一样做实验复盘。

---

## 二、核心能力一览

| 能力模块 | 关键技术 | 效果 |
|----------|---------|------|
| **Function Calling Agent** | OpenAI Tools 协议 + 6 工具 | LLM 自主决定调用哪些工具，支持链式调用（最多 5 轮） |
| **RAG 混合检索** | ChromaDB + 关键词双路 | 关键词 40% + 语义 60% 加权融合，召回率显著高于单一检索 |
| **向量语义搜索** | DashScope text-embedding-v2 (1536 维) | 容忍同义改写（如"训练失败" ≈ "OOM 报错"） |
| **多轮对话记忆** | MemoryManager + 上下文窗口 20 轮 | 跨会话保留实验上下文，支持最多 100 个独立会话 |
| **SSE 流式输出** | FastAPI StreamingResponse | 逐 token 推送，前端真实打字机效果，非前端模拟 |
| **知识图谱** | 9 类实体 + 11 类关系 + D3.js 可视化 | 结构化沉淀"实验-命令-参数-报错-方案"链路 |
| **多模态输入** | txt / md / json 上传 | 自动解析实验聊天记录 / 终端日志 |
| **LLM 增强抽取** | OpenAI-compatible API + 规则回退 | 无 Key 也能用规则抽取，配置 LLM 后效果更好 |

---

## 三、效果展示

### 1. 智能问答：直接给出实验报错归因

> 用户提问：以下是大数据处理技术实验中记录到的所有报错

Agent 自动调用 `search_records` + `analyze_data`，输出结构化归因：

| 错误类型 | 报错摘要 | 根因 | 建议解决方案 |
|---------|---------|------|-------------|
| Docker 镜像拉取失败 | `docker.io/library/ubuntu:22.04` 解析超时 | 网络问题，Docker 无法连接 Docker Hub（registry-1.docker.io:443） | 检查网络代理或更换镜像源 |
| service ssh start 启动失败 | 容器内 SSH 服务无法启动 | 容器默认没有安装 systemd，无法使用 systemctl | 改用 `/usr/sbin/sshd &` 后台启动 |
| JAVA_HOME 未设置 | `ERROR: JAVA_HOME is not set and could not be found` | 环境变量缺失 | 终端执行 `export JAVA_HOME=/usr/lib/jvm/...` |
| HDFS 写入失败 | `could only be replicated to 0 nodes` | DataNode 未启动 / 副本数 > 节点数 | 重新格式化 HDFS 或调整 `dfs.replication` |

> ⬆️ 真实运行结果（基于 Hadoop 3.3.5 + HBase 2.4.17 实验）
<img width="1608" height="930" alt="c128128cb305b3e3886ec70c1cb03bdc" src="https://github.com/user-attachments/assets/b467509f-aa4a-4273-80b1-00ce7860afdc" />

### 2. 复盘报告：自动生成 Markdown 实验复盘文档

针对每条实验记录，Agent 调用 `generate_report` 工具自动生成结构化复盘报告：

```markdown
# 实验复盘报告

## 1. 实验概述
- 实验任务：大数据处理技术实验（Hadoop 安装、HDFS 操作、Java 文件合并...）
- 数据集：HDFS 测试文件（fileA.txt, fileB.txt）
- 模型 / 框架：Hadoop 3.3.5, HBase 2.4.17

## 2. 原始运行配置
- 拉取 Ubuntu 22.04 镜像：bash
- 交互界面：bash

## 3. 报错记录
- Docker 拉取失败
- ssh 服务启动失败
- JAVA_HOME 未设置
...

## 4. 解决方案
- 配置 /etc/hosts 加速 Docker Hub
- 用 nohup /usr/sbin/sshd -D & 后台启动
- 写入 ~/.bashrc 持久化 JAVA_HOME

## 5. 调参建议
- hadoop.tmp.dir 改为 /data/tmp
- dfs.replication 从 3 降到 2 适应单节点
```

> ⬆️ 报告按时间顺序组织，结构清晰，可直接贴入实验周报
    <img width="1616" height="941" alt="49d841dc05557a3f59b02ce2cfaa11c1" src="https://github.com/user-attachments/assets/63a249de-2c90-400a-bf35-cad1e9f93487" />
### 3. 知识图谱：可视化"实验-命令-参数-报错-方案"全链路


图谱自动从结构化记录中抽取：

- **22 个实体**（Experiment / Dataset / Model / Command / Parameter / Error / Solution / Conclusion / NextStep 共 9 类）
- **18 条关系**（USES_DATASET / RUNS_COMMAND / HAS_ERROR / SOLVED_BY / ADJUSTS_PARAMETER / PRODUCES_CONCLUSION 等 11 类）

点击任意节点查看实体详情，支持关键词搜索、图例筛选、关系定位。

> ⬆️ 真实运行结果（基于 graph-20260614-151321-247151.json）
<img width="1606" height="929" alt="152adaab4cce0d05f8f64d3f3eb22416" src="https://github.com/user-attachments/assets/e323ff10-cce5-4e0c-8ab6-cc2f00d7073a" />

---

## 四、系统架构

```mermaid
graph TB
    subgraph Frontend["前端 · Vue 3 + D3.js"]
        UI["WorkspaceMain.vue<br/>三栏布局"]
        ChatPanel["AI 对话面板<br/>SSE 流式渲染"]
        GraphView["知识图谱可视化<br/>D3 力导向图"]
        DetailModal["实验详情弹窗<br/>锚点导航 + 搜索"]
    end

    subgraph Backend["后端 · FastAPI"]
        API["REST + SSE API"]
        AgentV2["AgentV2<br/>Function Calling<br/>max_iterations=5"]
        Memory["MemoryManager<br/>会话上下文窗口 20 轮"]
    end

    subgraph Tools["Agent 工具集（6 个）"]
        T1["search_records<br/>混合检索"]
        T2["search_graph<br/>图谱查询"]
        T3["analyze_data<br/>参数对比/趋势/摘要"]
        T4["generate_report<br/>Markdown 复盘报告"]
        T5["list_records<br/>记录列表"]
        T6["evaluate_answer<br/>LLM-as-Judge 评分"]
    end

    subgraph Storage["数据存储"]
        Records["JSON 实验记录<br/>data/records/"]
        Reports["Markdown 报告<br/>data/reports/"]
        Graph["知识图谱<br/>data/graph/"]
        MemDB["对话记忆<br/>内存 + 上下文窗口"]
    end

    subgraph Search["混合检索引擎"]
        KW["关键词搜索<br/>字段匹配 + 别名扩展"]
        SEM["语义搜索<br/>ChromaDB + DashScope"]
        HYB["Hybrid Search<br/>关键词 40% + 语义 60%"]
    end

    subgraph LLM["LLM 服务"]
        LLM_API["OpenAI-compatible API<br/>Chat Completions"]
        Stream["SSE 流式输出<br/>stream=true"]
        Embed["文本向量化<br/>text-embedding-v2"]
    end

    UI --> API
    ChatPanel -->|"POST /api/chat/stream<br/>SSE"| API
    API --> AgentV2
    AgentV2 --> T1 & T2 & T3 & T4 & T5 & T6
    AgentV2 -->|"tool_calls"| LLM_API
    AgentV2 --> Memory

    T1 --> HYB
    HYB --> KW & SEM
    KW --> Records
    SEM --> Embed --> LLM_API
    T2 --> Graph
    T4 --> Records --> Reports

    Records & Reports & Graph --> Storage
    Memory --> MemDB
    LLM_API --> Stream -->|"逐 token"| ChatPanel

    GraphView -->|"GET /api/graph/:id"| Graph
    DetailModal -->|"锚点跳转 + 高亮搜索"| UI
```

---

## 五、Agent 工具集设计

| 工具名 | 功能 | 适用场景 |
|--------|------|---------|
| `search_records` | 关键词 + 语义混合检索实验记录 | "查找所有 OOM 报错" |
| `search_graph` | 在知识图谱中按实体/关系搜索 | "哪些参数被调整过" |
| `analyze_data` | 参数对比 / 趋势 / 摘要 | "对比三次实验的 batch_size" |
| `generate_report` | 生成 Markdown 复盘报告 | "生成本次实验报告" |
| `list_records` | 列出全部实验记录 | "我之前做过哪些实验" |
| `evaluate_answer` | LLM-as-Judge 评估回答质量 | 内部评测，未暴露给用户 |

工具集使用 **OpenAI Function Calling 协议**定义，LLM 自主决定调用顺序。例如：

> 用户问：「生成 Hadoop 这次实验的报告」
>
> Agent 决策链：`list_records` → 找到 hadoop 记录 → `search_records` 获取详情 → `generate_report` 生成 Markdown → 流式输出

---

## 六、混合检索引擎

为解决"单一关键词检索召回率低"和"单一语义检索对专业术语不稳定"的问题，项目实现双路加权融合：

```python
hybrid_score = 0.4 × keyword_score + 0.6 × semantic_score
```

- **关键词路**：字段匹配 + 同义词别名扩展 + BM25-like 打分
- **语义路**：ChromaDB + DashScope text-embedding-v2 (1536 维) + 余弦相似度
- **降级策略**：ChromaDB 不可用时静默降级为纯关键词检索，不影响主流程

---

## 七、对话记忆系统

支持最多 100 个独立会话，每个会话维护：

- **20 轮**上下文窗口（可配置）
- **OpenAI 格式**消息历史
- **会话隔离**：不同实验、不同主题的对话互不干扰
- **持久化**：基于文件存储（生产环境可升级为 Redis / SQLite）

```python
from src.memory import get_memory_manager
mm = get_memory_manager()
session = mm.get_or_create_session("hadoop_exp_001")
session.add_user("对比 batch=16 和 batch=8 的训练效果")
session.add_assistant("...")
```

---

## 八、目录结构

```text
experiment-agent/
├── app.py                      # Streamlit 旧入口（保留）
├── backend/
│   └── main.py                 # FastAPI 主入口，20+ API 端点
├── frontend/                   # Vue 3 + Vite 前端
│   ├── src/views/ChatView.vue  # AI 对话主界面（SSE 流式）
│   ├── src/components/
│   │   ├── AgentTrace.vue      # 工具调用轨迹
│   │   ├── KnowledgeGraph.vue  # D3.js 图谱可视化
│   │   └── TheSidebar.vue      # 会话列表侧边栏
│   └── vite.config.js
├── src/
│   ├── agent.py                # v1 关键词路由 Agent
│   ├── agent_v2.py             # v2 Function Calling Agent（5 工具 + 流式）
│   ├── memory.py               # 对话记忆系统
│   ├── vector_store.py         # ChromaDB + DashScope Embedding
│   ├── llm_client.py           # OpenAI-compatible 客户端
│   ├── tools/                  # 6 个 Agent 工具
│   └── graph/                  # 知识图谱（builder / query / visualize）
├── data/                       # 运行期生成（已加入 .gitignore）
│   ├── records/                # JSON 实验记录
│   ├── reports/                # Markdown 复盘报告
│   ├── graph/                  # 知识图谱 JSON
│   └── chroma/                 # 向量数据库持久化
├── examples/
│   └── sample_chat.txt
├── prompts/
│   ├── extract_prompt.txt
│   └── summary_prompt.txt
├── docs/
│   └── llm_config.md
├── screenshots/                # 效果截图
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 九、快速开始

### 方式一：FastAPI + Vue3（推荐）

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 安装前端依赖
cd frontend && npm install && cd ..

# 3. 配置 LLM（可选，不配也能用规则抽取）
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY / DASHSCOPE_API_KEY

# 4. 启动后端（端口 8000）
python -m uvicorn backend.main:app --reload --port 8000

# 5. 启动前端（端口 5173）
cd frontend && npm run dev

# 6. 浏览器打开 http://localhost:5173
```

### 方式二：Streamlit 单文件（轻量模式）

```bash
streamlit run app.py
```

---

## 十、LLM 配置

支持任意 **OpenAI-compatible** 端点（OpenAI / DeepSeek / 通义千问 / 自部署 vLLM 等）。复制 `.env.example` 为 `.env`：

```bash
# 主 LLM（用于工具调用 + 生成回答）
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://your-openai-compatible-endpoint/v1
LLM_MODEL=your-model-name

# DashScope Embedding（可选，仅用于向量语义检索）
DASHSCOPE_API_KEY=your-dashscope-key
```

详细配置、启用判断、常见错误和回退方式见 [docs/llm_config.md](docs/llm_config.md)。

> 不配 LLM 也能用：项目会自动使用规则抽取结果，在页面中显示 `metadata.llm_used = False`。

---

## 十一、API 端点速览

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/analyze` | POST | 上传文件做结构化分析 |
| `/api/analyze/text` | POST | 纯文本分析 |
| `/api/records` | GET | 获取实验记录列表 |
| `/api/records/{id}` | GET / DELETE | 单条记录详情 / 删除 |
| `/api/search` | GET | 混合检索（关键词 + 语义） |
| `/api/ask` | POST | RAG 问答（旧版） |
| `/api/chat` | POST | AgentV2 对话（非流式） |
| `/api/chat/stream` | POST | **AgentV2 流式 SSE 对话** ⭐ |
| `/api/sessions` | GET / POST / DELETE | 会话管理 |
| `/api/vector-store/stats` | GET | 向量库状态 |
| `/api/vector-store/rebuild` | POST | 重建向量索引 |
| `/api/experiments` | GET / POST / DELETE | 实验管理 |
| `/api/graph` | GET | 知识图谱列表 |
| `/api/graph/{id}` | GET | 单条图谱详情 |

---

## 十二、技术栈

**后端**：Python 3.10+ / FastAPI / Uvicorn / ChromaDB / DashScope SDK / python-dotenv
**前端**：Vue 3 / Vite / Vue Router / marked.js / D3.js
**LLM**：OpenAI Function Calling 协议（兼容 DeepSeek / 通义千问 / GPT / 自部署）
**Embedding**：DashScope text-embedding-v2 (1536 维)
**存储**：本地 JSON / ChromaDB SQLite 后端 / 内存对话池

---

## 十三、Roadmap

- [x] Function Calling Agent（6 工具）
- [x] ChromaDB 向量语义检索
- [x] 多轮对话记忆
- [x] SSE 流式输出
- [x] 知识图谱（9 实体 + 11 关系）
- [x] LLM-as-Judge 内部评测
- [ ] Neo4j 替换 JSON 图谱存储
- [ ] 多文件批量分析
- [ ] 实验时间线视图
- [ ] 报错知识库（FAQ 沉淀）
- [ ] 评测集自动化回归

---

## 十四、安全提示

- `.env` 已在 `.gitignore` 中，**请勿**将 API Key 硬编码到代码或提交到 Git
- 公开仓库请使用 `.env.example` 引导他人配置
- 如发现 Key 泄露，**立即**前往对应平台（OpenAI / DashScope / DeepSeek）撤销并重新生成

---

## 十五、License

MIT
