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
