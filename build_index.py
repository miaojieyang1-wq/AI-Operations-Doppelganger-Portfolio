"""
这个脚本用于读取 works/ 文件夹中的 Markdown / Word 作品集文档，
将文档切分成适合检索的小文本块，生成向量后保存到本地 chroma_db/ 向量库。

运行方式：
python build_index.py

这个脚本通常只需要运行一次；除非 works/ 文件夹内容有更新，才需要重新运行。
"""

import json
import os
import shutil
import sys
import time
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import runtime_paths

PROJECT_DIR = Path(__file__).parent
WORKS_DIR = PROJECT_DIR / "works"
OPTIONAL_CONFIG_FILE = PROJECT_DIR / "config.yaml"
CHROMA_DIR = runtime_paths.data_path("chroma_db")
COLLECTION_NAME = "works_portfolio"
LOCAL_VECTORSTORE_FILE = CHROMA_DIR / "local_vectors.json"
EMBEDDING_MODEL_NAME = "BAAI/bge-small-zh-v1.5"
FALLBACK_EMBEDDING_NAME = "local-hashing-char-ngram"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
_EMBEDDING_MODEL: Any | None = None

# 可选同步路径配置，默认关闭。
# 此路径指向知识治理控制台的同步导出文件夹。启用后，控制台中注册和修正的知识单元将自动纳入Agent知识库索引。
# 默认关闭，Agent独立运行时不依赖此路径。
#
# 启用方式二选一：
# 1. 环境变量：
#    AI_OPS_INCLUDE_SYNC_DIR=1
#    AI_OPS_SYNC_DIR=控制台sync文件夹路径
# 2. 项目根目录 config.yaml：
#    knowledge_sync:
#      enabled: false
#      path: ""
SYNC_ENABLED_ENV = "AI_OPS_INCLUDE_SYNC_DIR"
SYNC_DIR_ENV = "AI_OPS_SYNC_DIR"


def ensure_works_folder() -> None:
    """确保 works/ 文件夹存在；如果缺失则创建示例知识库文档。"""
    if WORKS_DIR.exists():
        return
    WORKS_DIR.mkdir(parents=True, exist_ok=True)
    example_file = WORKS_DIR / "example.md"
    example_file.write_text(
        "这是AI运营分身的示例知识库文档。请将您的运营文档、分析报告、方法论总结放入works/文件夹，然后重新运行python build_index.py构建索引。",
        encoding="utf-8",
    )
    print("未发现 works/ 文件夹，已自动创建并放入 example.md 示例文档。")


