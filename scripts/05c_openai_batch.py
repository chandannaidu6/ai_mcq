"""
Step 5 (OpenAI answerer): uses the OpenAI Batch API (50% cheaper than
standard calls, per prices.json) for gpt-6-luna at two reasoning settings:
reasoning_effort="none" (the lowest value this model accepts -- "minimal"
is rejected; "none" measured 0 reasoning tokens in the cost-projection
test, i.e. genuinely off) and reasoning_effort="medium" (the "reasoning on"
comparison run).

Cost-projection test (05a_cost_projection.py) measured, on a real 20-question
sample, a projected FULL-SCALE cost of ~$0.05 (none) and ~$0.09 (medium) at
standard rates -- both settings stay far under the $9 Anthropic/OpenAI cap
even combined, so nothing needs to be skipped.

Usage:
    python 05c_openai_batch.py submit   # create & submit both batch jobs
    python 05c_openai_batch.py poll     # check status / download results when done
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dotenv import load_dotenv  # noqa: E402

ROOT = os.path.dirname(HERE)
load_dotenv(os.path.join(ROOT, ".env"))

import api_lib  # noqa: E402

QUESTIONS_PATH = os.path.join(ROOT, "results", "questions_v2_verified.json")
STATE_PATH = os.path.join(ROOT, "results", "openai_batch_state.json")
MODEL_ID = "gpt-6-luna"
SETTINGS = {
    "reasoning-none": "none",
    "reasoning-medium": "medium",
}


def load_state():
    if os.path.exists(STATE_PATH):
        return json.load(open(STATE_PATH, encoding="utf-8"))
    return {}


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def build_batch_file(questions, reasoning_effort, path):
    with open(path, "w", encoding="utf-8") as f:
        for q in questions:
            msg = api_lib.build_prompt_text(q)
            body = {
                "model": MODEL_ID,
                "max_completion_tokens": 1500 if reasoning_effort != "none" else 100,
                "reasoning_effort": reasoning_effort,
                "messages": [{"role": "user", "content": msg}],
            }
            line = {"custom_id": q["id"], "method": "POST", "url": "/v1/chat/completions", "body": body}
            f.write(json.dumps(line) + "\n")


def cmd_submit():
    import openai
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    questions = json.load(open(QUESTIONS_PATH, encoding="utf-8"))

    state = load_state()
    for setting_name, effort in SETTINGS.items():
        if setting_name in state and state[setting_name].get("batch_id"):
            print(f"{setting_name}: already submitted (batch_id={state[setting_name]['batch_id']}), skipping.")
            continue
        jsonl_path = os.path.join(ROOT, "pilot_data", f"openai_batch_{setting_name}.jsonl")
        build_batch_file(questions, effort, jsonl_path)
        print(f"Built {jsonl_path} ({len(questions)} requests)")

        upload = client.files.create(file=open(jsonl_path, "rb"), purpose="batch")
        batch = client.batches.create(
            input_file_id=upload.id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
            metadata={"setting": setting_name},
        )
        state[setting_name] = {"batch_id": batch.id, "input_file_id": upload.id, "status": batch.status,
                                "submitted_at": time.time()}
        save_state(state)
        print(f"{setting_name}: submitted batch {batch.id} (status={batch.status})")


def cmd_poll():
    import openai
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    state = load_state()
    if not state:
        print("No batches submitted yet. Run `submit` first.")
        return

    all_done = True
    for setting_name, info in state.items():
        if info.get("downloaded"):
            print(f"{setting_name}: already downloaded.")
            continue
        batch = client.batches.retrieve(info["batch_id"])
        print(f"{setting_name}: status={batch.status} "
              f"(completed={batch.request_counts.completed if batch.request_counts else '?'}/"
              f"{batch.request_counts.total if batch.request_counts else '?'})")
        info["status"] = batch.status
        if batch.status == "completed" and batch.output_file_id:
            content = client.files.content(batch.output_file_id)
            out_path = os.path.join(ROOT, "results", f"model_answers_v2_openai_gpt-6-luna_{setting_name}.json")
            save_batch_results(content.text, setting_name, out_path)
            info["downloaded"] = True
            info["out_path"] = out_path
            print(f"  -> saved {out_path}")
        elif batch.status in ("failed", "expired", "cancelled"):
            print(f"  -> batch {batch.status}! error_file_id={batch.error_file_id}")
            all_done = False
        else:
            all_done = False
    save_state(state)
    if all_done:
        print("\nAll OpenAI batches complete.")
    else:
        print("\nStill waiting on one or more batches. Re-run `poll` later.")


def save_batch_results(jsonl_text, setting_name, out_path):
    questions = {q["id"]: q for q in json.load(open(QUESTIONS_PATH, encoding="utf-8"))}
    results = []
    n_correct = n_valid = 0
    for line in jsonl_text.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        qid = row["custom_id"]
        q = questions[qid]
        resp_body = row.get("response", {}).get("body", {})
        choices = resp_body.get("choices", [])
        raw_text = choices[0]["message"]["content"] if choices else None
        letter = api_lib.parse_letter(raw_text) if raw_text else None
        gt = q.get("ground_truth_option")
        is_valid = letter is not None
        is_correct = (letter == gt) if (is_valid and gt is not None) else False
        if is_valid:
            n_valid += 1
        if is_correct:
            n_correct += 1
        usage = resp_body.get("usage", {})
        results.append({
            "id": qid, "category": q["category"], "question_id": q["question_id"],
            "answer_key": q["answer_key"], "ground_truth_option": gt,
            "model_raw_output": raw_text, "model_answer": letter if is_valid else "invalid",
            "is_valid": is_valid, "is_correct": is_correct, "usage": usage,
        })
    n_with_gt = sum(1 for r in results if r["ground_truth_option"] is not None)
    summary = {
        "model_id": MODEL_ID, "setting": setting_name, "via": "openai_batch_api",
        "n_valid_answers": n_valid, "n_with_ground_truth": n_with_gt, "n_correct": n_correct,
        "accuracy_overall_pct": 100.0 * n_correct / n_with_gt if n_with_gt else None,
        "results": results,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("submit", "poll"):
        print("Usage: 05c_openai_batch.py [submit|poll]")
        sys.exit(1)
    if sys.argv[1] == "submit":
        cmd_submit()
    else:
        cmd_poll()
