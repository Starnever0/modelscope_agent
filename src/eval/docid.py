"""
Document ID 的生成逻辑 - 基于 source_url、chunk_index 和 content 的哈希值构建唯一 docid
用于评估阶段的文档追踪和对齐，确保即使文档内容发生微小变化也能生成不同的 docid，从而反映出内容的差异。
"""
import hashlib
from typing import Any


def _normalize_text(value: str) -> str:
    return " ".join((value or "").strip().split())


def build_docid(source_url: str, chunk_index: int, content: str) -> str:
    payload = f"{_normalize_text(source_url)}|{chunk_index}|{_normalize_text(content)}"
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
    return f"doc_{digest}"


def build_docid_from_document(doc: Any, fallback_chunk_index: int = 0) -> str:
    metadata = getattr(doc, "metadata", {}) or {}
    if metadata.get("docid"):
        return str(metadata["docid"])

    source_url = str(metadata.get("source_url") or metadata.get("url") or metadata.get("source_file") or "")
    chunk_index = int(metadata.get("chunk_index", fallback_chunk_index))
    page_content = getattr(doc, "page_content", "") or ""
    return build_docid(source_url=source_url, chunk_index=chunk_index, content=page_content)
