import hashlib

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.llm.provider import get_llm
from src.prompt.generator_prompt import generator_system_prompt
from src.state.state import RagState
from src.test import timing_decorator

generator_prompt = ChatPromptTemplate.from_messages([("system", generator_system_prompt),

    MessagesPlaceholder("messages"),

    ("human", "{question}"),
])

generate_chain = generator_prompt | get_llm("answer_generate")


def _stable_docid(metadata: dict, fallback_index: int) -> str:
    source = metadata.get("docid") or metadata.get("source_url") or metadata.get("source_file") or f"doc-{fallback_index}"
    if metadata.get("docid"):
        return str(metadata["docid"])
    digest = hashlib.sha1(str(source).encode("utf-8")).hexdigest()[:12]
    return f"doc-{digest}"


def _normalize_image_map(raw_image_map) -> dict[str, str]:
    if isinstance(raw_image_map, dict):
        return {str(k): str(v) for k, v in raw_image_map.items() if isinstance(v, str) and v.strip()}

    if isinstance(raw_image_map, list):
        normalized = {}
        for item in raw_image_map:
            if not isinstance(item, dict):
                continue
            idx = item.get("idx")
            url = item.get("url")
            if idx is None or not isinstance(url, str) or not url.strip():
                continue
            normalized[str(idx)] = url
        return normalized

    return {}


def _build_context_and_registry(docs) -> tuple[str, dict[str, str]]:
    image_registry: dict[str, str] = {}
    parts: list[str] = []

    for doc_idx, doc in enumerate(docs):
        metadata = getattr(doc, "metadata", {}) or {}
        source = metadata.get("url") or metadata.get("source_url") or ""
        part = f"【来源】{source}\n{doc.page_content}"

        image_map = _normalize_image_map(metadata.get("image_map"))
        if image_map:
            docid = _stable_docid(metadata, doc_idx)
            placeholders = []
            for idx, img_url in image_map.items():
                placeholder = f"[[IMG:{docid}:{idx}]]"
                image_registry[placeholder] = img_url
                placeholders.append(placeholder)

            placeholders_text = "\n".join(f"- {p}" for p in placeholders)
            part += f"\n\n【图片占位符】\n{placeholders_text}"

        parts.append(part)

    return "\n\n".join(parts), image_registry

@timing_decorator
def generate_node(state: RagState):
    image_registry = {}
    if state.get("web_answer"):
        context = state["web_answer"]
    else:
        docs = (
                state.get("ranked_docs") or
                state.get("all_retrieved_docs") or
                state["retrieved_docs"]
        )
        context, image_registry = _build_context_and_registry(docs)
    res = generate_chain.invoke({
        "messages": state["messages"],
        "question": state["messages"][-1].content,
        "context": context
         })
    return {"messages": [res], "context": context, "image_registry": image_registry}

chat_prompt = ChatPromptTemplate.from_messages([
    ("system", """## 角色定位
你是一个 ModelScope (魔搭社区) 的官方智能助手，名字叫“魔搭小助手”。你的风格是：**专业、亲切、高效、充满技术热情**。

## 核心任务
1. **日常互动**：处理打招呼、感谢、心情分享等社交辞令。
2. **身份宣讲**：当用户问“你是谁”或“你能做什么”时，告知用户你是 ModelScope 专门负责答疑的 AI 助手。
3. **技术引流**：
   - 如果用户的问题虽然属于 AI 领域但过于宽泛（如“什么是大模型？”），请给出简洁通俗的解释。
   - 适时引导用户：“如果您有具体的代码报错、模型下载或 SWIFT 微调问题，可以直接问我，我会为您检索魔搭官方文档。”

## 行为准则
- **严禁幻觉**：不要虚构 ModelScope 不存在的活动、功能或链接。
- **简洁有力**：闲聊不宜长篇大论，尽快解决用户非技术性的疑惑。
- **语言风格**：多使用“哈喽”、“亲”、“希望能帮到你”等亲切词汇，但保持专业底色。

## 典型场景回复建议
- **问候**：“哈喽！我是魔搭小助手，很高兴见到你。今天有什么我可以帮你的吗？”
- **能力说明**：“我可以帮你查询魔搭社区的模型使用方法、SWIFT 微调教程，或者帮你解决 SDK 安装中的报错。”
- **遇到无法回答的非技术问题**：“这个问题难倒我了，不如我们聊聊模型微调或者魔搭上的热门模型吧？”
"""),
    MessagesPlaceholder("messages"),
    ("human", "{question}"),
])
chat_chain = chat_prompt | get_llm("chat_generate")
def chat_node(state: RagState):
    print("🤔 进入chat节点...")
    res = chat_chain.invoke({
        "messages": state["messages"],
        "question": state["messages"][-1].content
    })
    return {"messages": [res], "context": ""}