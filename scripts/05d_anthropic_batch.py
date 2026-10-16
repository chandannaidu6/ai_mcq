"""
Step 5 (Anthropic answerer): uses the Message Batches API (50% cheaper than
standard calls) for Claude Haiku 5.5 at two thinking settings.

Cost-projection test (20 real questions) measured:
  thinking=disabled:                  avg ~627 in / ~69 out tokens/question
                                       -> projected full-scale (1005) cost ~$0.10 standard
  thinking=adaptive, effort=high:     avg ~629 in / ~440 out tokens/question (incl. thinking)
                                       -> projected full-scale (1005) cost ~$0.28 standard
Both settings combined stay far under the $9 Anthropic cap (even at
non-batch rates), so nothing is skipped.

IMPORTANT caveat recorded in the final report: Claude Haiku is in the same
model family as the generator (Claude Sonnet 5), which may give it an
advantage other models don't have.

Usage:
    python 05d_anthropic_batch.py submit
    python 05d_anthropic_batch.py poll
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
STATE_PATH = os.path.join(ROOT, "results", "anthropic_batch_state.json")
MODEL_ID = "claude-haiku-5-5"
SETTINGS = {
    "thinking-off": dict(thinking={"type": "disabled"}, max_tokens=200),
    "thinking-on": dict(thinking={"type": "adaptive"}, output_config={"effort": "high"}, max_tokens=1500),
}


def load_state():
    if os.path.exists(STATE_PATH):
        return json.load(open(STATE_PATH, encoding="utf-8"))
    return {}


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def cmd_submit():
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["CLAUDE_API_KEY"])
    questions = json.load(open(QUESTIONS_PATH, encoding="utf-8"))

    state = load_state()
    for setting_name, extra_kwargs in SETTINGS.items():
        if setting_name in state and state[setting_name].get("batch_id"):
            print(f"{setting_name}: already submitted (batch_id={state[setting_name]['batch_id']}), skipping.")
            continue

        requests = []
        for q in questions:
            msg = api_lib.build_prompt_text(q)
            params = dict(model=MODEL_ID, messages=[{"role": "user", "content": msg}], **extra_kwargs)
            requests.append({"custom_id": q["id"], "params": params})

        batch = client.messages.batches.create(requests=requests)
        state[setting_name] = {"batch_id": batch.id, "status": batch.processing_status, "submitted_at": time.time()}
        save_state(state)
        print(f"{setting_name}: submitted batch {batch.id} (status={batch.processing_status}, {len(requests)} requests)")


def cmd_poll():
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["CLAUDE_API_KEY"])
    state = load_state()
    if not state:
        print("No batches submitted yet. Run `submit` first.")
        return

    all_done = True
    for setting_name, info in state.items():
        if info.get("downloaded"):
            print(f"{setting_name}: already downloaded.")
            continue
        batch = client.messages.batches.retrieve(info["batch_id"])
        counts = batch.request_counts
        print(f"{setting_name}: status={batch.processing_status} "
              f"(succeeded={counts.succeeded} errored={counts.errored} "
              f"processing={counts.processing} canceled={counts.canceled} expired={counts.expired})")
        info["status"] = batch.processing_status
        if batch.processing_status == "ended":
            out_path = os.path.join(ROOT, "results", f"model_answers_v2_claude-haiku-5.5_{setting_name}.json")
            save_batch_results(client, batch, setting_name, out_path)
            info["downloaded"] = True
            info["out_path"] = out_path
            print(f"  -> saved {out_path}")
        else:
            all_done = False
    save_state(state)
    if all_done:
        print("\nAll Anthropic batches complete.")
    else:
        print("\nStill waiting on one or more batches. Re-run `poll` later.")


def save_batch_results(client, batch, setting_name, out_path):
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
        results.append({
            "id": qid, "category": q["category"], "question_id": q["question_id"],
            "answer_key": q["answer_key"], "ground_truth_option": gt,
            "model_raw_output": raw_text, "model_answer": letter if is_valid else "invalid",
            "is_valid": is_valid, "is_correct": is_correct,
            "result_type": entry.result.type,
            "usage": usage,
        })
    n_with_gt = sum(1 for r in results if r["ground_truth_option"] is not None)
    summary = {
        "model_id": MODEL_ID, "setting": setting_name, "via": "anthropic_message_batches",
        "caveat": "Claude Haiku is in the same model family as the generator (Claude Sonnet 5), which may give it an advantage other models don't have.",
        "n_valid_answers": n_valid, "n_with_ground_truth": n_with_gt, "n_correct": n_correct,
        "accuracy_overall_pct": 100.0 * n_correct / n_with_gt if n_with_gt else None,
        "results": results,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("submit", "poll"):
        print("Usage: 05d_anthropic_batch.py [submit|poll]")
        sys.exit(1)
    if sys.argv[1] == "submit":
        cmd_submit()
    else:
        cmd_poll()
