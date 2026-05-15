# RAG Starter

RAG Starter 是一个基于 LangChain、FastAPI、Chroma 和 React 的本地 RAG 应用模板。它提供从文档上传、内容提取、智能分割、向量入库、知识库检索，到 Agent 对话、临时附件读取、文档生成和前端用户界面的完整链路。

项目适合用于学习 RAG 工程实践、快速搭建本地知识库问答系统，或作为二次开发的起点。

## 特性

- 多格式文档加载：支持 Markdown、TXT、PDF、Word、Excel、PPT、HTML、JSON、CSV、图片 OCR 等常见格式。
- 文档感知分割：针对 Markdown、Word、Excel 做了专门优化，减少标题、表头和正文被错误拆开的情况。
- 本地向量数据库：默认使用 Chroma 持久化到本地目录。
- 可切换 Embedding：支持阿里云百炼 DashScope 和本地 Ollama embedding。
- 文件去重：上传知识库文件时按文件 hash 拒绝重复文件，文件内 chunk 去重。
- RAG 对话：检索本地知识库后调用 LLM 生成增强回答。
- Agent 工具调用：模型可自动决定是否调用知识库检索、读取上传附件、查询天气、生成文档等工具。
- 临时对话附件：用户可在聊天输入框上传文件，Agent 可读取附件内容，但不会写入知识库。
- 文档生成：支持生成 Markdown、Word、Excel、PDF，并在前端提供下载入口。
- 前端 Web：提供状态控制台、对话、知识库管理、设置等用户端页面。
- 本地持久化：会话、消息和用户设置使用 SQLite 保存。

## 技术栈

后端：

- Python 3.11+
- FastAPI
- LangChain / LangChain Core / LangChain Chroma
- ChromaDB
- SQLite / SQLAlchemy
- DeepSeek OpenAI-compatible Chat API
- DashScope OpenAI-compatible Embedding API
- Ollama local embedding API

前端：

- Vite
- React
- TypeScript
- Tailwind CSS
- TanStack Query
- React Router
- lucide-react

## 项目结构

```text
rag-starter/
├── src/
│   ├── agent/                 # Agent 编排和工具注册
│   ├── api/                   # FastAPI 应用和接口 schema
│   ├── chat_files/            # 对话临时上传文件管理
│   ├── document_generator/    # Markdown/Word/Excel/PDF 文档生成
│   ├── embedding/             # DashScope、Ollama、Hash embedding 实现
│   ├── loader/                # 各类型文档加载器
│   ├── rag/                   # RAG 问答服务
│   ├── splitter/              # 文档分割器
│   ├── storage/               # SQLite 会话和设置持久化
│   └── vector_store/          # Chroma 向量库封装
├── tests/                     # 后端单元测试
├── web/                       # React 前端
├── .env.example               # 环境变量示例
├── pyproject.toml             # Python 项目配置
└── README.md
```

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/<your-name>/rag-starter.git
cd rag-starter
```

### 2. 创建 Python 虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell：

```powershell
.venv\Scripts\Activate.ps1
```

### 3. 安装后端依赖

基础安装：

```bash
pip install -e .
```

如果需要尽可能覆盖更多文档格式，建议安装 loader 可选依赖：

```bash
pip install -e ".[loaders]"
```

### 4. 配置环境变量

复制环境变量示例：

```bash
cp .env.example .env
```

至少需要配置一个 LLM API Key：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key
```

Embedding 可选择 DashScope 或 Ollama。本地免费方案推荐 Ollama：

```env
RAG_EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:4b
OLLAMA_EMBEDDING_DIMENSION=2560
```

如果使用 DashScope：

```env
RAG_EMBEDDING_PROVIDER=dashscope
DASHSCOPE_API_KEY=your_dashscope_api_key
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4
DASHSCOPE_EMBEDDING_DIMENSION=2048
```

### 5. 启动后端

```bash
uvicorn src.api.main:app --reload
```

默认 API 地址：`http://127.0.0.1:8000`

### 6. 启动前端

```bash
cd web
npm install
npm run dev
```

默认前端地址：`http://127.0.0.1:5173`

如需覆盖 API 地址，可在 `web/.env.local` 中配置：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## 使用 Ollama 本地 Embedding

项目支持通过 Ollama 调用本地 embedding 模型，例如 `qwen3-embedding:4b`。

确认 Ollama 服务运行：

```bash
ollama list
```

如果执行 `ollama serve` 时出现：

```text
listen tcp 127.0.0.1:11434: bind: address already in use
```

