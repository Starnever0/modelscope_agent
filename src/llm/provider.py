from src.llm.model_config import get_normal_llm, get_stream_llm


def get_llm(scene: str = "answer_generate"):
    # 保持兼容历史调用，统一走模型配置中心
    return get_stream_llm(scene=scene)


def get_normal_llm_for_scene(scene: str):
    return get_normal_llm(scene=scene)