def read_optional_config() -> dict[str, Any]:
    """读取项目根目录可选 config.yaml；文件不存在或解析失败时返回空配置。"""
    if not OPTIONAL_CONFIG_FILE.exists():
        return {}
    try:
        import yaml

        data = yaml.safe_load(OPTIONAL_CONFIG_FILE.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def is_truthy_config_value(value: Any) -> bool:
    """解析环境变量或 YAML 中的布尔开关。"""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on", "是", "开启"}


def get_optional_sync_dir() -> Path | None:
    """读取默认关闭的控制台 sync/ 导出路径。"""
    config = read_optional_config()
    sync_config = config.get("knowledge_sync", {}) if isinstance(config.get("knowledge_sync", {}), dict) else {}

    enabled_value = os.getenv(SYNC_ENABLED_ENV, sync_config.get("enabled", False))
    if not is_truthy_config_value(enabled_value):
        return None

    sync_dir_text = os.getenv(SYNC_DIR_ENV, str(sync_config.get("path", ""))).strip()
    if not sync_dir_text:
        print("已启用控制台同步路径，但未配置 AI_OPS_SYNC_DIR 或 config.yaml 中的 knowledge_sync.path。")
        return None

    return Path(sync_dir_text).expanduser()


def get_source_dirs() -> list[Path]:
    """返回知识库扫描目录；默认只扫描 works/，可选追加控制台 sync/ 导出目录。"""
    source_dirs = [WORKS_DIR]
    sync_dir = get_optional_sync_dir()
    if sync_dir is None:
        return source_dirs
    if not sync_dir.exists():
        print(f"已启用控制台同步路径，但目录不存在：{sync_dir}")
        return source_dirs
    source_dirs.append(sync_dir)
    print(f"已启用控制台同步路径：{sync_dir}")
    return source_dirs


def check_sentence_transformers_model() -> None:
    """安装友好检查：提示 sentence-transformers 模型状态，失败时给出手动指引。"""
    print(f"正在检查 sentence-transformers 模型：{EMBEDDING_MODEL_NAME}")
    print("模型预计大小约为100MB级别，首次下载时间取决于网络环境。")
    try:
        from sentence_transformers import SentenceTransformer

        try:
            SentenceTransformer(EMBEDDING_MODEL_NAME, local_files_only=True)
            print("已检测到本地 sentence-transformers 模型缓存。")
        except Exception:
            print("本地尚未检测到该模型缓存。当前索引构建会继续使用项目内置的本地轻量向量方案。")
            print("如需手动下载，可在网络可用时运行：")
            print(f"python -c \"from sentence_transformers import SentenceTransformer; SentenceTransformer('{EMBEDDING_MODEL_NAME}')\"")
    except Exception:
        print("未安装 sentence-transformers 或当前环境无法加载它。")
        print("项目会继续使用本地轻量向量方案构建索引，不影响基础检索功能。")


def estimate_processing_time(file_count: int) -> str:
    """根据文件数量给出粗略处理时间。"""
    seconds = max(3, file_count * 2)
    if seconds < 60:
        return f"约 {seconds} 秒"
    return f"约 {seconds // 60} 分钟"


def backup_existing_index() -> None:
    """覆盖索引前备份旧知识库索引目录。"""
    if not CHROMA_DIR.exists():
        return
    backup_dir = runtime_paths.data_path("chroma_db_backup")
    if backup_dir.exists():
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_dir = runtime_paths.data_path(f"chroma_db_backup_{timestamp}")
    shutil.copytree(CHROMA_DIR, backup_dir)
    print(f"已备份旧索引到：{backup_dir}")


def should_rebuild_existing_index() -> bool:
    """已有索引时询问覆盖还是跳过；非交互环境默认备份后覆盖。"""
    if not CHROMA_DIR.exists():
        return True
    print(f"检测到已有索引文件夹：{CHROMA_DIR}")
    if not sys.stdin.isatty():
        print("当前为非交互环境，将自动备份旧索引并覆盖。")
        backup_existing_index()
        return True
    answer = input("是否覆盖旧索引？输入 y 覆盖，其他任意键跳过：").strip().lower()
    if answer in {"y", "yes", "是"}:
        backup_existing_index()
        return True
    print("已跳过索引构建。")
    return False


def folder_size(path: Path) -> int:
    """计算文件夹大小。"""
    if not path.exists():
        return 0
    return sum(file_path.stat().st_size for file_path in path.rglob("*") if file_path.is_file())


def get_embedding_model() -> Any:
    """加载本地向量模型；全局只加载一次，避免重复占用时间和内存。"""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        try:
            print(f"正在加载本地向量模型：{EMBEDDING_MODEL_NAME}")
            print("如果这是第一次运行，程序会自动下载模型文件，请耐心等待下载完成。")
            # 改动位置：优先使用 fastembed 的 ONNX 本地模型，避免 PyTorch DLL 初始化失败。
            from fastembed import TextEmbedding

            _EMBEDDING_MODEL = {
                "type": "fastembed",
                "model": TextEmbedding(model_name=EMBEDDING_MODEL_NAME),
            }
        except Exception as exc:
            print(f"未能启用 fastembed 向量模型，将使用本地轻量向量方案。原因：{exc}")
            print("当前方案不需要额外 API、torch 或 Rust，适合先稳定构建作品集知识库。")
            from sklearn.feature_extraction.text import HashingVectorizer

            _EMBEDDING_MODEL = {
                "type": "hashing",
                "model": HashingVectorizer(
                    analyzer="char_wb",
                    ngram_range=(2, 4),
                    n_features=2048,
                    alternate_sign=False,
                    norm="l2",
                ),
            }

    return _EMBEDDING_MODEL


def encode_texts(texts: list[str], show_progress_bar: bool = False) -> list[list[float]]:
    """使用本地模型生成文本向量。"""
    embedding_backend = get_embedding_model()
    if embedding_backend["type"] == "fastembed":
        embeddings = embedding_backend["model"].embed(texts, batch_size=32)
        return [embedding.tolist() for embedding in embeddings]

    vectors = embedding_backend["model"].transform(texts)
    return vectors.toarray().tolist()


def encode_query(text: str) -> list[float]:
    """使用同一个本地模型生成查询向量。"""
    return encode_texts([text], show_progress_bar=False)[0]


def read_docx_text(file_path: Path) -> str:
    """读取 Word 文档正文文字。"""
    namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(file_path) as docx_zip:
        xml_text = docx_zip.read("word/document.xml")

    root = ElementTree.fromstring(xml_text)
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespaces):
        texts = [node.text or "" for node in paragraph.findall(".//w:t", namespaces)]
        line = "".join(texts).strip()
        if line:
            paragraphs.append(line)

    return "\n".join(paragraphs)


def read_source_files() -> list[tuple[Path, str]]:
    """读取知识库扫描目录下所有 Markdown 和 Word 文档。"""
    documents: list[tuple[Path, str]] = []
    supported_files: list[Path] = []
    for source_dir in get_source_dirs():
        if not source_dir.exists():
            continue
        supported_files.extend(
            file_path
            for file_path in source_dir.rglob("*")
            if file_path.is_file() and file_path.suffix.lower() in {".md", ".docx"}
        )

    for file_path in sorted(supported_files):
        if file_path.suffix.lower() == ".md":
            text = file_path.read_text(encoding="utf-8", errors="replace").strip()
        else:
            text = read_docx_text(file_path).strip()

        if text:
            documents.append((file_path, text))

    return documents


