from langchain_community.chat_models import ChatTongyi


def get_normal_llm():
    return ChatTongyi(
        model="qwen-flash",
        extra_body={
            "enable_thinking": False
        },
        temprorature=0,
    )


def get_llm():
    return ChatTongyi(
        model="qwen3-max",
        streaming=True,
    )
