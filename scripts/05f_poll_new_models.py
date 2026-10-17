"""
Polls and downloads the 3 ad-hoc batch jobs added on top of the original
8 model/settings: gpt-6-astra (reasoning: low) and claude-opus-5
(thinking: off, thinking: on). State tracked in results/new_models_state.json.
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
STATE_PATH = os.path.join(ROOT, "results", "new_models_state.json")

JOBS = {
    "gpt-6-astra_reasoning-low": {
        "provider": "openai", "batch_id": "batch_6ad2c1e99adc8190b3422bf8f02b74d7",
        "out_path": os.path.join(ROOT, "results", "model_answers_v2_openai_gpt-6-astra_reasoning-low.json"),
        "model_id": "gpt-6-astra",
    },
    "opus5_thinking-off": {
        "provider": "anthropic", "batch_id": "msgbatch_01CJVuix6dSHW6kjhmbUK77H",
        "out_path": os.path.join(ROOT, "results", "model_answers_v2_claude-opus-5_thinking-off.json"),
        "model_id": "claude-opus-5",
    },
    "opus5_thinking-on": {
        "provider": "anthropic", "batch_id": "msgbatch_01KAP27LkaM55WZB8o2k2ouJ",
        "out_path": os.path.join(ROOT, "results", "model_answers_v2_claude-opus-5_thinking-on.json"),
        "model_id": "claude-opus-5",
    },
}


def save_openai_results(jsonl_text, model_id, setting_name, out_path):
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
        results.append({"id": qid, "category": q["category"], "question_id": q["question_id"],
                         "answer_key": q["answer_key"], "ground_truth_option": gt,
                         "model_raw_output": raw_text, "model_answer": letter if is_valid else "invalid",
                         "is_valid": is_valid, "is_correct": is_correct, "usage": usage})
    n_with_gt = sum(1 for r in results if r["ground_truth_option"] is not None)
    summary = {"model_id": model_id, "setting": setting_name, "via": "openai_batch_api",
               "n_valid_answers": n_valid, "n_with_ground_truth": n_with_gt, "n_correct": n_correct,
               "accuracy_overall_pct": 100.0 * n_correct / n_with_gt if n_with_gt else None, "results": results}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)


def save_anthropic_results(client, batch, model_id, setting_name, out_path):
    questions = {q["id"]: q for q in json.load(open(QUESTIONS_PATH, encoding="utf-8"))}
    results = []
    n_correct = n_valid = 0
    for entry in client.messages.batches.results(batch.id):
        qid = entry.custom_id
        q = questions[qid]
        raw_text = None
        usage = None
        if entry.result.type == "succeeded":
            msg = entry.result.message
            text_blocks = [b.text for b in msg.content if b.type == "text"]
            raw_text = text_blocks[-1] if text_blocks else None
            u = msg.usage
            usage = dict(input_tokens=u.input_tokens, output_tokens=u.output_tokens,
                         thinking_tokens=(u.output_tokens_details.thinking_tokens or 0) if u.output_tokens_details else 0)
        letter = api_lib.parse_letter(raw_text) if raw_text else None
        gt = q.get("ground_truth_option")
        is_valid = letter is not None
        is_correct = (letter == gt) if (is_valid and gt is not None) else False
        if is_valid:
            n_valid += 1
        if is_correct:
            n_correct += 1
        results.append({"id": qid, "category": q["category"], "question_id": q["question_id"],
                         "answer_key": q["answer_key"], "ground_truth_option": gt,
                         "model_raw_output": raw_text, "model_answer": letter if is_valid else "invalid",
                         "is_valid": is_valid, "is_correct": is_correct, "result_type": entry.result.type,
                         "usage": usage})
    n_with_gt = sum(1 for r in results if r["ground_truth_option"] is not None)
    summary = {"model_id": model_id, "setting": setting_name, "via": "anthropic_message_batches",
               "n_valid_answers": n_valid, "n_with_ground_truth": n_with_gt, "n_correct": n_correct,
               "accuracy_overall_pct": 100.0 * n_correct / n_with_gt if n_with_gt else None, "results": results}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)


def main():
    import openai
    import anthropic
    oc = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    ac = anthropic.Anthropic(api_key=os.environ["CLAUDE_API_KEY"])

    state = json.load(open(STATE_PATH, encoding="utf-8")) if os.path.exists(STATE_PATH) else {}

    all_done = True
    for name, job in JOBS.items():
        if state.get(name, {}).get("downloaded"):
            print(f"{name}: already downloaded.")
            continue
        if job["provider"] == "openai":
            batch = oc.batches.retrieve(job["batch_id"])
            print(f"{name}: status={batch.status} "
                  f"(completed={batch.request_counts.completed if batch.request_counts else '?'}/"
                  f"{batch.request_counts.total if batch.request_counts else '?'})")
            if batch.status == "completed" and batch.output_file_id:
                content = oc.files.content(batch.output_file_id)
                save_openai_results(content.text, job["model_id"], name, job["out_path"])
                state[name] = {"downloaded": True}
                print(f"  -> saved {job['out_path']}")
            elif batch.status in ("failed", "expired", "cancelled"):
                print(f"  -> BATCH {batch.status}!")
                all_done = False
            else:
                all_done = False
        else:
            batch = ac.messages.batches.retrieve(job["batch_id"])
            counts = batch.request_counts
            print(f"{name}: status={batch.processing_status} "
                  f"(succeeded={counts.succeeded} errored={counts.errored} processing={counts.processing})")
            if batch.processing_status == "ended":
                save_anthropic_results(ac, batch, job["model_id"], name, job["out_path"])
                state[name] = {"downloaded": True}
                print(f"  -> saved {job['out_path']}")
            else:
                all_done = False

    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

    if all_done:
        print("\nALL NEW MODEL BATCHES COMPLETE")
    else:
        print("\nStill waiting on one or more batches.")


if __name__ == "__main__":
    main()
