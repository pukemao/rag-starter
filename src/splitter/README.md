# Document Splitters

`src/splitter` 提供统一的 LangChain 文档分割入口。它不关心文件格式，只处理已经由 `src.loader` 加载出来的 `Document` 列表。

## 使用方式

```python
from src.loader import load_documents
from src.splitter import split_documents

docs = load_documents("data/report.pdf")
chunks = split_documents(docs, chunk_size=1000, chunk_overlap=200)
```

加载并分割一个文件：

```python
from src.splitter import load_and_split_documents

chunks = load_and_split_documents(
    "data/report.pdf",
    chunk_size=1000,
    chunk_overlap=200,
)
```

## 支持的分割器

| alias | LangChain class | 适用场景 |
| --- | --- | --- |
| `recursive` | `RecursiveCharacterTextSplitter` | 默认选择，适合大多数普通文本和 RAG 入库 |
| `character` | `CharacterTextSplitter` | 按字符规则简单切分 |
| `token` | `TokenTextSplitter` | 按 token 长度控制 chunk |
| `markdown` | `MarkdownTextSplitter` | Markdown 文档 |
| `python` | `PythonCodeTextSplitter` | Python 源码 |

## 设计说明

加载器和分割器保持解耦：

```text
文件 -> loader -> Document 列表 -> splitter -> chunk 列表
```

这样不同文件格式可以复用同一套切块策略，后续调整 `chunk_size`、`chunk_overlap` 或 tokenizer 时，不需要修改各个 loader 模块。
