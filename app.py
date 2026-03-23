import gradio as gr
import uuid
import logging
import os
from dotenv import load_dotenv
from langchain_core.messages import AIMessageChunk

# 在应用启动时加载 .env，便于本地开发通过环境变量配置密钥
load_dotenv()

from src.graph import create_graph
from src.feedback.store import save_feedback

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RagAssistant")

try:
    graph = create_graph()
except Exception as e:
    logger.error(f"Graph 初始化失败: {e}", exc_info=True)


WELCOME_MESSAGE = {
    "role": "assistant",
    "content": "👋 您好！我是 **魔搭社区答疑助手**。\n\n我可以帮您解答关于 ModelScope 平台的使用问题、模型部署教程以及代码实现建议。您可以试着问我：\n- *如何快速部署 Qwen2.5 模型？*\n- *魔搭的免费 GPU 算力如何申请？*\n- *帮我写一个加载数据集的 Python 脚本。*"
}

def generate_session_id():
    return str(uuid.uuid4())


def format_history_for_langchain(gradio_history):
    messages = []
    for msg in gradio_history:
        if "<svg" not in msg["content"]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    if len(messages) > 0 and messages[0]["content"] == WELCOME_MESSAGE["content"]:
        return messages[1:]

    if len(messages) > 8:
        messages = messages[-8:]
    return messages


def add_user_message(user_input, history):
    if not user_input.strip():
        return history, user_input

    history.append({"role": "user", "content": user_input})
    return history, ""


def bot_response(history, session_id):
    if not history or history[-1]["role"] != "user":
        yield history
        return

    user_message = history[-1]["content"]
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


def record_feedback(history, feedback_type):
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

    # 生成唯一ID和保存反馈
    message_id = str(uuid.uuid4())[:8]
    user_input = last_user_msg.get("content", "")
    assistant_response = last_assistant_msg.get("content", "")

    try:
        save_feedback(message_id, user_input, assistant_response, feedback_type)

        # 在消息后追加反馈成功提示
        feedback_indicator = "✅ 感谢反馈！" if feedback_type == "up" else "✅ 反馈已记录，我们会改进！"
        history[-1]["content"] += f"\n\n<small style='color: #9ca3af; margin-top: 8px;'>{feedback_indicator}</small>"

        return history, f"反馈成功 (ID: {message_id})"

    except Exception as e:
        logger.error(f"保存反馈失败: {e}", exc_info=True)
        return history, f"反馈保存失败: {str(e)}"
def reset_chat():
    """重置逻辑：恢复初始欢迎消息，并生成新的 session_id"""
    # 返回欢迎消息列表和新的 UUID
    return [WELCOME_MESSAGE], generate_session_id()

def toggle_feedback_buttons(show, history):
    """根据对话状态切换反馈按钮的可见性"""
    # 只有在有实际对话内容时才显示按钮
    has_conversation = len(history) > 1 if history else False
    should_show = show and has_conversation
    return gr.update(visible=should_show), should_show

custom_css = """
/* 基础容器优化 */
.gradio-container {
    height: 90vh !important;
    max-height: 850px !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
}

.main-container {
    height: 100% !important;
    display: flex !important;
    flex-direction: column !important;
    max-width: 1000px !important; /* 稍微加宽一点 */
    margin: 0 auto !important;
    background: #f9fafb !important; /* 极简浅灰背景 */
}

/* 聊天区域滚动条美化 */
.chatbot-area {
    flex-grow: 1 !important;
    overflow-y: auto !important;
    padding: 10px !important;
}
.chatbot-area::-webkit-scrollbar {
    width: 6px;
}
.chatbot-area::-webkit-scrollbar-thumb {
    background: #e5e7eb;
    border-radius: 10px;
}

/* 气泡深度优化 */
.message-wrap .message {
    padding: 12px 18px !important;
    font-size: 15px !important;
    line-height: 1.6 !important;
    border-radius: 16px !important;
    margin-bottom: 8px !important;
    transition: all 0.2s ease;
}

/* 修改用户气泡颜色为淡粉色 */
.message-wrap .user {
    background: linear-gradient(135deg, #FFD1DC 0%, #FAD7E4 100%) !important;
    color: #333 !important;
    border: none !important;
    box-shadow: 0 4px 12px rgba(255, 209, 220, 0.2) !important;
}


/* 机器人气泡 */
.message-wrap .bot {
    background: white !important;
    border: 1px solid #f3f4f6 !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
}

/* 输入区域美化 */
.input-area {
    padding: 15px 20px !important;
    background: white !important;
    border-top: 1px solid #f3f4f6 !important;
}

.custom-input-box {
    border: 2px solid #f3f4f6 !important;
    border-radius: 28px !important;
    transition: border-color 0.3s ease, box-shadow 0.3s ease;
    background: #ffffff !important;
}

.custom-input-box:focus-within {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
}

/* 按钮样式微调 */
.send-btn {
    border-radius: 20px !important;
    font-weight: 600 !important;
}

.clear-btn {
    border: none !important;
    background: transparent !important;
    color: #9ca3af !important;
    transition: color 0.2s !important;
}
.clear-btn:hover {
    color: #ef4444 !important;
}
.example-container {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 0 20px 10px 20px;
    background: white;
}

/* 快捷按钮样式 */
.example-btn {
    background: #f3f4f6 !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 20px !important;
    padding: 4px 12px !important;
    font-size: 13px !important;
    color: #4b5563 !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    min-width: auto !important;
    width: auto !important;
}

.example-btn:hover {
    background: #e5e7eb !important;
    border-color: #d1d5db !important;
    color: #1f2937 !important;
}
.message-wrap .message {
    min-height: 40px !important; /* 确保气泡有足够高度显示动画 */
    display: flex !important;
    align-items: center !important;
}
.feedback-container {
    display: flex;
    gap: 8px;
    margin-top: 8px;
    padding: 4px;
    border-radius: 8px;
    background: #f3f4f6;
    justify-content: center;
}

.feedback-btn {
    padding: 4px 12px;
    font-size: 13px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s ease;
    min-width: auto;
    width: auto;
}

.feedback-btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
"""

