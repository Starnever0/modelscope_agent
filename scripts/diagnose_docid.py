"""
诊断脚本：检查 docid 生成逻辑中的不一致性
问题假设：生成数据集时和评测时的 docid 计算使用不同的 chunk_index，导致 docid 不匹配
"""
from dotenv import load_dotenv
load_dotenv()

# 必须在导入业务模块前加载 dotenv
import json
from src.eval.dataset_io import load_eval_cases_from_jsonl
from src.eval.docid import build_docid_from_document
from src.node.retriever import get_cached_retriever
from src.eval.docid import build_docid

# 加载第一个样本
cases = load_eval_cases_from_jsonl("data/eval/datasets/auto_questions_docid_80.jsonl")
first_case = cases[0]

print("=" * 80)
print("诊断: 第一个样本的 docid 不匹配问题")
print("=" * 80)
print(f"\n📋 样本信息:")
print(f"  case_id: {first_case.case_id}")
print(f"  query: {first_case.query[:60]}...")
print(f"  expected_docids (from JSONL): {first_case.expected_docids}")
print(f"  source_urls (from metadata): {first_case.metadata.get('source_urls', [])}")

# 尝试检索这个查询
retriever = get_cached_retriever("data/faiss_db")
retrieved_docs = retriever.invoke(first_case.query)

print(f"\n🔍 检索结果 (top 10):")
for idx, doc in enumerate(retrieved_docs[:10]):
    metadata = doc.metadata or {}
    generated_docid = build_docid_from_document(doc, fallback_chunk_index=idx)
    
    source_url = metadata.get("source_url") or metadata.get("url") or ""
    chunk_index = metadata.get("chunk_index", "未设置")
    content_preview = (doc.page_content or "")[:50].replace("\n", " ")
    
    print(f"\n  [位置 {idx}]")
    print(f"    source_url: {source_url}")
    print(f"    chunk_index (metadata): {chunk_index}")
    print(f"    fallback_chunk_index (used): {idx}")
    print(f"    content: {content_preview}...")
    print(f"    re-generated docid: {generated_docid}")
    
    if generated_docid in first_case.expected_docids:
        print(f"    ✅ MATCH with expected!")
    
    # 也计算一下如果用 metadata 中的 chunk_index（或默认 0）会怎样
    if isinstance(chunk_index, int):
        docid_with_meta = build_docid_from_document(doc, fallback_chunk_index=chunk_index)
        print(f"    docid (using metadata chunk_index): {docid_with_meta}")
    
    # 如果 metadata 中有预存的 docid，也打印一下
    if metadata.get("docid"):
        print(f"    docid (from metadata): {metadata.get('docid')}")

print("\n" + "=" * 80)
print("问题诊断:")
print("=" * 80)
print(f"""
如果看到上述输出：
1. 检索到的文档的 URL 与 expected_docids 对应的 URL 相同
2. 但是 re-generated docid 与 expected_docids 不同
   => 这说明 chunk_index 或 content 不一致

关键问题可能是：
- build_docid_from_document() 在生成数据集时使用的 fallback_chunk_index=idx (遍历索引)
- 在评测时也使用 fallback_chunk_index=idx (检索位置索引)
- 两个 idx 值不同 => 生成了不同的 docid

解决方案：
1. 在生成数据集时，预先将计算出的 docid 存储到文档 metadata 中
2. 在评测时，优先使用 metadata 中预存的 docid
""")