说明 Ollama 服务已经在本机运行，不需要重复启动。

如果模型尚未下载：

```bash
ollama pull qwen3-embedding:4b
```

注意：切换 embedding 模型或向量维度后，必须删除旧的 Chroma 数据并重新索引知识库，因为不同 embedding 模型的向量空间不兼容。

```bash
rm -rf storage/chroma
```

## 核心工作流

### 知识库索引

用户上传文件后，系统会执行：

```text
上传文件 -> 文档加载 -> 文档分割 -> 文件去重/chunk 去重 -> embedding -> 写入 Chroma
```

### RAG 对话

```text
用户问题 -> embedding -> Chroma 相似度检索 -> 参考段落 -> Prompt 组装 -> LLM -> 回答
```

### Agent 对话

Agent 会根据用户问题和工具描述自动判断是否调用工具：

- `search_knowledge_base`：检索本地知识库。
- `read_uploaded_document`：读取当前对话临时上传的文件。
- `generate_document`：生成 Markdown、Word、Excel、PDF 文档。
- `get_current_date`：获取当前日期。
- `get_current_location_city`：获取默认城市。
- `query_weather`：查询天气。

### 临时对话附件

聊天输入框左侧的 `+` 菜单支持添加文件，也支持拖拽文件到输入区域。临时附件只服务当前对话，不会写入知识库，也不会进入 Chroma。

```text
上传临时文件 -> 加载并分割 -> Agent 工具按需读取 -> 回答问题
```

### 文档生成

Agent 可根据用户要求生成可下载文档：

```text
用户要求生成文档 -> 模型整理内容 -> generate_document 工具 -> 保存文件 -> 前端附件卡片下载
```

支持格式：

- Markdown：`.md`
- Word：`.docx`
- Excel：`.xlsx`
- PDF：`.pdf`

## API 概览

### 系统

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/health` | 健康检查 |

### 知识库

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/documents` | 列出已入库知识库文件 |
| `POST` | `/index` | 上传文件并索引到向量库 |
| `POST` | `/documents` | 按本地路径加载并索引文件 |
| `DELETE` | `/documents` | 按 `ids`、`source_id` 或 `source` 删除向量记录 |
| `POST` | `/search` | 相似度检索 |

### 对话

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/chat` | 普通 LLM 对话 |
| `POST` | `/rag/chat` | RAG 增强对话 |
| `POST` | `/agent/chat` | Agent 智能对话 |
| `POST` | `/chat/files` | 上传对话临时附件 |
| `GET` | `/chat/sessions` | 列出会话 |
| `GET` | `/chat/sessions/{session_id}` | 获取会话详情 |
| `DELETE` | `/chat/sessions/{session_id}` | 删除会话 |

### 文档生成

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/generated-documents/{file_id}/download` | 下载 Agent 生成的文档 |

### 设置

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/settings` | 获取用户设置 |
| `PUT` | `/settings` | 更新用户设置 |

## API 示例

上传并索引知识库文件：

```bash
curl -X POST http://127.0.0.1:8000/index \
  -F "files=@docs/report.pdf" \
  -F "splitter_type=recursive" \
  -F "chunk_size=1000" \
  -F "chunk_overlap=200"
```

检索知识库：

```bash
curl -X POST http://127.0.0.1:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"项目背景","k":3}'
```

Agent 对话：

```bash
curl -X POST http://127.0.0.1:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"根据知识库总结项目背景","k":2,"history":[]}'
```

上传对话临时附件：

```bash
curl -X POST http://127.0.0.1:8000/chat/files \
  -F "file=@docs/report.pdf"
```

## 配置说明

所有运行配置集中在 [src/config.py](src/config.py)，可通过环境变量覆盖。

### 常用配置

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `RAG_API_TITLE` | `RAG Starter API` | FastAPI 标题 |
| `RAG_CORS_ORIGINS` | `http://localhost:5173,...` | 允许访问 API 的前端来源，逗号分隔 |
| `RAG_DATABASE_URL` | `sqlite:///storage/app.db` | SQLite 数据库地址 |
| `RAG_CHROMA_PERSIST_DIRECTORY` | `storage/chroma` | Chroma 持久化目录 |
| `RAG_CHROMA_COLLECTION_NAME` | `documents` | Chroma collection 名称 |
| `RAG_TOP_K` | `2` | 默认检索段落数 |
| `RAG_SPLITTER_TYPE` | `recursive` | 默认分割器 |
| `RAG_CHUNK_SIZE` | `1000` | 默认 chunk 大小 |
| `RAG_CHUNK_OVERLAP` | `200` | 默认 chunk 重叠 |