def get_metadata_source_path(file_path: Path) -> str:
    """生成索引元数据中的来源路径；项目内文件保留相对路径，外部同步文件标记为 sync 来源。"""
    try:
        return file_path.relative_to(PROJECT_DIR).as_posix()
    except ValueError:
        sync_dir = get_optional_sync_dir()
        if sync_dir:
            try:
                return f"sync/{file_path.relative_to(sync_dir).as_posix()}"
            except ValueError:
                pass
        return file_path.name


def split_text_recursively(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> list[str]:
    """用纯 Python 递归切分文本，避免导入 langchain_text_splitters 触发 torch。"""
    separators = ["\n\n", "\n", "。", "！", "？", "；", ";", "，", ",", " ", ""]

    def split_with_separator(segment: str, separator_index: int) -> list[str]:
        if len(segment) <= chunk_size:
            return [segment]

        separator = separators[separator_index]
        if separator:
            parts = segment.split(separator)
            pieces = [part + separator for part in parts[:-1]]
            if parts[-1]:
                pieces.append(parts[-1])
        else:
            pieces = [segment[index : index + chunk_size] for index in range(0, len(segment), chunk_size)]

        chunks: list[str] = []
        current = ""
        for piece in pieces:
            if len(piece) > chunk_size and separator_index + 1 < len(separators):
                if current.strip():
                    chunks.append(current.strip())
                    current = ""
                chunks.extend(split_with_separator(piece, separator_index + 1))
                continue

            if len(current) + len(piece) <= chunk_size:
                current += piece
            else:
                if current.strip():
                    chunks.append(current.strip())
                current = piece

        if current.strip():
            chunks.append(current.strip())

        return chunks

    raw_chunks = split_with_separator(text, 0)
    if chunk_overlap <= 0:
        return raw_chunks

    overlapped_chunks: list[str] = []
    previous_tail = ""
    for chunk in raw_chunks:
        merged = f"{previous_tail}{chunk}" if previous_tail else chunk
        overlapped_chunks.append(merged.strip())
        previous_tail = chunk[-chunk_overlap:]

    return overlapped_chunks


def split_documents(documents: list[tuple[Path, str]]) -> tuple[list[str], list[dict]]:
    """将文档切分成小块，并为每个小块记录来源文件。"""
    chunks: list[str] = []
    metadatas: list[dict] = []

    for file_path, text in documents:
        relative_path = get_metadata_source_path(file_path)
        split_texts = split_text_recursively(text)

        for chunk_index, chunk_text in enumerate(split_texts):
            metadata = {
                "source": relative_path,
                "chunk_index": chunk_index,
            }
            if relative_path == "works/mathematics-full.md":
                metadata["document_mode"] = "full_display_direct_read"
                metadata["note"] = "完整展示类问题优先走独立文件读取，不经过RAG切分检索"
            elif relative_path.startswith("works/math-segments/"):
                metadata["document_mode"] = "math_segment_retrieval"
            chunks.append(chunk_text)
            metadatas.append(metadata)

    return chunks, metadatas


def save_local_vectorstore(chunks: list[str], embeddings: list[list[float]], metadatas: list[dict]) -> None:
    """保存本地向量文件，避免 Chroma Rust 后端在部分 Windows 环境中崩溃。"""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    vectorstore_data = {
        "collection_name": COLLECTION_NAME,
        "embedding_model": EMBEDDING_MODEL_NAME,
        "fallback_embedding": FALLBACK_EMBEDDING_NAME,
        "documents": chunks,
        "embeddings": embeddings,
        "metadatas": metadatas,
    }
    LOCAL_VECTORSTORE_FILE.write_text(
        json.dumps(vectorstore_data, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> None:
    """构建 works/ 文件夹的本地知识库索引。"""
    ensure_works_folder()
    if not should_rebuild_existing_index():
        return

    documents = read_source_files()
    print(f"即将处理的文档数量：{len(documents)}")
    print(f"预估处理时间：{estimate_processing_time(len(documents))}")
    check_sentence_transformers_model()

    chunks, metadatas = split_documents(documents)

    if not chunks:
        print("已处理的文件数量：0")
        print("分割的文本块数量：0")
        print(f"存储位置：{CHROMA_DIR}")
        print("请先将 .md 或 .docx 文档放入 works/ 文件夹后再构建索引。")
        return

    embeddings = encode_texts(chunks, show_progress_bar=True)

    save_local_vectorstore(chunks, embeddings, metadatas)

    index_size_mb = folder_size(CHROMA_DIR) / (1024 * 1024)
    print(f"已处理的文件数量：{len(documents)}")
    print(f"分割的文本块数量：{len(chunks)}")
    print(f"索引文件大小：{index_size_mb:.2f} MB")
    print(f"存储位置：{CHROMA_DIR}")


if __name__ == "__main__":
    main()
