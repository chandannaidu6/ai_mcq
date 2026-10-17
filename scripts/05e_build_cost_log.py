"""
Builds results/cost_log.csv from the REAL per-call token usage recorded in
each paid provider's downloaded batch results (never estimated). One row
per (model, setting) with aggregated tokens and the actual cost computed
from results/prices.json's officially-sourced PER-MODEL rates (batch
discount applied throughout -- every paid run used the provider's batch API).
"""
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "results")
PRICES_PATH = os.path.join(RESULTS_DIR, "prices.json")
OUT_PATH = os.path.join(RESULTS_DIR, "cost_log.csv")

# (price_model_key, display_label, result_filename)
SOURCES = [
    ("gpt-6-luna", "gpt-6-luna (reasoning: none)", "model_answers_v2_openai_gpt-6-luna_reasoning-none.json"),
    ("gpt-6-luna", "gpt-6-luna (reasoning: medium)", "model_answers_v2_openai_gpt-6-luna_reasoning-medium.json"),
    ("gpt-6-astra", "gpt-6-astra (reasoning: low)", "model_answers_v2_openai_gpt-6-astra_reasoning-low.json"),
    ("claude-haiku-5-5", "claude-haiku-5.5 (thinking: off)", "model_answers_v2_claude-haiku-5.5_thinking-off.json"),
    ("claude-haiku-5-5", "claude-haiku-5.5 (thinking: on)", "model_answers_v2_claude-haiku-5.5_thinking-on.json"),
    ("claude-opus-5", "claude-opus-5 (thinking: off)", "model_answers_v2_claude-opus-5_thinking-off.json"),
    ("claude-opus-5", "claude-opus-5 (thinking: on)", "model_answers_v2_claude-opus-5_thinking-on.json"),
]


def main():
    prices = json.load(open(PRICES_PATH, encoding="utf-8"))
    rows = []
    running_totals = {"openai": 0.0, "anthropic": 0.0}

    for price_key, label, fname in SOURCES:
        model_prices = prices["models"][price_key]
        provider = model_prices["provider"]
        std_rate = model_prices["standard_usd_per_million_tokens"]
        disc = model_prices["batch_discount_pct"] / 100
        rate = {"input": std_rate["input"] * (1 - disc), "output": std_rate["output"] * (1 - disc)}

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

        cost = (total_in * rate["input"] + total_out * rate["output"]) / 1e6
        running_totals[provider] += cost
        rows.append([provider, label, n, total_in, total_out, total_thinking_or_reasoning, f"{cost:.4f}",
                     f"{running_totals[provider]:.4f}"])

    grand_total = running_totals["openai"] + running_totals["anthropic"]

    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["provider", "model_setting", "n_calls", "input_tokens", "output_tokens",
                    "thinking_or_reasoning_tokens", "cost_usd_this_setting", "running_total_usd_this_provider"])
        w.writerows(rows)
        w.writerow([])
        w.writerow(["TOTALS", "", "", "", "", "",
                    f"openai={running_totals['openai']:.4f}", f"anthropic={running_totals['anthropic']:.4f}"])
        w.writerow(["", "", "", "", "", "", "gemini=0.0000 (free tier, dropped before any token usage was billable)", ""])
        w.writerow(["GRAND TOTAL (all providers)", "", "", "", "", "", f"${grand_total:.4f}", ""])
        w.writerow(["COMBINED BUDGET CAP", "", "", "", "", "", "$10.00", f"margin=${10-grand_total:.4f}"])

    print(f"Wrote {OUT_PATH}")
    for row in rows:
        print(row)
    print(f"\nGRAND TOTAL: ${grand_total:.4f} (cap $10.00, margin ${10-grand_total:.4f})")


if __name__ == "__main__":
    main()
