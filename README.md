# RAG Starter

本项目提供一组基于 LangChain 的本地文档加载器、文档分割器、本地向量数据库封装和 FastAPI 接口。加载器位于 `src/loader`，按文档类型拆分为独立 Python 模块；分割器位于 `src/splitter`，提供统一的 chunk 切分入口；向量库位于 `src/vector_store`，默认使用本地持久化 Chroma。

## 安装

基础依赖：

```bash
pip install langchain-community langchain-core
pip install langchain-text-splitters
pip install langchain-chroma chromadb fastapi uvicorn
```

不同格式会需要额外依赖。建议在需要覆盖办公文档、图片 OCR、EPUB 等格式时安装：

```bash
pip install "unstructured[all-docs]" pypdf beautifulsoup4 jq openpyxl python-docx python-pptx nbformat pillow pytesseract pysrt
```

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
- `POST /documents`: 加载、分割并写入本地向量库
- `DELETE /documents`: 按 `ids` 或 `source` 删除向量库记录
- `POST /search`: 相似度检索

示例：

```bash
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
