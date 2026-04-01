import logging
import os
import re
import uuid

import gradio as gr
from dotenv import load_dotenv
from langchain_core.messages import AIMessageChunk

from src.feedback.store import save_feedback
from src.graph import create_graph

# 在应用启动时加载 .env，便于本地开发通过环境变量配置密钥
load_dotenv()

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("RagAssistant")

try:
    graph = create_graph()
except Exception as e:
    logger.error(f"Graph 初始化失败: {e}", exc_info=True)
    graph = None

WELCOME_MESSAGE = {
    "role": "assistant",
    "content": (
        "您好，欢迎来到 **魔搭社区答疑助手**。\n\n"
        "我会尽量用清晰、易执行的方式回答你的问题，也会在必要时提醒不确定项。你可以直接问：\n"
        "- *如何快速部署 Qwen2.5 模型？*\n"
        "- *魔搭的免费 GPU 算力如何申请？*\n"
        "- *帮我写一个加载数据集的 Python 脚本。*"
    ),
}

QUICK_PROMPTS = [
    "我想在本地快速部署 Qwen2.5，给我最短路径步骤",
    "新手第一次用魔搭，先做哪三件事最有效？",
    "帮我对比 API 调用和本地部署的选型",
    "如何定位模型推理慢的问题？给排查顺序",
]

INLINE_FEEDBACK_HTML = (
    "<div class='inline-feedback' data-feedback='actions'>"
        "<button type='button' class='inline-feedback-btn' data-feedback-type='up'>👍 有帮助</button>"
        "<button type='button' class='inline-feedback-btn' data-feedback-type='down'>👎 待改进</button>"
    "</div>"
)

INLINE_FEEDBACK_JS = """
() => {
    if (window.__inlineFeedbackBound) {
        return;
    }
    window.__inlineFeedbackBound = true;

    document.addEventListener('click', (event) => {
        const btn = event.target.closest('.inline-feedback-btn');
        if (!btn) {
            return;
        }
        event.preventDefault();
        const feedbackType = btn.getAttribute('data-feedback-type');
        const triggerId = feedbackType === 'up' ? 'feedback_up_trigger' : 'feedback_down_trigger';
        const trigger = document.getElementById(triggerId);
        if (trigger) {
            trigger.click();
        }
    });
}
"""

INLINE_FEEDBACK_PATTERN = re.compile(r"<div class='inline-feedback'.*?</div>", re.S)
INLINE_FEEDBACK_ACK_PATTERN = re.compile(r"<small class='feedback-indicator'.*?</small>", re.S)


def generate_session_id() -> str:
    return str(uuid.uuid4())


def format_history_for_langchain(gradio_history: list[dict]) -> list[dict]:
    messages = []
    for msg in gradio_history:
        if "<svg" not in msg["content"]:
            clean_content = INLINE_FEEDBACK_PATTERN.sub("", msg["content"])
            clean_content = INLINE_FEEDBACK_ACK_PATTERN.sub("", clean_content)
            messages.append({"role": msg["role"], "content": clean_content})

    if len(messages) > 0 and messages[0]["content"] == WELCOME_MESSAGE["content"]:
        return messages[1:]

    if len(messages) > 8:
        messages = messages[-8:]
    return messages


def add_user_message(user_input: str, history: list[dict]):
    if not user_input.strip():
        return history, user_input

    history.append({"role": "user", "content": user_input})
    return history, ""


def bot_response(history: list[dict], session_id: str):
    if not history or history[-1]["role"] != "user":
        yield history
        return

    langchain_messages = format_history_for_langchain(history)

    inputs = {"messages": langchain_messages}
    config = {"configurable": {"thread_id": session_id}}

    full_response = ""
    try:
        if graph is None:
            raise RuntimeError("Graph 未初始化")

        history.append({"role": "assistant", "content": ""})

        for chunk in graph.stream(inputs, config, stream_mode="messages"):
            if isinstance(chunk[0], AIMessageChunk):
                new_content = chunk[0].content
                full_response += new_content
                history[-1]["content"] = full_response
                yield history

    except Exception as e:
        logger.error(f"异常: {str(e)}", exc_info=True)
        friendly_error = "😔 服务繁忙，请稍后重试。"
        history[-1]["content"] = full_response + f"\n\n---\n*{friendly_error}*"
        yield history


