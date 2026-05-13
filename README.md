# RAG Starter

本项目提供一组基于 LangChain 的本地文档加载器、文档分割器、本地向量数据库封装和 FastAPI 接口。加载器位于 `src/loader`，按文档类型拆分为独立 Python 模块；分割器位于 `src/splitter`，提供统一的 chunk 切分入口；向量库位于 `src/vector_store`，默认使用本地持久化 Chroma。

## 安装

基础依赖：

```bash
pip install langchain-community langchain-core
pip install langchain-text-splitters
pip install langchain-chroma chromadb fastapi uvicorn python-multipart
pip install langchain-openai
```

不同格式会需要额外依赖。建议在需要覆盖办公文档、图片 OCR、EPUB 等格式时安装：

```bash
pip install "unstructured[all-docs]" pypdf beautifulsoup4 jq openpyxl xlrd python-docx python-pptx nbformat pillow pytesseract pysrt
```

## 统一配置

项目运行默认值集中在 [src/config.py](src/config.py)，API、分割器、embedding 和本地 Chroma 向量库都从这里读取默认配置。需要覆盖默认值时，可以通过环境变量配置：

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `RAG_API_TITLE` | `RAG Starter API` | FastAPI 标题 |
| `RAG_API_VERSION` | `0.1.0` | FastAPI 版本 |
| `RAG_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174` | 允许访问 API 的前端来源，逗号分隔 |
| `RAG_SPLITTER_TYPE` | `recursive` | 默认分割器 |
| `RAG_CHUNK_SIZE` | `1000` | 默认 chunk 大小 |
| `RAG_CHUNK_OVERLAP` | `200` | 默认 chunk 重叠长度 |
| `RAG_EMBEDDING_PROVIDER` | `dashscope` | 默认 embedding 提供方 |
| `DASHSCOPE_API_KEY` | 空 | 阿里云百炼 API Key，写入向量库和检索时必填 |
| `DASHSCOPE_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | 百炼 OpenAI 兼容接口地址 |
| `DASHSCOPE_EMBEDDING_MODEL` | `text-embedding-v4` | 默认 embedding 模型 |
| `DASHSCOPE_EMBEDDING_DIMENSION` | `2048` | `text-embedding-v4` 输出维度 |
| `DASHSCOPE_EMBEDDING_BATCH_SIZE` | `10` | 单次 embedding 请求文本数量，百炼要求不超过 10 |
| `DASHSCOPE_EMBEDDING_TIMEOUT_SECONDS` | `60.0` | embedding 请求超时时间 |
| `RAG_CHROMA_PERSIST_DIRECTORY` | `storage/chroma` | Chroma 持久化目录 |
| `RAG_CHROMA_COLLECTION_NAME` | `documents` | Chroma collection 名称 |
| `RAG_TOP_K` | `2` | RAG 对话默认检索段落数 |
| `RAG_SYSTEM_PROMPT` | 知识库问答助手提示词 | RAG 对话默认 system prompt |
| `RAG_LLM_PROVIDER` | `deepseek` | 默认 LLM 提供方 |
| `DEEPSEEK_API_KEY` | 空 | DeepSeek API Key，调用 `/rag/chat` 时必填 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | DeepSeek OpenAI 兼容接口地址 |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | DeepSeek 对话模型 |
| `DEEPSEEK_TEMPERATURE` | `0.2` | 生成温度 |
| `DEEPSEEK_MAX_TOKENS` | `1024` | 单次回答最大 token 数 |
| `DEEPSEEK_TIMEOUT_SECONDS` | `60.0` | LLM 请求超时时间 |

本地开发可以在项目根目录创建 `.env`，项目启动时会自动读取：

```bash
DEEPSEEK_API_KEY="sk-..."
DASHSCOPE_API_KEY="sk-..."
```

`.env` 已加入 `.gitignore`，不要把真实 API Key 提交到远程仓库。

## 快速使用

```python
from src.loader import load_documents, get_loader, supported_extensions

docs = load_documents("docs/report.pdf")
loader = get_loader("docs/table.csv")
print(supported_extensions())
```

按目录加载：

```python
from src.loader.directory import load_directory

docs = load_directory("docs", recursive=True)
```

文档分割：

```python
from src.loader import load_documents
from src.splitter import split_documents

docs = load_documents("docs/report.pdf")
chunks = split_documents(
    docs,
    chunk_size=1000,
    chunk_overlap=200,
)
```

加载并分割：

```python
from src.splitter import load_and_split_documents

chunks = load_and_split_documents("docs/report.pdf")
```

Markdown 文件在 `load_and_split_documents()` 中会优先按标题层级聚合，再做 recursive 二次切分，避免标题和正文落入不同 chunk。切分后的 metadata 会保留 `h1`、`h2` 等标题层级，提升 RAG 检索上下文完整性。

Word 文件在 `load_and_split_documents()` 中会使用标题感知切分：`.docx` 通过 `python-docx` 读取标题样式，`.doc` 通过 Unstructured elements 的标题元数据聚合章节。每个 section 会保留标题层级和正文，recursive 二次切分后也会给子 chunk 补回标题上下文，避免 RAG 检索命中正文时缺少所属章节信息。

Excel 文件在 `load_and_split_documents()` 中会使用表格感知切分：按工作表读取 `.xls`、`.xlsx`，自动识别表头，把文件名、工作表名、表头和完整数据行一起写入 chunk。这样可以避免通用文本切分把表头和单元格内容拆开，导致 RAG 检索命中某一行时缺少列名语义。`.xlsx` 依赖 `openpyxl`，`.xls` 依赖 `xlrd`。

完整索引链路：

```python
from src.vector_store import VectorStoreService

