from langchain_tavily import TavilySearch
from langchain_core.documents import Document
import os
import json

from src.test import timing_decorator


@timing_decorator
def web_node(state):
    """
    Retrieve relevant web documents using Tavily search.
    
    Uses the langchain-tavily package (replaces deprecated langchain_community.tools.TavilySearchResults).
    Parses both string and dict formats from the search results.
    
    Returns a state with retrieved_docs list of Document objects.
    """
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    web_search_tool = TavilySearch(
        tavily_api_key=tavily_api_key
    )
    
    # TavilySearch.invoke() returns a string (JSON formatted)
    result = web_search_tool.invoke({"query": state["rewritten_query"]})

    documents = []
    
    # Parse the result which could be string or dict
    if isinstance(result, str):
        try:
            # Try to parse as JSON string
            parsed = json.loads(result)
            results_list = parsed.get("results", []) if isinstance(parsed, dict) else []
        except (json.JSONDecodeError, AttributeError):
            # If not JSON, treat the whole string as content
            results_list = [{"content": result}]
    elif isinstance(result, dict):
        # If already a dict, extract results
        results_list = result.get("results", [])
    elif isinstance(result, list):
        # If already a list, use it directly
        results_list = result
    else:
        results_list = []

    for item in results_list:
        # Handle both dict and string formats
        if isinstance(item, dict):
            page_content = item.get("content", "")
            title = item.get("title", "")
            url = item.get("url", "")
            score = item.get("score", 0)
        else:
            # Fallback for string format
            page_content = str(item)
            title = ""
            url = ""
            score = 0
        
        if page_content:  # Only create document if there's content
            doc = Document(
                page_content=page_content,
                metadata={
                    "title": title,
                    "url": url,
                    "score": score,
                    "source_type": "web"
                }
            )
            documents.append(doc)

    return {"retrieved_docs": documents}

