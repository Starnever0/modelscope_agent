from src.graph_routes import route_after_router, route_after_decompose


def test_route_after_router_to_chat_node():
    state = {"datasource": "chat"}
    assert route_after_router(state) == "chat_node"


def test_route_after_router_to_decompose_node():
    state = {"datasource": "docs"}
    assert route_after_router(state) == "decompose_query_node"


def test_route_after_decompose_parallel_path():
    state = {"sub_questions": ["q1", "q2"]}
    assert route_after_decompose(state) == "parallel_retrieve_node"


def test_route_after_decompose_simple_path():
    state = {"sub_questions": None}
    assert route_after_decompose(state) == "retrieve_docs_node"
