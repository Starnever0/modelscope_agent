import json
from datetime import datetime

from src.feedback.store import get_feedback_file_path, save_feedback


def test_get_feedback_file_path():
    now = datetime(2026, 3, 22, 10, 0, 0)
    path = get_feedback_file_path("./feedback_data", now)
    assert path.endswith("feedback_2026-03-22.json")


def test_save_feedback_appends_records(tmp_path):
    now = datetime(2026, 3, 22, 10, 0, 0)

    save_feedback(
        message_id="a1",
        user_input="u1",
        assistant_response="r1",
        feedback_type="up",
        feedback_dir=str(tmp_path),
        now=now,
    )
    save_feedback(
        message_id="a2",
        user_input="u2",
        assistant_response="r2",
        feedback_type="down",
        feedback_dir=str(tmp_path),
        now=now,
    )

    feedback_file = tmp_path / "feedback_2026-03-22.json"
    with open(feedback_file, "r", encoding="utf-8") as f:
        payload = json.load(f)

    assert len(payload) == 2
    assert payload[0]["id"] == "a1"
    assert payload[1]["id"] == "a2"
