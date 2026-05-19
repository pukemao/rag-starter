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

## Markdown 优化

`load_and_split_documents()` 对 `.md`、`.markdown`、`.mdx` 有专门处理：先使用 LangChain `MarkdownHeaderTextSplitter` 按 `#` 到 `######` 标题聚合内容，并保留标题文本，然后再用 `RecursiveCharacterTextSplitter` 控制最大 chunk 大小。

这样可以避免 Markdown loader 的 `elements` 模式把标题和正文拆成不同 chunk，导致 RAG 检索命中正文时缺少标题上下文。最终 chunk 会尽量保持：

```text
# 标题
正文段落
```

metadata 中会保留 `h1`、`h2` 等标题层级，便于后续展示来源或过滤。

## Word 优化

`load_and_split_documents()` 对 `.doc`、`.docx` 有专门处理：先按标题层级聚合章节，再使用 `RecursiveCharacterTextSplitter` 控制 chunk 大小。

`.docx` 会通过 `python-docx` 读取 Word 段落样式，识别 `Heading 1`、`Heading 2`、`标题 1` 等标题层级；`.doc` 会继续使用 LangChain/Unstructured 加载器，但会把 `Title`、`Header` 元素与后续正文重新聚合，避免标题单独成为一个过短 chunk。

最终 chunk 会尽量保持：

```text
# 一级标题
## 二级标题
正文段落
```

当某个章节很长、需要 recursive 二次切分时，后续子 chunk 会自动补回 `heading_context`，保证检索命中正文片段时仍能带上所属标题。metadata 会保留 `h1`、`h2`、`heading_context` 和 `chunk_type=word_section`，便于 RAG 提示词构造和来源展示。

## Excel 优化

`load_and_split_documents()` 对 `.xls`、`.xlsx` 也有专门处理。表格文件不会直接交给通用字符分割器，而是先按工作表读取，再把表头和数据行组织成适合检索的文本：

```text
文件: sales.xlsx
工作表: 订单
表头: 订单号 | 客户 | 金额
第3行: 订单号=A001；客户=张三；金额=120
```

这种结构保证每个 chunk 都带有文件名、工作表名和列名语义，避免 RAG 只检索到单元格值却不知道该值对应哪个字段。大表会按完整数据行分块，并在每个 chunk 中重复表头；metadata 会保留 `sheet_name`、`sheet_index`、`start_row`、`end_row`、`row_count` 等信息。

`.xlsx` 使用 `openpyxl` 读取，`.xls` 使用 `xlrd` 读取。缺少依赖时会返回明确的安装提示。

## PDF 优化

`load_and_split_documents()` 对 `.pdf` 也有专门处理，不再直接依赖按页后的通用字符切分。当前方案优先使用 `pymupdf4llm` 将 PDF 转成接近 Markdown 的结构化文本，再按标题层级聚合为章节块，最后用 `RecursiveCharacterTextSplitter` 控制 chunk 大小。

这样可以尽量保留 PDF 的标题、目录、表格和阅读顺序，减少下面这些问题：

- 标题和正文被拆成不同 chunk
- 页眉页脚和页码污染正文
- 跨页段落被硬切断
- 表格值失去字段语义

每个 PDF chunk 会尽量保留：

```text
# 章节标题
正文段落
```

metadata 中会保留 `page_start`、`page_end`、`pages`、`heading_context`、`h1`-`h6`、`table_count`、`chunk_type=pdf_section`，方便后续检索展示和来源定位。

如果 `pymupdf4llm` 不可用，系统会明确提示安装依赖。若某些 PDF 结构非常复杂，仍可通过 `load_and_split_documents(..., splitter_type="recursive")` 回退到通用切分，但生产环境建议优先使用当前 PDF 专用链路。
