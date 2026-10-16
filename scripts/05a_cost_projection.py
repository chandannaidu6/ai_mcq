"""
Step 5a: budget-safety cost projection. For every PAID provider/setting we
intend to run at full scale, run it on a small real sample of N questions,
measure ACTUAL token usage from the API's own response, and project the
full-scale cost using the prices recorded in results/prices.json (looked up
from each provider's official pricing page). If a projection would exceed
that provider's hard cap, the orchestrator (05_run_api_answerers.py) skips
the most expensive setting first and records why.

Never estimates token counts -- only ever uses what the API actually
reports using.
"""
import json
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dotenv import load_dotenv  # noqa: E402

ROOT = os.path.dirname(HERE)
load_dotenv(os.path.join(ROOT, ".env"))

import api_lib  # noqa: E402

QUESTIONS_PATH = os.path.join(ROOT, "results", "questions_v2_verified.json")
PRICES_PATH = os.path.join(ROOT, "results", "prices.json")
OUT_PATH = os.path.join(ROOT, "results", "cost_projection.json")

TEST_N = 20
SAMPLE_SEED = 42


def sample_questions(n):
    qs = json.load(open(QUESTIONS_PATH, encoding="utf-8"))
    rng = random.Random(SAMPLE_SEED)
    return rng.sample(qs, min(n, len(qs)))


def test_openai(model_id, reasoning_effort, questions):
    import openai
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    total_in = total_out = total_reasoning = 0
    n_ok = 0
    for q in questions:
        msg = api_lib.build_prompt_text(q)
        try:
            resp = client.chat.completions.create(
                model=model_id,
                max_completion_tokens=100,
                reasoning_effort=reasoning_effort,
                messages=[{"role": "user", "content": msg}],
            )
            u = resp.usage
            total_in += u.prompt_tokens
            total_out += u.completion_tokens  # completion_tokens already includes reasoning_tokens per OpenAI's accounting
            total_reasoning += (u.completion_tokens_details.reasoning_tokens or 0) if u.completion_tokens_details else 0
            n_ok += 1
        except Exception as e:
            print(f"  [openai test error] {e!r}")
    return dict(n_ok=n_ok, total_in=total_in, total_out=total_out, total_reasoning=total_reasoning)


def test_gemini(model_id, thinking_budget, questions):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    total_in = total_out = total_thoughts = 0
    n_ok = 0
    for q in questions:
        msg = api_lib.build_prompt_text(q)
        try:
            cfg_kwargs = dict(max_output_tokens=200)
            if thinking_budget is not None:
                cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking_budget)
            cfg = types.GenerateContentConfig(**cfg_kwargs)
            resp = client.models.generate_content(model=model_id, contents=msg, config=cfg)
            u = resp.usage_metadata
            total_in += u.prompt_token_count or 0
            total_out += u.candidates_token_count or 0
            total_thoughts += u.thoughts_token_count or 0
            n_ok += 1
        except Exception as e:
            print(f"  [gemini test error] {e!r}")
        time.sleep(1.0)  # gentle pacing for free tier
    return dict(n_ok=n_ok, total_in=total_in, total_out=total_out, total_thoughts=total_thoughts)


def project_openai_cost(stats, prices, full_n):
    if stats["n_ok"] == 0:
        return None
    avg_in = stats["total_in"] / stats["n_ok"]
    avg_out = stats["total_out"] / stats["n_ok"]
    rate = prices["openai"]["standard_usd_per_million_tokens"]
    cost_per_q = (avg_in * rate["input"] + avg_out * rate["output"]) / 1e6
    return dict(avg_input_tokens=avg_in, avg_output_tokens=avg_out,
                projected_cost_usd_standard=cost_per_q * full_n,
                projected_cost_usd_batch=cost_per_q * full_n * (1 - prices["openai"]["batch_discount_pct"] / 100))


def main():
    prices = json.load(open(PRICES_PATH, encoding="utf-8"))
    questions = sample_questions(TEST_N)
    full_n = len(json.load(open(QUESTIONS_PATH, encoding="utf-8")))

    results = {"test_n": TEST_N, "full_n": full_n, "sample_seed": SAMPLE_SEED, "settings": {}}

    print(f"Running {TEST_N}-question cost-projection tests (full scale = {full_n} questions)...")

    print("\n--- OpenAI gpt-6-luna, reasoning_effort=none ---")
    s = test_openai("gpt-6-luna", "none", questions)
    proj = project_openai_cost(s, prices, full_n)
    results["settings"]["openai_gpt-6-luna_reasoning-none"] = {"raw": s, "projection": proj}
    print(s, "\nprojection:", proj)

    print("\n--- OpenAI gpt-6-luna, reasoning_effort=medium ---")
    s = test_openai("gpt-6-luna", "medium", questions)
    proj = project_openai_cost(s, prices, full_n)
    results["settings"]["openai_gpt-6-luna_reasoning-medium"] = {"raw": s, "projection": proj}
    print(s, "\nprojection:", proj)

    print("\n--- Gemini gemini-3.8-flash, thinking_budget=0 ---")
    s = test_gemini("gemini-3.8-flash", 0, questions)
    results["settings"]["gemini_3.8-flash_thinking-off"] = {"raw": s}
    print(s)

    print("\n--- Gemini gemini-3.8-flash, thinking_budget=-1 (dynamic/on) ---")
    s = test_gemini("gemini-3.8-flash", -1, questions)
    results["settings"]["gemini_3.8-flash_thinking-on"] = {"raw": s}
    print(s)

    print("\n--- Gemini gemini-3.5-flash-lite, no thinking_config (default/off) ---")
    s = test_gemini("gemini-3.5-flash-lite", None, questions)
    results["settings"]["gemini_3.5-flash-lite_thinking-off"] = {"raw": s}
    print(s)

    print("\n--- Gemini gemini-3.5-flash-lite, thinking_budget=1024 (on) ---")
    s = test_gemini("gemini-3.5-flash-lite", 1024, questions)
    results["settings"]["gemini_3.5-flash-lite_thinking-on"] = {"raw": s}
    print(s)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {OUT_PATH}")


if __name__ == "__main__":
    main()