def record_feedback(history: list[dict], feedback_type: str):
    """
    处理用户反馈点击事件
    feedback_type: "up" 或 "down"
    """
    if not history or len(history) < 2:
        return history, "反馈失败：没有对话记录"

    # 获取最后一对对话（用户问题 + 助手回答）
    last_assistant_msg = history[-1]
    last_user_msg = history[-2] if len(history) >= 2 else None

    if last_assistant_msg["role"] != "assistant" or not last_user_msg:
        return history, "反馈失败：对话格式错误"

    if "feedback-indicator" in last_assistant_msg.get("content", ""):
        return history, "反馈已记录"

    message_id = str(uuid.uuid4())[:8]
    user_input = last_user_msg.get("content", "")
    assistant_response = last_assistant_msg.get("content", "")
    assistant_response = INLINE_FEEDBACK_PATTERN.sub("", assistant_response)
    assistant_response = INLINE_FEEDBACK_ACK_PATTERN.sub("", assistant_response)
    assistant_response = assistant_response.strip()

    try:
        save_feedback(message_id, user_input, assistant_response, feedback_type)

        feedback_indicator = "✅ 感谢反馈！"
        content_without_buttons = INLINE_FEEDBACK_PATTERN.sub("", history[-1]["content"])
        content_without_buttons = INLINE_FEEDBACK_ACK_PATTERN.sub("", content_without_buttons)
        history[-1]["content"] = (
            f"{content_without_buttons}\n\n"
            f"<small class='feedback-indicator' style='color: #6f8091; margin-top: 8px;'>{feedback_indicator}</small>"
        )

        return history, f"反馈成功 (ID: {message_id})"

    except Exception as e:
        logger.error(f"保存反馈失败: {e}", exc_info=True)
        return history, f"反馈保存失败: {str(e)}"


def reset_chat():
    """重置逻辑：恢复初始欢迎消息，并生成新的 session_id。"""
    return [WELCOME_MESSAGE], generate_session_id()


def toggle_feedback_buttons(show: bool, history: list[dict]):
    """根据对话状态切换反馈按钮的可见性。"""
    has_conversation = len(history) > 1 if history else False
    should_show = show and has_conversation
    return gr.update(visible=should_show), should_show


def append_inline_feedback(history: list[dict]):
    if not history:
        return history

    if history[-1].get("role") != "assistant":
        return history

    content = history[-1].get("content", "")
    if "data-feedback='actions'" in content or "feedback-indicator" in content:
        return history

    history[-1]["content"] = f"{content}\n\n{INLINE_FEEDBACK_HTML}"
    return history


def quick_send(prompt: str, history: list[dict]):
    return add_user_message(prompt, history)


custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700&display=swap');

:root {
    --bg-main: #eef4f9;
    --bg-panel: #f8fbff;
    --surface: #ffffff;
    --line: #d3deea;
    --text-main: #122235;
    --text-sub: #4f6680;
    --brand: #0d67b2;
    --chip: #edf4fb;
    --chip-hover: #e1eef9;
}

.gradio-container {
    height: 100vh !important;
    padding: 12px 0 !important;
    box-sizing: border-box !important;
    overflow: hidden !important;
    background:
        radial-gradient(circle at 8% 10%, rgba(13, 103, 178, 0.06), transparent 34%),
        radial-gradient(circle at 92% 12%, rgba(24, 126, 197, 0.06), transparent 28%),
        var(--bg-main) !important;
    font-family: "Noto Sans SC", "Manrope", "Segoe UI", sans-serif !important;
}