# --- 4. 优化后的界面构建 ---
with gr.Blocks(title="魔搭社区答疑助手", css=custom_css, theme=gr.themes.Soft(), fill_height=True) as demo:
    session_state = gr.State(generate_session_id)
    button_visibility = gr.State(False)  # False 表示隐藏，True 表示显示
    feedback_message = gr.Textbox(visible=False)  # 隐藏的状态消息

    with gr.Column(elem_classes="main-container"):
        gr.HTML("""
            <div style="padding: 16px; border-bottom: 1px solid #f3f4f6;">
                <h2 style="margin:0; font-size:18px; color:#1f2937; font-weight:700; display:flex; align-items:center; gap:8px;">
                    <span style="background:#6366f1; width:8px; height:18px; border-radius:4px; display:inline-block;"></span>
                    魔搭社区答疑助手
                </h2>
            </div>
        """)

        chatbot = gr.Chatbot(
            value=[WELCOME_MESSAGE],
            elem_classes="chatbot-area",
            show_label=False,
            avatar_images=("./assets/用户.svg", "./assets/机器人.svg"),
            show_copy_button=True,
            sanitize_html=False,
            type="messages"
        )

        # 反馈按钮区域
        with gr.Row(elem_classes="feedback-area", visible=False) as feedback_row:
            feedback_up_btn = gr.Button("👍 有帮助", scale=1, min_width=100)
            feedback_down_btn = gr.Button("👎 没帮助", scale=1, min_width=100)
            feedback_status = gr.Textbox(
                label="反馈状态",
                interactive=False,
                visible=False
            )

        # 输入区域
        with gr.Column(elem_classes="input-area"):
            with gr.Row(elem_classes="custom-input-box"):
                clear_btn = gr.Button("🗑️", elem_classes="clear-btn", scale=1, min_width=40)
                msg_input = gr.Textbox(
                    show_label=False,
                    placeholder="输入您的问题，例如：如何部署 Qwen 模型？",
                    container=False,
                    scale=10,
                    autofocus=True,
                    lines=1
                )
                submit_btn = gr.Button("发送", variant="primary", elem_classes="send-btn", scale=2, min_width=80)

            gr.Markdown("Tip: 点击 🗑️ 可清空对话历史", elem_id="tip-text", visible=True)

    # --- 事件绑定 ---
    msg_input.submit(
        fn=add_user_message,
        inputs=[msg_input, chatbot],
        outputs=[chatbot, msg_input],
        queue=False
    ).then(
        fn=bot_response,
        inputs=[chatbot, session_state],
        outputs=[chatbot]
    ).then(
        fn=toggle_feedback_buttons,
        inputs=[gr.State(True), chatbot],
        outputs=[feedback_row, button_visibility]
    )

    submit_btn.click(
        fn=add_user_message,
        inputs=[msg_input, chatbot],
        outputs=[chatbot, msg_input],
        queue=False
    ).then(
        fn=bot_response,
        inputs=[chatbot, session_state],
        outputs=[chatbot]
    ).then(
        fn=toggle_feedback_buttons,
        inputs=[gr.State(True), chatbot],
        outputs=[feedback_row, button_visibility]
    )

    # 反馈按钮事件
    feedback_up_btn.click(
        fn=record_feedback,
        inputs=[chatbot, gr.State("up")],
        outputs=[chatbot, feedback_status],
        queue=False
    ).then(
        fn=toggle_feedback_buttons,
        inputs=[gr.State(False), chatbot],
        outputs=[feedback_row, button_visibility]
    )

    feedback_down_btn.click(
        fn=record_feedback,
        inputs=[chatbot, gr.State("down")],
        outputs=[chatbot, feedback_status],
        queue=False
    ).then(
        fn=toggle_feedback_buttons,
        inputs=[gr.State(False), chatbot],
        outputs=[feedback_row, button_visibility]
    )

    clear_btn.click(
        fn=reset_chat,
        inputs=None,
        outputs=[chatbot, session_state],
        queue=False
    ).then(
        fn=lambda: gr.update(visible=False),
        inputs=None,
        outputs=[feedback_row]
    ).then(
        fn=lambda: False,
        inputs=None,
        outputs=[button_visibility]
    )

if __name__ == "__main__":
    demo.queue(max_size=20)
    server_name = os.getenv("GRADIO_SERVER_NAME", "127.0.0.1")
    server_port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    inbrowser = os.getenv("GRADIO_INBROWSER", "1").lower() not in {"0", "false", "no"}
    print(f"🌐 Gradio URL: http://{server_name}:{server_port}")
    demo.launch(server_name=server_name, server_port=server_port, inbrowser=inbrowser)