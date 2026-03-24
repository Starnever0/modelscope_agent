import argparse
import csv
import json
from pathlib import Path


def _write_jsonl(rows, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _repair_mojibake(text: str) -> str:
    if not text:
        return ""
    try:
        repaired = text.encode("gbk").decode("utf-8")
    except Exception:
        return text
    return repaired if repaired else text


def convert_feedback_csv(input_csv: str, output_jsonl: str):
    rows = []
    with open(input_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for idx, r in enumerate(reader, start=1):
            rows.append(
                {
                    "case_id": r.get("case_id") or f"feedback_{idx}",
                    "query": _repair_mojibake(r.get("问题") or r.get("query") or ""),
                    "bot_answer": _repair_mojibake(r.get("答疑机器人回答") or r.get("bot_answer") or ""),
                    "user_rating": r.get("用户评分") or r.get("user_rating"),
                    "user_feedback": _repair_mojibake(r.get("用户反馈") or r.get("user_feedback") or ""),
                    "dataset_type": "feedback",
                    "difficulty": r.get("difficulty") or "easy",
                    "expected_docids": [],
                    "tags": ["feedback"],
                }
            )
    _write_jsonl(rows, Path(output_jsonl))


def convert_qa_csv(input_csv: str, output_jsonl: str):
    rows = []
    with open(input_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        def _extract_compound_qa(row: dict) -> tuple[str, str]:
            for key in ("问题，答案", "问题,答案", "query，reference_answer", "query,reference_answer"):
                value = row.get(key)
                if not value:
                    continue
                if "，" in value:
                    q, a = value.split("，", 1)
                    return q.strip(), a.strip()
                if "," in value:
                    q, a = value.split(",", 1)
                    return q.strip(), a.strip()
            return "", ""

        for idx, r in enumerate(reader, start=1):
            raw_docids = r.get("expected_docids") or r.get("docids") or ""
            expected_docids = [x.strip() for x in raw_docids.split("|") if x.strip()]
            query = r.get("问题") or r.get("query") or r.get("question") or ""
            reference_answer = r.get("标准答案") or r.get("reference_answer") or r.get("答案") or r.get("answer") or ""

            # Compatibility for files where question and answer are merged in one column.
            if not query and not reference_answer:
                query, reference_answer = _extract_compound_qa(r)

            rows.append(
                {
                    "case_id": r.get("case_id") or f"qa_{idx}",
                    "query": _repair_mojibake(query),
                    "reference_answer": _repair_mojibake(reference_answer),
                    "expected_docids": expected_docids,
                    "dataset_type": "qa",
                    "difficulty": r.get("difficulty") or "easy",
                    "tags": [x.strip() for x in (r.get("tags") or "qa").split("|") if x.strip()],
                }
            )
    _write_jsonl(rows, Path(output_jsonl))


def main():
    parser = argparse.ArgumentParser(description="Convert CSV datasets to eval jsonl format")
    parser.add_argument("--mode", choices=["feedback", "qa"], required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    if args.mode == "feedback":
        convert_feedback_csv(args.input, args.output)
    else:
        convert_qa_csv(args.input, args.output)

    print(f"Converted {args.mode} dataset to {args.output}")


if __name__ == "__main__":
    main()
