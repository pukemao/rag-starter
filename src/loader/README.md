# Document Loaders

`src/loader` 是一层轻量封装：每种本地文档格式一个模块，模块内暴露 `SPEC` 和 `create_loader()`；`registry.py` 负责按文件扩展名选择对应模块。

## 目录结构

- `registry.py`: 统一入口，提供 `get_loader()`、`load_documents()`、`lazy_load_documents()`、`supported_extensions()`。
- `directory.py`: 目录扫描和批量加载。
- `base.py`: 共享的 `LoaderSpec` 元数据。
- `utils.py`: 扩展名规范化、懒导入和错误类型。
- `*.py`: 具体格式加载器，每个文档类型一个文件。

## 使用方式

```python
from src.loader import load_documents

docs = load_documents("data/manual.docx")
```

带 LangChain loader 参数：

```python
from src.loader import get_loader

loader = get_loader("data/items.json", jq_schema=".items[]", text_content=False)
docs = loader.load()
```

目录批量加载：

```python
from src.loader.directory import load_directory

docs = load_directory("data", recursive=True)
```

## 模块与格式

| 模块 | 扩展名 | LangChain 加载器 |
| --- | --- | --- |
| `text.py` | `.txt`, `.log` | `TextLoader` |
| `csv.py` | `.csv` | `CSVLoader` |
| `tsv.py` | `.tsv` | `UnstructuredTSVLoader` |
| `json.py` | `.json`, `.jsonl`, `.ndjson` | `JSONLoader` |
| `pdf.py` | `.pdf` | `PyPDFLoader` |
| `markdown.py` | `.md`, `.markdown`, `.mdx` | `UnstructuredMarkdownLoader` |
| `html.py` | `.html`, `.htm` | `BSHTMLLoader` |
| `mhtml.py` | `.mht`, `.mhtml` | `MHTMLLoader` |
| `xml.py` | `.xml` | `UnstructuredXMLLoader` |
| `word.py` | `.doc`, `.docx` | `UnstructuredWordDocumentLoader` |
| `powerpoint.py` | `.ppt`, `.pptx` | `UnstructuredPowerPointLoader` |
| `excel.py` | `.xls`, `.xlsx` | `UnstructuredExcelLoader` |
| `email.py` | `.eml`, `.msg` | `UnstructuredEmailLoader` |
| `chm.py` | `.chm` | `UnstructuredCHMLoader` |
| `epub.py` | `.epub` | `UnstructuredEPubLoader` |
| `odt.py` | `.odt` | `UnstructuredODTLoader` |
| `org.py` | `.org` | `UnstructuredOrgModeLoader` |
| `rst.py` | `.rst` | `UnstructuredRSTLoader` |
| `rtf.py` | `.rtf` | `UnstructuredRTFLoader` |
| `subtitle.py` | `.srt` | `SRTLoader` |
| `image.py` | `.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`, `.bmp`, `.heic` | `UnstructuredImageLoader` |
| `notebook.py` | `.ipynb` | `NotebookLoader` |
| `toml.py` | `.toml` | `TomlLoader` |
| `yaml.py` | `.yaml`, `.yml` | `TextLoader` |
| `source_code.py` | 常见源码扩展名 | `PythonLoader` / `TextLoader` |

## 新增一种格式

1. 新建 `src/loader/<type>.py`。
2. 定义 `SPEC = LoaderSpec(...)`。
3. 实现 `create_loader(file_path, **kwargs)`。
4. 把模块路径加入 `registry.py` 的 `_LOADER_MODULES`。
5. 为注册表和关键参数补测试。

示例：

```python
from pathlib import Path
from typing import Any

from .base import LoaderSpec
from .utils import create_loader_instance

SPEC = LoaderSpec(
    key="pdf",
    title="PDF",
    extensions=(".pdf",),
    module=__name__,
    dependencies=("langchain-community", "pypdf"),
)


def create_loader(file_path: str | Path, **kwargs: Any) -> Any:
    return create_loader_instance(
        file_path,
        ("langchain_community.document_loaders", "langchain_community.document_loaders.pdf"),
        "PyPDFLoader",
        SPEC.dependencies,
        **kwargs,
    )
```

## 设计说明

LangChain 的文档加载器分散在 `langchain_community.document_loaders` 下，并且很多格式依赖可选包。这里采用懒导入：只有实际加载某种文件时才导入对应 LangChain 类。这样注册表和测试不会因为缺少 PDF、OCR、Office 等可选依赖而失败。

远程服务类加载器（例如 Notion、Slack、S3、GitHub）通常需要 token、URL、bucket 或工作区信息，未纳入按扩展名自动路由。需要这类加载器时，建议在 `src/loader/integrations/` 下按服务单独封装。