.main-container {
    width: min(1360px, 98vw) !important;
    height: 100% !important;
    margin: 0 auto !important;
    display: flex !important;
    flex-direction: column !important;
    min-height: 0 !important;
    border: 1px solid var(--line) !important;
    border-radius: 20px !important;
    overflow: hidden !important;
    background: linear-gradient(180deg, rgba(249, 252, 255, 0.94), rgba(255, 255, 255, 0.98)) !important;
    box-shadow: 0 16px 40px rgba(14, 39, 67, 0.08) !important;
}

.chat-shell {
    flex: 1 !important;
    min-height: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    padding: 8px 10px 0 10px !important;
    gap: 4px !important;
}

.top-header {
    padding: 10px 16px !important;
    border-bottom: 1px solid var(--line) !important;
    background: var(--bg-panel) !important;
}

.top-header .title {
    margin: 0 !important;
    font-size: 18px !important;
    font-weight: 700 !important;
    color: var(--text-main) !important;
}

.top-header .subtitle {
    margin-top: 1px !important;
    font-size: 11px !important;
    color: var(--text-sub) !important;
}

.chatbot-area {
    flex: 1 1 auto !important;
    min-height: 0 !important;
    padding: 14px 18px !important;
    overflow: hidden !important;
    background: rgba(255, 255, 255, 0.88) !important;
    border: 1px solid var(--line) !important;
    border-radius: 16px !important;
}

.chatbot-area .message-wrap {
    height: 100% !important;
    min-height: 0 !important;
    overflow-y: auto !important;
}

.chatbot-area > div,
.chatbot-area .wrap,
.chatbot-area .bubble-wrap {
    min-height: 0 !important;
    max-height: 100% !important;
    overflow: visible !important;
}

.dock-area {
    flex: 0 0 auto !important;
    display: grid !important;
    grid-template-rows: auto auto auto !important;
    gap: 4px !important;
    align-content: end !important;
    margin: auto 0 0 0 !important;
    padding: 0 !important;
    min-height: 0 !important;
}

.chatbot-area::-webkit-scrollbar {
    width: 6px;
}

.chatbot-area::-webkit-scrollbar-thumb {
    background: #b9c7d7;
    border-radius: 10px;
}

.message-wrap .message {
    padding: 12px 16px !important;
    font-size: 14px !important;
    line-height: 1.55 !important;
    border-radius: 12px !important;
    margin-bottom: 6px !important;
    color: var(--text-main) !important;
    min-height: 36px !important;
    display: flex !important;
    align-items: center !important;
    max-width: 92% !important;
}

