import sys
import os
import re
import shutil
import time
import traceback

from tqdm import tqdm
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from src.embedding.embedding import get_embedding
from src.build_utils import resolve_target_dirs

# 加载 .env，确保构建索引时也能读取 API Key
load_dotenv()

# 路径修正
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_RAW_DIR = './data/raw/docs'
FAISS_DOC_PATH = './data/faiss_db'
CHUNK_SIZE = 512
BATCH_SIZE = 32
CHUNK_OVERLAP = 100
# # 研习社目录
# LEARN_DIR = './data/raw_learn'

SAFE_CHUNK_SIZE = 1000
SAFE_BATCH_SIZE = 10


def parse_metadata(text, filename):
    """提取元数据"""
    metadata = {"source_file": filename, "data_type": "doc"}
    url_match = re.search(r"^> Source URL: (.*?)\n", text, re.MULTILINE)
    if url_match: metadata['source_url'] = url_match.group(1).strip()
    title_match = re.search(r"^> Title: (.*?)\n", text, re.MULTILINE)
    if title_match: metadata['title'] = title_match.group(1).strip()
    type_match = re.search(r"^> Data Type: (.*?)\n", text, re.MULTILINE)
    if type_match: metadata['data_type'] = type_match.group(1).strip()
    return metadata


def load_all_docs(directories):
    """加载并切分文档"""
    all_chunks = []

    headers_to_split_on = [("#", "h1"), ("##", "h2"), ("###", "h3")]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

    # 使用更安全的切片大小
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=SAFE_CHUNK_SIZE,
        chunk_overlap=128,
        separators=["\n```", "\n\n", "\n", " ", ""],
        keep_separator=True
    )

    for directory in directories:
        if not os.path.exists(directory):
            print(f"⚠️ 目录不存在跳过: {directory}")
            continue

        files = []
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                if filename.endswith(".md"):
                    files.append(os.path.join(root, filename))

        print(f"📂 正在处理目录 {directory}: 发现 {len(files)} 个文件")

        for filepath in tqdm(files, desc="Splitting"):
            filename = os.path.basename(filepath)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    text = f.read()

                if not text.strip(): continue

                meta = parse_metadata(text, filename)
                header_splits = markdown_splitter.split_text(text)
                final_splits = text_splitter.split_documents(header_splits)

                for doc in final_splits:
                    doc.metadata.update(meta)
                    source_info = f"来源: {meta.get('title', filename)}"
                    if 'source_url' in meta: source_info += f" ({meta['source_url']})"

                    header_path = " > ".join([doc.metadata.get(k, "") for k in ["h1", "h2", "h3"] if k in doc.metadata])
                    if header_path: source_info += f" | 章节: {header_path}"

                    doc.page_content = f"【{source_info}】\n\n{doc.page_content}"

                    # 严格过滤
                    if doc.page_content and len(doc.page_content.strip()) > 5:
                        # 再次强制截断，防止 metadata 注入后超长
                        if len(doc.page_content) > 2000:
                            doc.page_content = doc.page_content[:2000]
                        all_chunks.append(doc)

            except Exception as e:
                print(f"❌ 处理文件错误 {filename}: {e}")

    return all_chunks


def add_single_doc_safely(vector_store, doc, embeddings):
    """单条写入，捕捉所有异常"""
    try:
        if vector_store is None:
            return FAISS.from_documents([doc], embeddings)
        else:
            vector_store.add_documents([doc])
            return vector_store
    except Exception as e:
        # 这里是重点：如果这一条失败了，打印出来，但不要抛出异常，直接返回旧的 store
        print(f"\n❌ [跳过毒数据] {doc.metadata.get('source_file')} - 错误: {str(e)[:100]}")
        return vector_store


def build_faiss_index(chunks, save_path):
    if not chunks:
        print("❌ 没有切片数据。")
        return

    print(f"🚀 开始向量化 {len(chunks)} 个切片...")
    embeddings = get_embedding()
    vector_store = None

    # === 核心逻辑修改 ===
    # 我们不再整批整批的做，而是采用“尝试批量，失败降级”的策略
    # 初始化阶段最容易挂，所以初始化我们直接用第一条能成功的数据来做

    success_count = 0

    # 1. 寻找第一个有效切片来初始化 Vector Store
    print("⚙️ 正在初始化索引库...")
    pbar = tqdm(total=len(chunks), desc="Indexing")

    # 临时缓冲区
    current_batch = []

    for doc in chunks:
        current_batch.append(doc)

        # 当凑够一批，或者还没有初始化时
        if len(current_batch) >= SAFE_BATCH_SIZE or vector_store is None:
            try:
                # 尝试批量写入
                if vector_store is None:
                    # 第一次必须非常小心
                    # 如果第一次批量失败，我们将无法获得 vector_store 对象
                    # 所以第一次我们强制用单条模式找到第一个基准
                    if len(current_batch) > 1:
                        # 如果还没初始化就积攒了一批，强制回退到单条处理，确保初始化成功
                        for item in current_batch:
                            vector_store = add_single_doc_safely(vector_store, item, embeddings)
                            if vector_store: success_count += 1
                            pbar.update(1)
                    else:
                        # 单条初始化
                        vector_store = add_single_doc_safely(vector_store, current_batch[0], embeddings)
                        if vector_store: success_count += 1
                        pbar.update(1)
                else:
                    # 已经初始化过了，尝试批量添加
                    vector_store.add_documents(current_batch)
                    success_count += len(current_batch)
                    pbar.update(len(current_batch))

                # 成功后清空缓冲区
                current_batch = []
                time.sleep(0.1)  # 防限流

            except Exception as e:
                # 批量失败，进入逐条挽救模式
                # print(f"\n⚠️ 批次失败，转为逐条模式...")
                for item in current_batch:
                    vector_store = add_single_doc_safely(vector_store, item, embeddings)
                    if vector_store: success_count += 1  # 只有 vector_store 不为 None 且没报错才算成功（这里简化计数）
                    pbar.update(1)
                current_batch = []

    # 处理剩余的
    if current_batch:
        for item in current_batch:
            vector_store = add_single_doc_safely(vector_store, item, embeddings)
            pbar.update(1)

    pbar.close()

    if vector_store:
        print(f"\n💾 正在保存索引到: {save_path}")
        vector_store.save_local(save_path)
        print(f"✅ 构建完成！共存入 {vector_store.index.ntotal} 条向量。")
    else:
        print("\n❌ 构建失败：所有数据均无法向量化。")


def main():
    # 兼容可选目录：当 LEARN_DIR 被注释或未定义时仅处理主数据目录
    target_dirs = resolve_target_dirs(DATA_RAW_DIR, globals().get("LEARN_DIR"))
    all_doc_chunks = load_all_docs(target_dirs)

    if os.path.exists(FAISS_DOC_PATH):
        import shutil
        shutil.rmtree(FAISS_DOC_PATH)
        print("🧹 清理旧索引...")

    build_faiss_index(all_doc_chunks, FAISS_DOC_PATH)


if __name__ == "__main__":
    main()