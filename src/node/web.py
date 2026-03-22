from langchain_community.tools import TavilySearchResults
from langchain_core.documents import Document
import os

from src.test import timing_decorator


@timing_decorator
def web_node(state):
    web_search_tool = TavilySearchResults(
        k=3,
        tavily_api_key=os.getenv("TAVILY_API_KEY")
    )
    res = web_search_tool.invoke({"query": state["rewritten_query"]})

    documents = []
    for item in res:
        doc = Document(
            page_content=item.get("content", ""),
            metadata={
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "score": item.get("score", 0),
                "source_type": "web"
            }
        )
        documents.append(doc)

    return {"retrieved_docs": documents}
