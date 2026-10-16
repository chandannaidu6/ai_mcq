"""
Step 5 (Gemini free-tier answerer): resumable, rate-limited runner.

The Gemini free tier enforces a strict per-model RPM quota (measured at 5
requests/minute for gemini-3.8-flash during this run's cost-projection
test). This script paces requests to stay safely under that limit, retries
with backoff reading the API's own suggested retry delay on 429s, and saves
progress after EVERY question (not just at the end) so it can be killed and
resumed without re-paying for/re-waiting on already-answered questions --
matching the brief's "if the daily limit is reached, save progress and
resume tomorrow" instruction.

Usage:
    python 05b_run_gemini.py <model_id> <thinking_setting> <out_path>
    thinking_setting: "off" or "on"
"""
import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dotenv import load_dotenv  # noqa: E402

ROOT = os.path.dirname(HERE)
load_dotenv(os.path.join(ROOT, ".env"))

import api_lib  # noqa: E402

QUESTIONS_PATH = os.path.join(ROOT, "results", "questions_v2_verified.json")

MIN_INTERVAL_SECONDS = 13.0  # safely under the observed 5 RPM (=12s) free-tier cap
MAX_RETRIES = 6


def parse_retry_after(err_str):
    m = re.search(r"retry in ([\d.]+)s", err_str)
    if m:
        return float(m.group(1)) + 1.0
    return None


def call_gemini(client, types, model_id, prompt, thinking_setting):
    cfg_kwargs = dict(max_output_tokens=300)
    if model_id == "gemini-3.8-flash":
        # observed: thinking_budget=0 does NOT fully suppress thinking on real
        # (non-trivial) prompts for this model -- record that as "minimum
        # achievable" per the brief's instruction, rather than pretending it's off.
        budget = 0 if thinking_setting == "off" else -1  # -1 = dynamic/auto thinking
        cfg_kwargs["thinking_config"] = type(types.ThinkingConfig())(thinking_budget=budget)
    else:  # gemini-3.5-flash-lite: no thinking by default; must opt in explicitly
        if thinking_setting == "on":
            cfg_kwargs["thinking_config"] = type(types.ThinkingConfig())(thinking_budget=1024)
        # "off": omit thinking_config entirely (confirmed default = no thinking tokens)
    cfg = types.GenerateContentConfig(**cfg_kwargs)
    return client.models.generate_content(model=model_id, contents=prompt, config=cfg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model_id")
    ap.add_argument("thinking_setting", choices=["off", "on"])
    ap.add_argument("out_path")
    args = ap.parse_args()

    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    questions = json.load(open(QUESTIONS_PATH, encoding="utf-8"))

    # resume support: load any existing partial results
    done = {}
    if os.path.exists(args.out_path):
        existing = json.load(open(args.out_path, encoding="utf-8"))
        for r in existing.get("results", []):
            done[r["id"]] = r
        print(f"Resuming: {len(done)}/{len(questions)} already answered.")

    results = list(done.values())
    last_call_time = 0.0
    daily_limit_hit = False

    for i, q in enumerate(questions):
        if q["id"] in done:
            continue
        if daily_limit_hit:
            break

        prompt = api_lib.build_prompt_text(q)

        # pace requests
        elapsed = time.time() - last_call_time
        if elapsed < MIN_INTERVAL_SECONDS:
            time.sleep(MIN_INTERVAL_SECONDS - elapsed)

        attempt = 0
        raw_text = None
        usage = None
        while attempt < MAX_RETRIES:
            attempt += 1
            try:
                last_call_time = time.time()
                resp = call_gemini(client, types, args.model_id, prompt, args.thinking_setting)
                raw_text = resp.text
                u = resp.usage_metadata
                usage = dict(prompt_tokens=u.prompt_token_count or 0,
                             output_tokens=u.candidates_token_count or 0,
                             thoughts_tokens=u.thoughts_token_count or 0)
                break
            except Exception as e:
                err_str = str(e)
                if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                    if "PerDay" in err_str or "daily" in err_str.lower():
                        print(f"Daily quota hit at question {i} ({q['id']}). Stopping cleanly.")
                        daily_limit_hit = True
                        break
                    retry_after = parse_retry_after(err_str) or (5 * attempt)
                    print(f"  rate-limited (attempt {attempt}/{MAX_RETRIES}), waiting {retry_after:.1f}s...")
                    time.sleep(retry_after)
                else:
                    print(f"  [error, attempt {attempt}/{MAX_RETRIES}] {err_str[:200]}")
                    time.sleep(3 * attempt)

        if daily_limit_hit:
            break

        letter = api_lib.parse_letter(raw_text) if raw_text else None
        gt = q.get("ground_truth_option")
        results.append({
            "id": q["id"],
            "category": q["category"],
            "question_id": q["question_id"],
            "answer_key": q["answer_key"],
            "ground_truth_option": gt,
            "model_raw_output": raw_text,
            "model_answer": letter if letter else "invalid",
            "is_valid": letter is not None,
            "is_correct": (letter == gt) if (letter and gt is not None) else False,
            "usage": usage,
        })

        if (len(results)) % 20 == 0 or i == len(questions) - 1:
            save(args, results, done_count=len(results), total=len(questions),
                 daily_limit_hit=daily_limit_hit)
            print(f"  ...progress saved: {len(results)}/{len(questions)}")

    save(args, results, done_count=len(results), total=len(questions), daily_limit_hit=daily_limit_hit)
    print(f"Done (or paused). {len(results)}/{len(questions)} answered. daily_limit_hit={daily_limit_hit}")


def save(args, results, done_count, total, daily_limit_hit):
    n_with_gt = sum(1 for r in results if r["ground_truth_option"] is not None)
    n_correct = sum(1 for r in results if r["is_correct"])
    n_valid = sum(1 for r in results if r["is_valid"])
    summary = {
        "model_id": args.model_id,
        "thinking_setting": args.thinking_setting,
        "progress": f"{done_count}/{total}",
        "complete": done_count >= total,
        "daily_limit_hit": daily_limit_hit,
        "n_valid_answers": n_valid,
        "n_with_ground_truth": n_with_gt,
        "n_correct": n_correct,
        "accuracy_overall_pct": 100.0 * n_correct / n_with_gt if n_with_gt else None,
        "results": results,
    }
    tmp = args.out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    os.replace(tmp, args.out_path)


if __name__ == "__main__":
    main()
