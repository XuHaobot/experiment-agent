# LLM API 配置说明

本文档说明如何为实验记录整理 Agent 配置 OpenAI-compatible Chat Completions API，以及如何判断系统是否启用了 LLM 增强抽取。

## 1. 配置 OpenAI-compatible API

项目不会在代码中写死 API Key。请在项目根目录创建 `.env` 文件，可以先复制 `.env.example`：

```bash
cp .env.example .env
```

Windows PowerShell 可以使用：

```powershell
Copy-Item .env.example .env
```

然后填写以下变量：

```bash
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://your-openai-compatible-endpoint/v1
LLM_MODEL=your-model-name
```

变量说明：

- `LLM_API_KEY`：API 密钥。不要提交到 Git 仓库。
- `LLM_BASE_URL`：OpenAI-compatible 服务的基础地址，不需要包含 `/chat/completions`。
- `LLM_MODEL`：模型名称，例如服务端提供的 `gpt-4o-mini`、`gpt-4.1-mini` 或其他兼容模型名。

客户端会自动把 `LLM_BASE_URL` 拼接为 Chat Completions 地址。如果你填入的地址已经以 `/chat/completions` 结尾，客户端也会兼容。

## 2. 如何判断 LLM 是否启用

启动项目：

```bash
streamlit run app.py
```

页面顶部会显示当前 LLM 配置状态：

- 如果 `.env` 中三个变量都已填写，页面会提示 LLM API 已配置。
- 如果未配置，页面会提示当前使用规则抽取结果。

完成一次分析后，页面会显示：

```text
metadata.llm_used = True 或 False
```

同时，最终 JSON 的 `metadata` 字段也会包含：

```json
{
  "llm_used": false,
  "llm_error": "LLM_CONFIG_ERROR: ..."
}
```

当 `llm_used` 为 `true` 时，说明本次分析成功拿到了 LLM 返回的可解析 JSON，并参与了结果合并。

## 3. 常见错误

### LLM_CONFIG_ERROR

含义：`LLM_API_KEY`、`LLM_BASE_URL` 或 `LLM_MODEL` 至少有一个未配置。

处理方式：

- 检查项目根目录是否存在 `.env`
- 检查变量名是否完全一致
- 检查 `LLM_MODEL` 是否为空

### LLM_API_ERROR

含义：请求 API 失败，或服务返回了 4xx / 5xx。

常见原因：

- API Key 无效
- Base URL 填错
- 模型名不被当前服务支持
- 网络不可达
- 额度不足或服务限流

处理方式：

- 确认 `LLM_BASE_URL` 不要重复包含 `/chat/completions`
- 确认模型名称与服务商文档一致
- 查看页面或 JSON 中的 `metadata.llm_error`

### LLM_RESPONSE_ERROR

含义：服务返回了响应，但不是 OpenAI-compatible Chat Completions 格式。

处理方式：

- 确认服务返回结构包含 `choices[0].message.content`
- 如果使用代理服务，确认它兼容 Chat Completions API

### JSON_PARSE_ERROR

含义：模型返回内容无法解析为 JSON。

处理方式：

- 检查 `prompts/extract_prompt.txt`
- 降低温度或换用更稳定的模型
- 确保模型输出的是 JSON object，而不是解释文本

## 4. 如何回退到规则抽取

如果希望暂时禁用 LLM，可以清空 `.env` 中的任意一个必要变量，例如：

```bash
LLM_API_KEY=
```

或者临时删除 `.env` 文件。系统不会崩溃，会自动回退到规则抽取流程。

回退后仍然可以使用：

- 命令提取
- 参数分层抽取
- 报错分析
- 解决方案提取
- Markdown 报告生成
- 历史关键词检索

此时最终 JSON 中通常会看到：

```json
{
  "llm_used": false,
  "llm_error": "LLM_CONFIG_ERROR: LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL must be configured before calling the LLM."
}
```

这表示系统已按预期使用规则抽取结果。
