from src.eval.docid import build_docid, build_docid_from_document


def test_build_docid_is_stable():
    d1 = build_docid(source_url="https://a/b", chunk_index=1, content="hello")
    d2 = build_docid(source_url="https://a/b", chunk_index=1, content="hello")
    assert d1 == d2


def test_build_docid_changes_with_content():
    d1 = build_docid(source_url="https://a/b", chunk_index=1, content="hello")
    d2 = build_docid(source_url="https://a/b", chunk_index=1, content="world")
    assert d1 != d2


def test_build_docid_from_document_prefers_existing_metadata_docid():
    class D:
        metadata = {"docid": "abc123", "source_url": "https://a/b", "chunk_index": 0}
        page_content = "ignored"

    assert build_docid_from_document(D()) == "abc123"
