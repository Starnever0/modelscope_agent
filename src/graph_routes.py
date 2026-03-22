from src.state.state import RagState


def route_after_router(state: RagState) -> str:
    ds = state["datasource"]
    if ds == "chat":
        return "chat_node"
    return "decompose_query_node"


def route_after_decompose(state: RagState) -> str:
    if state["sub_questions"] is not None:
        return "parallel_retrieve_node"
    return "retrieve_docs_node"
