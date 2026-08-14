# 上线部署指南（公网展示 · 用自己的 Key）

## 0. 配置逻辑（核心）

本项目采用 **「服务器默认 Key + 访客可选 BYOK」** 双轨：

- **服务器环境变量**里放你自己的 `LLM_API_KEY` / `DASHSCOPE_API_KEY` → 访客打开站点**直接能用**，不用填任何东西。
- 前端的 **⚙ 模型设置**面板仍保留，访客如果想用自己的 Key（省你的额度 / 用别的模型）可填了覆盖。
- 只配 `LLM_API_KEY`：对话可用，**语义检索降级为关键词**（不报错）。
- 再加 `DASHSCOPE_API_KEY`：语义检索默认在线（推荐，求职展示最完整）。

> 安全：访客的 BYOK Key 只在单次请求内存活，不落盘、不打日志、不回显。

---

## 0.1 公网只读模式（推荐给求职展示站）

直接公网开放会带来两个风险：**陌生人传脏数据污染你的记录库**，以及**多访客会话互相串台/被挤掉**。
本项目内置 `DEMO_READONLY` 开关，一键把站点变成「只读展示」：

| 行为 | 关闭（默认） | 开启 `DEMO_READONLY=true` |
|---|---|---|
| 对话 / 语义检索 | ✅ | ✅（用你的种子记录） |
| 访客上传 / 新建实验 / 删除记录 / 重建索引 | ✅ | ❌ 返回 403 |
| 会话隔离 | 全局共享 | 按浏览器匿名租户隔离，互不串台、互不挤压 |
| 适合场景 | 本地自用 / 可信环境 | 公网求职展示 |

**多用户隔离原理**：每个浏览器首次访问生成一个匿名 `tenant_id`（仅 UUID，无个人信息），
随请求发送；服务端会话列表/历史/删除都按 `tenant_id` 限定，淘汰也只清理同租户最旧的会话。
因此 A 访客看不到 B 访客的对话，且不会因为别人会话多而把自己的历史挤掉。

**配置方式**：在 `.env` 里加一行 `DEMO_READONLY=true`（模板见 `.env.server.example`），
CloudBase 则在环境变量里加同名键值。无需改代码。

> 隐私取舍：只读模式下访客的对话仍会按租户短暂落在服务器（便于回来继续聊）。
> 若希望「完全不存访客对话」，后续可改为前端 localStorage 全本地态——当前方案已足够安全且 UX 更好。

---

## 1. 通用：构建镜像

```bash
# 在项目根目录（含 Dockerfile）
docker build -t experiment-agent:latest .
```

镜像内已包含前端构建产物 + 后端代码 + 4 条种子实验记录。
密钥**不打入镜像**，运行时通过环境变量注入。

---

## 2. 方案 A：轻量应用服务器（¥60–100/年，简历最硬核）

适合：想证明"自己买服务器、自己部署、自己运维"，面试官印象分最高。

### 步骤
1. 在腾讯云/阿里云买一台轻量应用服务器（2C2G 够用），系统选 Ubuntu 22.04。
2. 服务器装 Docker + Docker Compose：
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER   # 重登后生效
   ```
3. 把整个项目 `git clone` 到服务器，或 `scp` 过去。
4. 复制配置模板并填 Key：
   ```bash
   cp .env.server.example .env
   vim .env          # 填入你的 LLM_API_KEY / DASHSCOPE_API_KEY
   ```
5. 启动：
   ```bash
   docker compose up -d --build
   ```
6. 验证：`curl http://localhost:5001/api/health` 应返回 `llm_configured: true`。
7. 浏览器访问 `http://<服务器公网IP>:5001`。

### 进阶（可选）
- **绑域名 + HTTPS**：在轻量服务器控制台配域名解析 → 用 Nginx/Caddy 反代 5001 并申请证书。国内域名需 **ICP 备案**（约 1–2 周）。
- **防火墙**：只放行 80/443/22，5001 不建议直暴露公网，走反代更安全。

---

## 3. 方案 B：腾讯云 CloudBase CloudRun（几乎免运维，自带公网域名）

适合：不想管服务器、国内访问快、免费额度够展示。

### 步骤
1. 打开 CloudBase 控制台 → 云托管（CloudRun）→ 新建服务，选择**从代码仓库 / 本地镜像**部署，运行时选 **Docker**。
2. 上传本项目（含 Dockerfile），构建命令 `docker build -t experiment-agent .`。
3. 在 CloudBase 控制台的**环境变量**里填入：
   - `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`
   - `DASHSCOPE_API_KEY`
   - `AUTO_REBUILD_VECTORS=true`
   - `PYTHONPATH=/app`（Dockerfile 已设，确认即可）
4. 端口填 `5001`（与 Dockerfile EXPOSE 一致）。
5. 部署完成后，CloudBase 分配 `*.ap-shanghai.app.tcloudbase.com` 公网域名，直接可访问。

> ⚠️ 注意：CloudBase 国内环境调用 **OpenAI / Claude** 大概率被网络限制；用 **DeepSeek / 通义 / 文心** 等国内模型无此问题。这也是推荐配 DashScope 做 embedding 的原因。

---

## 4. 首次上线必做检查

| 检查项 | 方法 | 期望 |
|---|---|---|
| 服务存活 | `GET /api/health` | `status: ok` |
| 对话可用 | 打开站点发一条消息 | 正常回复（用你的 Key） |
| 语义检索在线 | 状态条显示「语义检索：已绑定…」| 非降级模式 |
| 向量索引已建 | 启动时日志含 `vector index ready` | 语义搜索有结果 |
| 种子数据可见 | 站点能检索到 4 条实验记录 | 访客无需上传即可对话 |

如语义检索无结果：手动触发一次重建
```bash
curl -X POST http://<host>:5001/api/vector-store/rebuild
```

---

## 5. 成本与风险

- **算力**：容器常驻，轻量服务器按年付很便宜；CloudBase 按量，展示流量基本免费额度内。
- **Token**：访客直接烧你的 `LLM_API_KEY`。求职展示流量小，可接受；若担心被刷，可：
  - 在站点加简单访问口令（后续可加）；
  - 或引导访客用 ⚙ 面板填自己的 Key（BYOK）。
- **数据**：`/app/data` 已挂持久化卷（compose）或 CloudBase 持久化目录，重启不丢记录/索引。

---

## 6. 目录与文件说明（本次新增）

| 文件 | 作用 |
|---|---|
| `Dockerfile` | 多阶段构建：node 打前端 + python 跑后端，单容器同源服务 |
| `.dockerignore` | 排除密钥/缓存/可变数据，不进镜像 |
| `entrypoint.sh` | 首启初始化种子数据 + 自动建向量索引 + 启 uvicorn |
| `docker-compose.yml` | 轻量服务器一键起（含数据卷） |
| `.env.server.example` | 服务器侧 Key 模板（无密钥，可提交） |
| `DEPLOY.md` | 本文档 |