### LLM 配置

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `RAG_LLM_PROVIDER` | `deepseek` | LLM 提供方 |
| `DEEPSEEK_API_KEY` | 空 | DeepSeek API Key |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | DeepSeek OpenAI 兼容地址 |
| `DEEPSEEK_MODEL` | `deepseek-v4-pro` | 对话模型 |
| `DEEPSEEK_TEMPERATURE` | `0.2` | 生成温度 |
| `DEEPSEEK_MAX_TOKENS` | `1024` | 最大输出 token |

### Embedding 配置

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `RAG_EMBEDDING_PROVIDER` | `dashscope` | `dashscope`、`ollama` 或 `hash` |
| `DASHSCOPE_API_KEY` | 空 | DashScope API Key |
| `DASHSCOPE_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | DashScope OpenAI 兼容地址 |
| `DASHSCOPE_EMBEDDING_MODEL` | `text-embedding-v4` | DashScope embedding 模型 |
| `DASHSCOPE_EMBEDDING_DIMENSION` | `2048` | DashScope 向量维度 |
| `DASHSCOPE_EMBEDDING_BATCH_SIZE` | `10` | DashScope 单批数量 |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama 服务地址 |
| `OLLAMA_EMBEDDING_MODEL` | `qwen3-embedding:4b` | Ollama embedding 模型 |
| `OLLAMA_EMBEDDING_DIMENSION` | `2560` | Ollama 向量维度 |
| `OLLAMA_EMBEDDING_BATCH_SIZE` | `10` | Ollama 单批数量 |

### 文件目录配置

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `RAG_GENERATED_DOCUMENT_DIRECTORY` | `storage/generated_documents` | Agent 生成文档目录 |
| `RAG_CHAT_UPLOAD_DIRECTORY` | `storage/chat_uploads` | 对话临时附件目录 |
| `RAG_CHAT_UPLOAD_MAX_SIZE_MB` | `20` | 单个临时附件最大体积 |

## 支持的文档格式

已注册的文件扩展名包括：

```text
txt, log, csv, tsv, json, jsonl, ndjson, pdf, md, markdown, mdx,
html, htm, mht, mhtml, xml, doc, docx, ppt, pptx, xls, xlsx,
eml, msg, chm, epub, odt, org, rst, rtf, srt,
jpg, jpeg, png, tif, tiff, bmp, heic, ipynb, toml, yaml, yml,
以及常见源码文件
```

更多加载器和分割器说明见：

- [src/loader/README.md](src/loader/README.md)
- [src/splitter/README.md](src/splitter/README.md)

## 前端页面

前端位于 [web](web)，当前包含：

- 状态：系统控制台，展示知识库、会话、系统链路等状态。
- 对话：Agent 对话页，支持上下文记忆、临时附件上传、文档生成下载、Markdown 渲染。
- 知识库：文件列表、上传、查询、删除，并提供按文件类型和 chunk 规模生成的立体知识库空间视图，点击文件块可快速限定查询范围。
- 设置：RAG 参考段落显示开关、聊天背景个性化配置。

## 测试

后端测试：

```bash
PYTHONPATH=. python -m unittest discover -s tests
```

前端测试：

```bash
cd web
npm test
```

前端构建：

```bash
cd web
npm run build
```

## 数据与安全

- `.env` 包含密钥，已被 `.gitignore` 忽略，不要提交真实 API Key。
- `storage/` 保存本地数据库、向量库、临时上传文件和生成文档，默认不应提交到仓库。
- 更换 embedding 模型后，请删除旧向量库并重新索引。
- 对话临时附件不会自动进入知识库。
- 生成文档接口仅返回本地生成文件下载地址。

## Roadmap

- 支持更多 LLM provider。
- 支持临时附件的会话级生命周期清理。
- 支持更多文档生成模板。
- 支持 Docker Compose 一键启动。
- 支持可配置的 Agent 工具开关和权限控制。
- 增加端到端测试。

## Contributing

欢迎提交 issue 和 pull request。建议在提交前运行：

```bash
PYTHONPATH=. python -m unittest discover -s tests
cd web && npm test && npm run build
```

## License

本项目尚未声明开源许可证。正式发布到 GitHub 前，建议添加 `LICENSE` 文件，例如 MIT、Apache-2.0 或其他符合你预期的许可证。
