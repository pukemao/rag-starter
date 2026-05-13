# RAG Starter

本项目提供一组基于 LangChain 的本地文档加载器、文档分割器、本地向量数据库封装和 FastAPI 接口。加载器位于 `src/loader`，按文档类型拆分为独立 Python 模块；分割器位于 `src/splitter`，提供统一的 chunk 切分入口；向量库位于 `src/vector_store`，默认使用本地持久化 Chroma。

## 安装

基础依赖：

```bash
pip install langchain-community langchain-core
pip install langchain-text-splitters
pip install langchain-chroma chromadb fastapi uvicorn python-multipart
```

不同格式会需要额外依赖。建议在需要覆盖办公文档、图片 OCR、EPUB 等格式时安装：

```bash
pip install "unstructured[all-docs]" pypdf beautifulsoup4 jq openpyxl python-docx python-pptx nbformat pillow pytesseract pysrt
```

## 统一配置

项目运行默认值集中在 [src/config.py](src/config.py)，API、分割器、embedding 和本地 Chroma 向量库都从这里读取默认配置。需要覆盖默认值时，可以通过环境变量配置：

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `RAG_API_TITLE` | `RAG Starter API` | FastAPI 标题 |
| `RAG_API_VERSION` | `0.1.0` | FastAPI 版本 |
| `RAG_SPLITTER_TYPE` | `recursive` | 默认分割器 |
| `RAG_CHUNK_SIZE` | `1000` | 默认 chunk 大小 |
| `RAG_CHUNK_OVERLAP` | `200` | 默认 chunk 重叠长度 |
| `RAG_EMBEDDING_DIMENSION` | `384` | 本地 Hash embedding 维度 |
| `RAG_CHROMA_PERSIST_DIRECTORY` | `storage/chroma` | Chroma 持久化目录 |
| `RAG_CHROMA_COLLECTION_NAME` | `documents` | Chroma collection 名称 |

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

完整索引链路：

```python
from src.vector_store import VectorStoreService

service = VectorStoreService()
result = service.index_file("docs/report.pdf", source_label="report.pdf")
print(result.ids, result.skipped_duplicates)
results = service.search("项目背景", k=3)
```

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
- `POST /index`: 上传文件，执行提取、分割并写入向量库
- `POST /documents`: 加载、分割并写入本地向量库
- `DELETE /documents`: 按 `ids` 或 `source` 删除向量库记录
- `POST /search`: 相似度检索

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

curl -X POST http://127.0.0.1:8000/documents \
  -H "Content-Type: application/json" \
  -d '{"path":"docs/report.pdf","chunk_size":1000,"chunk_overlap":200}'

curl -X POST http://127.0.0.1:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"项目背景","k":3}'
```

## 支持格式

当前按本地文件扩展名注册了以下类型：

`txt`, `log`, `csv`, `tsv`, `json`, `jsonl`, `ndjson`, `pdf`, `md`, `markdown`, `mdx`, `html`, `htm`, `mht`, `mhtml`, `xml`, `doc`, `docx`, `ppt`, `pptx`, `xls`, `xlsx`, `eml`, `msg`, `chm`, `epub`, `odt`, `org`, `rst`, `rtf`, `srt`, `jpg`, `jpeg`, `png`, `tif`, `tiff`, `bmp`, `heic`, `ipynb`, `toml`, `yaml`, `yml`，以及常见源码文件。

更多说明见 [src/loader/README.md](src/loader/README.md) 和 [src/splitter/README.md](src/splitter/README.md)。

## 测试

测试使用 Python 标准库 `unittest`，不依赖真实 LangChain 安装即可验证注册表、懒导入逻辑和 splitter 封装：

```bash
PYTHONPATH=. python -m unittest discover -s tests
```
