"""
Builds results/cost_log.csv from the REAL per-call token usage recorded in
each paid provider's downloaded batch results (never estimated). One row
per (provider, setting) with aggregated tokens and the actual cost computed
from results/prices.json's officially-sourced rates (batch-discounted,
since both OpenAI and Anthropic runs used their batch APIs).
"""
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "results")
PRICES_PATH = os.path.join(RESULTS_DIR, "prices.json")
OUT_PATH = os.path.join(RESULTS_DIR, "cost_log.csv")

SOURCES = [
    ("openai", "gpt-6-luna (reasoning: none)", "model_answers_v2_openai_gpt-6-luna_reasoning-none.json"),
    ("openai", "gpt-6-luna (reasoning: medium)", "model_answers_v2_openai_gpt-6-luna_reasoning-medium.json"),
    ("anthropic", "claude-haiku-5.5 (thinking: off)", "model_answers_v2_claude-haiku-5.5_thinking-off.json"),
    ("anthropic", "claude-haiku-5.5 (thinking: on)", "model_answers_v2_claude-haiku-5.5_thinking-on.json"),
]


def main():
    prices = json.load(open(PRICES_PATH, encoding="utf-8"))
    rows = []
    running_totals = {"openai": 0.0, "anthropic": 0.0, "gemini": 0.0}

    for provider, label, fname in SOURCES:
        path = os.path.join(RESULTS_DIR, fname)
        if not os.path.exists(path):
            rows.append([provider, label, "NOT RUN", "", "", "", "", ""])
            continue
        data = json.load(open(path, encoding="utf-8"))
        total_in = total_out = total_thinking_or_reasoning = 0
        n = 0
        for r in data.get("results", []):
            u = r.get("usage")
            if not u:
                continue
            n += 1
            if provider == "openai":
                total_in += u.get("prompt_tokens", 0)
                total_out += u.get("completion_tokens", 0)
                d = u.get("completion_tokens_details") or {}
                total_thinking_or_reasoning += d.get("reasoning_tokens", 0) if isinstance(d, dict) else 0
            else:
                total_in += u.get("input_tokens", 0)
                total_out += u.get("output_tokens", 0)
                total_thinking_or_reasoning += u.get("thinking_tokens", 0)

        if provider == "openai":
            rate = prices["openai"]["batch_usd_per_million_tokens"]
        else:
            std = prices["anthropic"]
            disc = std["batch_discount_pct"] / 100
            rate = {"input": std["input_usd_per_million_tokens"]["le_100k_context"] * (1 - disc),
                    "output": std["output_usd_per_million_tokens"]["le_100k_context"] * (1 - disc)}

        cost = (total_in * rate["input"] + total_out * rate["output"]) / 1e6
        running_totals[provider] += cost
        rows.append([provider, label, n, total_in, total_out, total_thinking_or_reasoning, f"{cost:.4f}",
                     f"{running_totals[provider]:.4f}"])

    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["provider", "model_setting", "n_calls", "input_tokens", "output_tokens",
                    "thinking_or_reasoning_tokens", "cost_usd_this_setting", "running_total_usd_this_provider"])
        w.writerows(rows)
        w.writerow([])
        w.writerow(["TOTALS", "", "", "", "", "",
                    f"openai={running_totals['openai']:.4f}", f"anthropic={running_totals['anthropic']:.4f}"])
        w.writerow(["", "", "", "", "", "", "gemini=0.0000 (free tier, dropped before any token usage was billable)", ""])
        w.writerow(["BUDGET CAPS", "", "", "", "", "", "openai_cap=9.00", "anthropic_cap=9.00"])

    print(f"Wrote {OUT_PATH}")
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()
