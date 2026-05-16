import json
import logging
import math
from pathlib import Path
from functools import lru_cache

import api_runtime
# 改动位置：复用 build_index.py 的本地 Embedding 模型，确保全局只加载一次。
from build_index import CHROMA_DIR, LOCAL_VECTORSTORE_FILE, encode_query, get_embedding_model


DEFAULT_MODEL = api_runtime.DEFAULT_MODEL
DEFAULT_BASE_URL = api_runtime.DEFAULT_BASE_URL
logger = logging.getLogger(__name__)


def create_deepseek_client():
    """创建 DeepSeek 客户端，配置方式与 app.py 保持一致。"""
    return api_runtime.create_client()


def call_deepseek_api(system_prompt: str, user_question: str) -> str:
    """调用 DeepSeek API，返回模型回复。"""
    return api_runtime.call_chat_completion(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question},
        ],
        temperature=0.7,
    )


@lru_cache(maxsize=1)
def load_vectorstore_by_signature(file_mtime_ns: int, file_size: int):
    """按文件签名缓存本地向量库，文件更新后自动失效。"""
    try:
        get_embedding_model()
        return json.loads(LOCAL_VECTORSTORE_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("向量数据库暂时无法加载，将使用普通回答模式：%s", exc)
        return None


def load_vectorstore():
    """从本地 chroma_db/ 文件夹加载向量数据库。"""
    api_runtime.ensure_env_loaded()

    if not LOCAL_VECTORSTORE_FILE.exists():
        logger.info("未找到本地知识库索引，将使用普通回答模式。")
        return None

    stat = LOCAL_VECTORSTORE_FILE.stat()
    return load_vectorstore_by_signature(stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=1)
def get_vectorstore_status_by_signature(file_mtime_ns: int, file_size: int) -> dict:
    """按文件签名缓存知识库状态，避免侧边栏每次刷新都读取 5MB JSON。"""
    try:
        vectorstore_data = json.loads(LOCAL_VECTORSTORE_FILE.read_text(encoding="utf-8"))
        return {
            "exists": True,
            "chunk_count": len(vectorstore_data.get("documents", [])),
            "message": "",
        }
    except Exception as exc:
        return {
            "exists": False,
            "chunk_count": 0,
            "message": f"知识库暂时无法读取，当前使用基础问答模式。原因：{exc}",
        }


def get_vectorstore_status() -> dict:
    """获取知识库状态，用于界面展示，不触发 Embedding 初始化。"""
    if not LOCAL_VECTORSTORE_FILE.exists():
        return {
            "exists": False,
            "chunk_count": 0,
            "message": "知识库尚未构建，请先运行 python build_index.py 构建索引。当前使用基础问答模式。",
        }

    stat = LOCAL_VECTORSTORE_FILE.stat()
    return get_vectorstore_status_by_signature(stat.st_mtime_ns, stat.st_size)


def query_rag(user_question: str, system_prompt: str) -> str:
    """检索作品集上下文后调用 DeepSeek；如果没有向量库，则直接调用 DeepSeek。"""
    api_runtime.ensure_env_loaded()

    if api_runtime.demo_engine.is_demo_mode():
        return call_deepseek_api(system_prompt, user_question)

    vectorstore = load_vectorstore()
    if vectorstore is None:
        return call_deepseek_api(system_prompt, user_question)

    try:
        question_embedding = encode_query(user_question)
        retrieved_chunks = retrieve_top_chunks(vectorstore, question_embedding, top_k=3)
    except Exception as exc:
        logger.warning("作品集检索暂时不可用，将使用普通回答模式：%s", exc)
        return call_deepseek_api(system_prompt, user_question)

    context_text = "\n\n---\n\n".join(chunk for chunk in retrieved_chunks if chunk)
    if context_text:
        enhanced_system_prompt = (
            f"{system_prompt}\n\n"
            "以下是从作品集文档中检索到的相关内容，请优先参考这些内容回答，"
            "但不要生硬照抄；如果检索内容和问题无关，请以原系统提示词为准。\n\n"
            f"{context_text}"
        )
    else:
        enhanced_system_prompt = system_prompt

    return call_deepseek_api(enhanced_system_prompt, user_question)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """计算两个向量的余弦相似度。"""
    dot_product = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot_product / (left_norm * right_norm)


def retrieve_top_chunks(vectorstore: dict, query_embedding: list[float], top_k: int = 5, min_score: float = 0.12) -> list[str]:
    """从本地向量文件中检索最相关的文本块。"""
    documents = vectorstore.get("documents", [])
    embeddings = vectorstore.get("embeddings", [])
    scored_chunks = [
        (cosine_similarity(query_embedding, embedding), document)
        for document, embedding in zip(documents, embeddings)
    ]
    scored_chunks.sort(key=lambda item: item[0], reverse=True)
    return [document for score, document in scored_chunks[:top_k] if document and score >= min_score]


if __name__ == "__main__":
    # 这个简单入口用于本地快速测试 RAG 是否能正常调用。
    question = input("请输入想测试的问题：").strip()
    if not question:
        raise SystemExit("没有输入问题，已退出。")

    import config_loader

    base_prompt = config_loader.get_system_prompt("prompt_background")
    print(query_rag(question, base_prompt))
