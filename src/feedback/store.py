import json
import os
from datetime import datetime
from typing import Optional


def get_feedback_file_path(feedback_dir: str, now: Optional[datetime] = None) -> str:
    dt = now or datetime.now()
    today = dt.strftime("%Y-%m-%d")
    return os.path.join(feedback_dir, f"feedback_{today}.json")


def save_feedback(
    message_id: str,
    user_input: str,
    assistant_response: str,
    feedback_type: str,
    feedback_dir: str = "./feedback_data",
    now: Optional[datetime] = None,
):
    dt = now or datetime.now()
    feedback_record = {
        "id": message_id,
        "timestamp": dt.isoformat(),
        "user_input": user_input,
        "assistant_response": assistant_response,
        "feedback_type": feedback_type,
    }

    os.makedirs(feedback_dir, exist_ok=True)
    feedback_file = get_feedback_file_path(feedback_dir, dt)

    feedbacks = []
    if os.path.exists(feedback_file):
        with open(feedback_file, "r", encoding="utf-8") as f:
            feedbacks = json.load(f)

    feedbacks.append(feedback_record)

    with open(feedback_file, "w", encoding="utf-8") as f:
        json.dump(feedbacks, f, ensure_ascii=False, indent=2)

    return feedback_record