service = VectorStoreService()
result = service.index_file("docs/report.pdf", source_label="report.pdf")
print(result.ids, result.skipped_duplicates)
results = service.search("项目背景", k=3)
```

默认 embedding 使用阿里云百炼 `text-embedding-v4`，通过 LangChain `OpenAIEmbeddings` 连接百炼 OpenAI 兼容接口，默认输出 2048 维向量。切换 embedding 模型或维度后，需要删除旧的 Chroma 数据并重新索引知识库，因为同一个 Chroma collection 不能混用不同维度的向量。

RAG 增强对话链路：

```python
from src.rag import RagService

service = RagService()
result = service.answer("项目背景是什么？", k=3)
print(result.answer)
print(result.references)
```

流程为：用户问题 -> LangChain embedding -> LangChain Chroma 相似度检索 -> 返回 top-k 知识库段落 -> 将用户问题和参考段落整合为最终 prompt -> LangChain ChatOpenAI 兼容方式调用 DeepSeek LLM -> 返回自然回答、prompt 和引用段落。

索引入库前会执行文件内 chunk 去重：同一个文件切出的重复 chunk 只写入一次；不同文件里的相同 chunk 会分别保留，方便后续删除某个上传文件时只删除该文件对应的数据。

上传索引会先计算文件内容 SHA-256，并检查向量库 metadata 中是否已存在相同 `file_hash`。重复文件不会入库，接口返回 `409`，响应体中包含 `message`、`filename` 和 `file_hash`。

写入本地向量库：

```python
from src.vector_store import VectorStoreService

service = VectorStoreService()
ids = service.add_file("docs/report.pdf")
results = service.search("检索问题", k=3)
service.delete(ids=ids)
```

启动 FastAPI：

```bash
uvicorn src.api.main:app --reload
```

接口：

- `GET /health`: 健康检查
- `GET /documents`: 按文件维度列出已入库知识库文件和 chunk 数量
- `POST /index`: 上传文件，执行提取、分割并写入向量库
- `POST /documents`: 加载、分割并写入本地向量库
- `DELETE /documents`: 按 `ids`、`source_id` 或 `source` 删除向量库记录
- `POST /search`: 相似度检索
- `POST /rag/chat`: RAG 增强对话，基于本地知识库检索结果调用 DeepSeek

`POST /index` 会返回每个文件的 `filename`、`source_id`、`ids`、写入 chunk 数量、输入 chunk 数量和跳过的重复 chunk 数量，方便后续追踪、删除和观察去重效果。若上传重复文件，会返回类似：

```json
{
  "detail": {
    "message": "文件 report.pdf 已存在，不允许重复上传",
    "filename": "report.pdf",
    "file_hash": "..."
  }
}
```

示例：

```bash
curl -X POST http://127.0.0.1:8000/index \
  -F "files=@docs/report.pdf" \
  -F "files=@docs/notes.txt" \
  -F "splitter_type=recursive" \
  -F "chunk_size=1000" \
  -F "chunk_overlap=200"

curl http://127.0.0.1:8000/documents

curl -X POST http://127.0.0.1:8000/documents \
  -H "Content-Type: application/json" \
  -d '{"path":"docs/report.pdf","chunk_size":1000,"chunk_overlap":200}'

curl -X POST http://127.0.0.1:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"项目背景","k":3}'

export DEEPSEEK_API_KEY="sk-..."

curl -X POST http://127.0.0.1:8000/rag/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"项目背景是什么？","k":3}'
```

`POST /rag/chat` 响应包含 `answer`、`question`、实际发送给 LLM 的 `prompt`、`references`、`model` 和 `usage`。如果没有配置 `DEEPSEEK_API_KEY`，接口会返回 `500` 并提示设置环境变量。

## 前端 Web

前端位于 [web](web)，技术栈为 Vite、React、TypeScript、Tailwind CSS、shadcn/ui 风格组件、TanStack Query 和 React Router。

启动后端：

```bash
uvicorn src.api.main:app --reload
```

启动前端：

```bash
cd web
npm install
npm run dev
```

默认前端地址为 `http://127.0.0.1:5173`。默认 API 地址为 `http://127.0.0.1:8000`，可通过 `web/.env.local` 覆盖：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

当前页面包含：

- 知识库：用户端知识库管理页，主页面展示文件列表；上传文件和查询知识库通过按钮弹出表单完成；上传支持拖拽和点击选择，可批量上传；查询结果在查询弹窗内展示；按文件操作优先使用 `source_id`
- 状态：检查 FastAPI `/health`
- 索引：上传文件并调用 `POST /index`
- 检索：调用 `POST /search`
- RAG 对话：调用 `POST /rag/chat`
- 删除：调用 `DELETE /documents`

## 支持格式

当前按本地文件扩展名注册了以下类型：

`txt`, `log`, `csv`, `tsv`, `json`, `jsonl`, `ndjson`, `pdf`, `md`, `markdown`, `mdx`, `html`, `htm`, `mht`, `mhtml`, `xml`, `doc`, `docx`, `ppt`, `pptx`, `xls`, `xlsx`, `eml`, `msg`, `chm`, `epub`, `odt`, `org`, `rst`, `rtf`, `srt`, `jpg`, `jpeg`, `png`, `tif`, `tiff`, `bmp`, `heic`, `ipynb`, `toml`, `yaml`, `yml`，以及常见源码文件。

更多说明见 [src/loader/README.md](src/loader/README.md) 和 [src/splitter/README.md](src/splitter/README.md)。

## 测试

测试使用 Python 标准库 `unittest`，不依赖真实 LangChain 安装即可验证注册表、懒导入逻辑和 splitter 封装：

```bash
PYTHONPATH=. python -m unittest discover -s tests
```
