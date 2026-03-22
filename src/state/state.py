from typing import Annotated, Optional, List

from langchain_core.documents import Document
from langgraph.graph import MessagesState


class RagState(MessagesState):
    rewritten_query: str
    datasource: str
    retrieved_docs: list
    loop_step: Annotated[int, lambda x, y: x + y]
    web_answer: list
    context: str
    sub_questions: Optional[List[str]]
    all_retrieved_docs: Optional[List[Document]]
    ranked_docs: Optional[List[Document]]