.message-wrap .user {
    background: linear-gradient(135deg, #dcecf9 0%, #d4e8f8 100%) !important;
    border: 1px solid #c1d9ec !important;
}

.message-wrap .bot {
    background: #ffffff !important;
    border: 1px solid #dce7f2 !important;
}

.input-area {
    margin-top: 0 !important;
    padding: 0 !important;
}

.custom-input-box {
    border: 1px solid #cfdae6 !important;
    border-radius: 999px !important;
    background: #ffffff !important;
    padding: 5px 7px !important;
    box-shadow: 0 2px 10px rgba(15, 40, 66, 0.08) !important;
}

.custom-input-box:focus-within {
    border-color: #95b7d6 !important;
    box-shadow: 0 4px 14px rgba(15, 40, 66, 0.12) !important;
}

.custom-input-box textarea,
.custom-input-box input {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
}

.send-btn {
    border-radius: 999px !important;
    background: var(--brand) !important;
    border: 1px solid var(--brand) !important;
    font-weight: 600 !important;
}

.clear-btn {
    border: none !important;
    border-radius: 999px !important;
    background: transparent !important;
    color: #5a6f85 !important;
}

.clear-btn:hover {
    background: #f3f8fc !important;
}

.example-container {
    display: flex;
    flex-wrap: nowrap;
    gap: 6px;
    margin-top: 0;
    padding: 0 !important;
    overflow-x: auto !important;
    overflow-y: hidden !important;
    white-space: nowrap !important;
}

.example-container::-webkit-scrollbar {
    height: 4px;
}

.example-container::-webkit-scrollbar-thumb {
    background: #c4d7e9;
    border-radius: 999px;
}

.example-btn {
    background: var(--chip) !important;
    border: 1px solid #c8dff1 !important;
    border-radius: 999px !important;
    padding: 5px 12px !important;
    font-size: 11px !important;
    color: #1a4f7d !important;
    cursor: pointer !important;
    min-width: auto !important;
    width: auto !important;
}

.example-btn:hover {
    background: var(--chip-hover) !important;
    border-color: #a9cae6 !important;
}

.feedback-area {
    display: flex;
    gap: 6px;
    margin: 0 !important;
    padding: 0;
    border-radius: 8px;
    background: transparent;
    justify-content: center;
}

.inline-feedback {
    margin-top: 8px;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.inline-feedback-btn {
    background: #edf6fe;
    border: 1px solid #c8dff1;
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 12px;
    color: #1a4f7d;
    cursor: pointer;
}

.inline-feedback-btn:hover {
    background: #e2f0fd;
}

.feedback-btn {
    padding: 4px 10px;
    font-size: 12px;
    border: 1px solid #c8dff1;
    border-radius: 6px;
    cursor: pointer;
    background: #ffffff;
    min-width: auto;
    width: auto;
}

.feedback-btn:hover {
    background: #edf6fe;
}

.feedback-trigger {
    display: none !important;
}

.tip-text {
    margin: 0 !important;
    color: #617791 !important;
    font-size: 12px !important;
}

@media (max-width: 1024px) {
    .main-container {
        width: 98vw !important;
        height: 100% !important;
        margin: 0 auto !important;
        border-radius: 14px !important;
    }

    .chat-shell {
        display: flex !important;
        flex-direction: column !important;
        padding: 8px 8px 0 8px !important;
        gap: 4px !important;
    }

    .dock-area {
        flex-basis: auto !important;
        align-content: end !important;
    }

    .chatbot-area {
        border-radius: 12px !important;
    }
}
"""


with gr.Blocks(title="魔搭社区答疑助手", css=custom_css, js=INLINE_FEEDBACK_JS, theme=gr.themes.Soft(), fill_height=True) as demo:
    session_state = gr.State(generate_session_id)

    with gr.Column(elem_classes="main-container"):
        gr.HTML(
            """
            <div class="top-header">
                <h2 class="title">魔搭社区答疑助手</h2>
                <div class="subtitle">社区伙伴模式 | 宽屏沉浸式会话</div>
            </div>
            """
        )

        with gr.Column(elem_classes="chat-shell"):
            chatbot = gr.Chatbot(
                value=[WELCOME_MESSAGE],
                elem_classes="chatbot-area",
                show_label=False,
                avatar_images=("./assets/用户.svg", "./assets/机器人.svg"),
                show_copy_button=True,
                sanitize_html=False,
                type="messages",
            )

            feedback_up_trigger = gr.Button("feedback_up", elem_id="feedback_up_trigger", elem_classes="feedback-trigger")
            feedback_down_trigger = gr.Button(
                "feedback_down", elem_id="feedback_down_trigger", elem_classes="feedback-trigger"
            )
            feedback_status = gr.Textbox(label="反馈状态", interactive=False, visible=False)

            with gr.Column(elem_classes="dock-area"):
                with gr.Row(elem_classes="example-container"):
                    qp1 = gr.Button("部署最短路径", elem_classes="example-btn", min_width=10)
                    qp2 = gr.Button("新手三步", elem_classes="example-btn", min_width=10)
                    qp3 = gr.Button("方案对比", elem_classes="example-btn", min_width=10)
                    qp4 = gr.Button("性能排查", elem_classes="example-btn", min_width=10)

                with gr.Column(elem_classes="input-area"):
                    with gr.Row(elem_classes="custom-input-box"):
                        clear_btn = gr.Button("清空", elem_classes="clear-btn", scale=1, min_width=52)
                        msg_input = gr.Textbox(
                            show_label=False,
                            placeholder="发送消息，例如：如何在 ModelScope 上部署 Qwen 模型？",
                            container=False,
                            scale=10,
                            autofocus=True,
                            lines=1,
                        )
                        submit_btn = gr.Button("发送", variant="primary", elem_classes="send-btn", scale=2, min_width=84)

    msg_input.submit(
        fn=add_user_message,
        inputs=[msg_input, chatbot],
        outputs=[chatbot, msg_input],
        queue=False,
    ).then(
        fn=bot_response,
        inputs=[chatbot, session_state],
        outputs=[chatbot],
    ).then(
        fn=append_inline_feedback,
        inputs=[chatbot],
        outputs=[chatbot],
    )

    submit_btn.click(
        fn=add_user_message,
        inputs=[msg_input, chatbot],
        outputs=[chatbot, msg_input],
        queue=False,
    ).then(
        fn=bot_response,
        inputs=[chatbot, session_state],
        outputs=[chatbot],
    ).then(
        fn=append_inline_feedback,
        inputs=[chatbot],
        outputs=[chatbot],
    )

    qp1.click(fn=lambda: QUICK_PROMPTS[0], inputs=None, outputs=[msg_input], queue=False).then(
        fn=quick_send,
        inputs=[msg_input, chatbot],
        outputs=[chatbot, msg_input],
        queue=False,
    ).then(
        fn=bot_response,
        inputs=[chatbot, session_state],
        outputs=[chatbot],
    ).then(
        fn=append_inline_feedback,
        inputs=[chatbot],
        outputs=[chatbot],
    )

    qp2.click(fn=lambda: QUICK_PROMPTS[1], inputs=None, outputs=[msg_input], queue=False).then(
        fn=quick_send,
        inputs=[msg_input, chatbot],
        outputs=[chatbot, msg_input],
        queue=False,
    ).then(
        fn=bot_response,
        inputs=[chatbot, session_state],
        outputs=[chatbot],
    ).then(
        fn=append_inline_feedback,
        inputs=[chatbot],
        outputs=[chatbot],
    )

    qp3.click(fn=lambda: QUICK_PROMPTS[2], inputs=None, outputs=[msg_input], queue=False).then(
        fn=quick_send,
        inputs=[msg_input, chatbot],
        outputs=[chatbot, msg_input],
        queue=False,
    ).then(
        fn=bot_response,
        inputs=[chatbot, session_state],
        outputs=[chatbot],
    ).then(
        fn=append_inline_feedback,
        inputs=[chatbot],
        outputs=[chatbot],
    )

    qp4.click(fn=lambda: QUICK_PROMPTS[3], inputs=None, outputs=[msg_input], queue=False).then(
        fn=quick_send,
        inputs=[msg_input, chatbot],
        outputs=[chatbot, msg_input],
        queue=False,
    ).then(
        fn=bot_response,
        inputs=[chatbot, session_state],
        outputs=[chatbot],
    ).then(
        fn=append_inline_feedback,
        inputs=[chatbot],
        outputs=[chatbot],
    )

    feedback_up_trigger.click(
        fn=record_feedback,
        inputs=[chatbot, gr.State("up")],
        outputs=[chatbot, feedback_status],
        queue=False,
    )

    feedback_down_trigger.click(
        fn=record_feedback,
        inputs=[chatbot, gr.State("down")],
        outputs=[chatbot, feedback_status],
        queue=False,
    )

    clear_btn.click(
        fn=reset_chat,
        inputs=None,
        outputs=[chatbot, session_state],
        queue=False,
    )

if __name__ == "__main__":
    demo.queue(max_size=20)
    server_name = os.getenv("GRADIO_SERVER_NAME", "127.0.0.1")
    server_port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    inbrowser = os.getenv("GRADIO_INBROWSER", "1").lower() not in {"0", "false", "no"}
    print(f"🌐 Gradio URL: http://{server_name}:{server_port}")
    demo.launch(server_name=server_name, server_port=server_port, inbrowser=inbrowser)
