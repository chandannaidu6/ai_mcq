"""
Step 6 (v2): analyze and report across every model/setting that has
results available (GPU open-source models, OpenAI batch results, Gemini
free-tier results, Anthropic Claude Haiku if unblocked). Designed to run
at any point and clearly report what's complete vs. still in progress /
blocked, rather than requiring every provider to be finished.

Produces:
  results/questions_v2.csv
  results/summary_v2.md
  results/accuracy_all_models.png
  results/accuracy_by_category_all.png
  results/thinking_effect.png
  results/accuracy_by_size.png
"""
import csv
import glob
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "results")
QUESTIONS_PATH = os.path.join(RESULTS_DIR, "questions_v2_verified.json")
SAMPLES_PATH = os.path.join(ROOT, "pilot_data", "sampled_solutions_v2.json")
SKIPS_PATH = os.path.join(RESULTS_DIR, "category_skips.json")
METADATA_PATH = os.path.join(RESULTS_DIR, "metadata.json")

CATEGORIES = ["output", "variable_state", "loop_trace", "control_flow",
              "call_count", "edge_case", "code_modification", "data_structure_state"]

PALETTE = ["#4E79A7", "#F28E2B", "#59A14F", "#E15759", "#B07AA1", "#76B7B2", "#EDC948", "#FF9DA7"]

# (display_label, file_glob_or_path, family, is_commercial, size_b_or_None, thinking_setting_or_None)
MODEL_SOURCES = [
    ("Qwen2.5-Coder-3B-Instruct", "model_answers_v2_qwen2.5-coder-3b-instruct.json", "Qwen2.5-Coder", False, 3, None),
    ("Qwen2.5-Coder-7B-Instruct-AWQ", "model_answers_v2_qwen2.5-coder-7b-instruct-awq.json", "Qwen2.5-Coder", False, 7, None),
    ("Qwen2.5-Coder-14B-Instruct-AWQ", "model_answers_v2_qwen2.5-coder-14b-instruct-awq.json", "Qwen2.5-Coder", False, 14, None),
    ("DeepSeek-Coder-V2-Lite-Instruct-AWQ", "model_answers_v2_deepseek-coder-v2-lite-instruct-awq.json", "DeepSeek-Coder", False, 16, None),
    ("GPT-6 Luna (reasoning: none)", "model_answers_v2_openai_gpt-6-luna_reasoning-none.json", "GPT-6", True, None, "off"),
    ("GPT-6 Luna (reasoning: medium)", "model_answers_v2_openai_gpt-6-luna_reasoning-medium.json", "GPT-6", True, None, "on"),
    ("Claude Haiku 5.5 (thinking: off)", "model_answers_v2_claude-haiku-5.5_thinking-off.json", "Claude", True, None, "off"),
    ("Claude Haiku 5.5 (thinking: on)", "model_answers_v2_claude-haiku-5.5_thinking-on.json", "Claude", True, None, "on"),
]


def load_model_data():
    loaded = {}
    missing = {}
    for label, fname, family, commercial, size, thinking in MODEL_SOURCES:
        path = os.path.join(RESULTS_DIR, fname)
        if os.path.exists(path):
            try:
                data = json.load(open(path, encoding="utf-8"))
                complete = data.get("complete", True)  # GPU/batch runs are always complete when the file exists
                loaded[label] = dict(data=data, family=family, commercial=commercial, size=size,
                                      thinking=thinking, complete=complete)
            except Exception as e:
                missing[label] = f"failed to parse: {e}"
        else:
            missing[label] = "not yet available"
    return loaded, missing


def compute_accuracy(data):
    results = data["results"]
    gt_by_id = {r["id"]: r.get("ground_truth_option") for r in results}
    cat_by_id = {r["id"]: r["category"] for r in results}
    correct = total = 0
    cat_correct = {c: 0 for c in CATEGORIES}
    cat_total = {c: 0 for c in CATEGORIES}
    n_valid = 0
    for r in results:
        if r.get("is_valid"):
            n_valid += 1
        gt = gt_by_id[r["id"]]
        if gt is None:
            continue
        total += 1
        cat_total[cat_by_id[r["id"]]] += 1
        if r.get("is_correct"):
            correct += 1
            cat_correct[cat_by_id[r["id"]]] += 1
    overall = 100.0 * correct / total if total else None
    by_cat = {c: (100.0 * cat_correct[c] / cat_total[c] if cat_total[c] else None) for c in CATEGORIES}
    return overall, by_cat, n_valid, len(results), total


def write_csv(questions, loaded):
    out_path = os.path.join(RESULTS_DIR, "questions_v2.csv")
    labels = list(loaded.keys())
    lookup = {label: {r["id"]: r for r in info["data"]["results"]} for label, info in loaded.items()}

    header = ["id", "task_question_id", "student_id", "category", "question",
              "option_A", "option_B", "option_C", "option_D",
              "answer_key", "ground_truth_option", "key_is_correct", "generation_note"]
    for label in labels:
        header += [f"{label}_answer", f"{label}_correct", f"{label}_valid"]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for q in questions:
            row = [q["id"], q["question_id"], q["student_id"], q["category"], q["question"],
                   q["options"]["A"], q["options"]["B"], q["options"]["C"], q["options"]["D"],
                   q["answer_key"], q.get("ground_truth_option"), q.get("key_is_correct"),
                   q.get("generation_note", "")]
            for label in labels:
                r = lookup[label].get(q["id"])
                if r is None:
                    row += ["", "", ""]
                else:
                    row += [r.get("model_answer"), r.get("is_correct"), r.get("is_valid")]
            w.writerow(row)
    print(f"Wrote {out_path}")
    return out_path


def plot_accuracy_all(overall_by_label, loaded, out_path):
    labels = [l for l in overall_by_label if overall_by_label[l] is not None]
    labels.sort(key=lambda l: overall_by_label[l])
    vals = [overall_by_label[l] for l in labels]
    colors = []
    for l in labels:
        fam = loaded[l]["family"]
        colors.append(PALETTE[0] if fam == "Qwen2.5-Coder" else
                       PALETTE[1] if fam == "DeepSeek-Coder" else
                       PALETTE[2] if fam == "GPT-6" else
                       PALETTE[3] if fam == "Gemini" else PALETTE[4])
    fig, ax = plt.subplots(figsize=(9, max(4, 0.45 * len(labels) + 1)), dpi=150)
    y = np.arange(len(labels))
    bars = ax.barh(y, vals, color=colors)
    for b, v in zip(bars, vals):
        ax.text(v + 1, b.get_y() + b.get_height() / 2, f"{v:.1f}%", va="center", fontsize=8)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.axvline(25, color="gray", linestyle=":", linewidth=1)
    ax.text(25, -0.8, "chance (25%)", fontsize=7, color="gray", ha="center")
    ax.set_xlabel("Accuracy vs. execution ground truth (%)")
    ax.set_xlim(0, 105)
    ax.set_title("Overall MCQ accuracy, all models/settings")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_path}")


def plot_accuracy_by_category(by_cat_by_label, loaded, out_path, max_models=8):
    labels = sorted(by_cat_by_label.keys(),
                     key=lambda l: -np.nanmean([v if v is not None else np.nan for v in by_cat_by_label[l].values()]))[:max_models]
    n_models = len(labels)
    fig, ax = plt.subplots(figsize=(11, 6), dpi=150)
    x = np.arange(len(CATEGORIES))
    width = 0.8 / max(n_models, 1)
    for i, label in enumerate(labels):
        vals = [by_cat_by_label[label][c] if by_cat_by_label[label][c] is not None else 0 for c in CATEGORIES]
        offset = (i - (n_models - 1) / 2) * width
        ax.bar(x + offset, vals, width, label=label, color=PALETTE[i % len(PALETTE)])
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace("_", "\n") for c in CATEGORIES], fontsize=8)
    ax.set_ylabel("Accuracy (%)")
    ax.set_ylim(0, 110)
    ax.axhline(25, color="gray", linestyle=":", linewidth=1)
    ax.set_title(f"Accuracy by category (top {n_models} models by mean accuracy)")
    ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_path}")


def plot_thinking_effect(overall_by_label, loaded, out_path):
    pairs = []
    seen_bases = set()
    for label, info in loaded.items():
        if info["thinking"] != "off":
            continue
        base = label.split(" (thinking")[0].split(" (reasoning")[0]
        on_label = None
        for l2, info2 in loaded.items():
            if info2["thinking"] == "on" and l2.startswith(base):
                on_label = l2
                break
        if on_label and overall_by_label.get(label) is not None and overall_by_label.get(on_label) is not None:
            pairs.append((base, overall_by_label[label], overall_by_label[on_label]))

    if not pairs:
        print("No complete thinking on/off pairs yet -- skipping thinking_effect.png")
        return False

    fig, ax = plt.subplots(figsize=(7, 5), dpi=150)
    x = np.arange(len(pairs))
    width = 0.35
    offs = [p[1] for p in pairs]
    ons = [p[2] for p in pairs]
    ax.bar(x - width / 2, offs, width, label="thinking/reasoning OFF (or minimum)", color=PALETTE[0])
    ax.bar(x + width / 2, ons, width, label="thinking/reasoning ON", color=PALETTE[3])
    for i, (b, o, on) in enumerate(pairs):
        ax.text(i - width / 2, o + 1, f"{o:.0f}%", ha="center", fontsize=8)
        ax.text(i + width / 2, on + 1, f"{on:.0f}%", ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([p[0] for p in pairs], fontsize=9)
    ax.set_ylabel("Accuracy (%)")
    ax.set_ylim(0, 110)
    ax.set_title("Effect of thinking/reasoning on accuracy (same model)")
    ax.legend(fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_path}")
    return True


def plot_accuracy_by_size(overall_by_label, loaded, out_path):
    qwen = [(info["size"], overall_by_label[l]) for l, info in loaded.items()
            if info["family"] == "Qwen2.5-Coder" and overall_by_label.get(l) is not None]
    qwen.sort()
    fig, ax = plt.subplots(figsize=(7, 5), dpi=150)
    if qwen:
        sizes = [s for s, a in qwen]
        accs = [a for s, a in qwen]
        ax.plot(sizes, accs, "-o", color=PALETTE[0], linewidth=2, markersize=8, label="Qwen2.5-Coder (AWQ for 7B/14B)")
        for s, a in qwen:
            ax.annotate(f"{a:.0f}%", (s, a), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9)
    others = [(l, info["size"], overall_by_label[l]) for l, info in loaded.items()
              if info["family"] != "Qwen2.5-Coder" and info["size"] is not None and overall_by_label.get(l) is not None]
    for i, (l, s, a) in enumerate(others):
        ax.scatter([s], [a], color=PALETTE[(i + 1) % len(PALETTE)], s=90, zorder=5, label=l)
        ax.annotate(f"{a:.0f}%", (s, a), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)
    ax.axhline(25, color="gray", linestyle=":", linewidth=1, label="chance (25%)")
    ax.set_xlabel("Model size (billion parameters)")
    ax.set_ylabel("Overall accuracy (%)")
    ax.set_ylim(0, 110)
    ax.set_title("Accuracy vs. model size (open-source models)")
    ax.legend(fontsize=7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_path}")


def main():
    questions = json.load(open(QUESTIONS_PATH, encoding="utf-8"))
    samples = json.load(open(SAMPLES_PATH, encoding="utf-8"))
    skips = json.load(open(SKIPS_PATH, encoding="utf-8")) if os.path.exists(SKIPS_PATH) else []
    metadata = json.load(open(METADATA_PATH, encoding="utf-8")) if os.path.exists(METADATA_PATH) else {}

    loaded, missing = load_model_data()
    if not loaded:
        print("No model results available yet.")
        return

    write_csv(questions, loaded)

    overall_by_label = {}
    by_cat_by_label = {}
    n_valid_by_label = {}
    n_total_by_label = {}
    n_with_gt_by_label = {}
    for label, info in loaded.items():
        overall, by_cat, n_valid, n_total, n_with_gt = compute_accuracy(info["data"])
        overall_by_label[label] = overall
        by_cat_by_label[label] = by_cat
        n_valid_by_label[label] = n_valid
        n_total_by_label[label] = n_total
        n_with_gt_by_label[label] = n_with_gt

    plot_accuracy_all(overall_by_label, loaded, os.path.join(RESULTS_DIR, "accuracy_all_models.png"))
    plot_accuracy_by_category(by_cat_by_label, loaded, os.path.join(RESULTS_DIR, "accuracy_by_category_all.png"))
    plot_thinking_effect(overall_by_label, loaded, os.path.join(RESULTS_DIR, "thinking_effect.png"))
    plot_accuracy_by_size(overall_by_label, loaded, os.path.join(RESULTS_DIR, "accuracy_by_size.png"))

    # ---- summary.md ----
    n_total_q = len(questions)
    n_gt = sum(1 for q in questions if q.get("ground_truth_option") is not None)
    n_key_wrong = sum(1 for q in questions if q.get("key_is_correct") is False)
    n_tasks = len(set(s["question_id"] for s in samples))
    n_solutions = len(samples)

    cat_gt_counts = {c: sum(1 for q in questions if q["category"] == c) for c in CATEGORIES}
    cat_gt_verified = {c: sum(1 for q in questions if q["category"] == c and q.get("ground_truth_option") is not None) for c in CATEGORIES}
    cat_key_wrong = {c: sum(1 for q in questions if q["category"] == c and q.get("key_is_correct") is False) for c in CATEGORIES}

    lines = []
    lines.append("# AI-MCQ-PILOT v2: expanded 8-category, multi-provider results\n")
    lines.append(f"Generator: **{metadata.get('generator',{}).get('model_name','Claude Sonnet 5')}** "
                 f"(`{metadata.get('generator',{}).get('model_id','claude-sonnet-5')}`), run via Claude Code.\n")
    all_complete = not missing and all(info["complete"] for info in loaded.values())
    status_note = "all providers complete." if all_complete else "report generated during an ongoing run -- see per-provider completeness notes below."
    lines.append(f"Run date: {metadata.get('run_started','2026-10-16')} ({status_note})\n")
    lines.append("")

    lines.append("## Hardware\n")
    hw = metadata.get("hardware", {})
    lines.append(f"- GPU: {hw.get('gpu','NVIDIA RTX 4000 Ada Generation')}, {hw.get('gpu_vram_mib','20475')} MiB VRAM\n")
    lines.append(f"- Python {hw.get('python_version','3.10.12')}, vLLM 0.31.0\n")
    lines.append("")

    lines.append("## Dataset and question generation\n")
    lines.append(f"- **{n_solutions} student solutions** sampled (seed=42, superset of the original 25-solution "
                  f"pilot sample), spanning **{n_tasks}/21 distinct Python tasks** in the dataset.\n")
    lines.append(f"- **{n_total_q} questions** generated across **8 categories** by a template-based "
                  f"(AutoMCQ-style) generator: for each applicable category/solution pair, the generator used "
                  f"`ast` analysis plus the dataset's own `tests.csv` test cases and tester harnesses to "
                  f"construct a question, in one pass, with NO execution of student code to self-check before "
                  f"saving (ground truth comes only from Step 3's execution). Categories that don't apply to a "
                  f"given solution (e.g. no loop found) are skipped and logged "
                  f"(`results/category_skips.json`, {len(skips)} skips recorded).\n")
    lines.append("")
    lines.append("### Questions per category (generated / with verifiable ground truth / wrong generator key)\n")
    lines.append("| Category | Generated | Verifiable ground truth | Generator's key was wrong |")
    lines.append("|---|---|---|---|")
    for c in CATEGORIES:
        wrong_pct = f"{100*cat_key_wrong[c]/cat_gt_verified[c]:.1f}%" if cat_gt_verified[c] else "n/a"
        lines.append(f"| {c} | {cat_gt_counts[c]} | {cat_gt_verified[c]} ({100*cat_gt_verified[c]/cat_gt_counts[c]:.0f}%) | "
                      f"{cat_key_wrong[c]} ({wrong_pct}) |")
    lines.append("")
    lines.append(f"**Overall: {n_gt}/{n_total_q} ({100*n_gt/n_total_q:.1f}%) questions have verifiable execution "
                  f"ground truth; {n_key_wrong}/{n_gt} ({100*n_key_wrong/n_gt:.1f}%) of the generator's own "
                  f"answer keys were wrong when checked against execution** (left uncorrected, as required -- "
                  f"accuracy below is scored against execution ground truth, never the generator's original key).\n")
    lines.append("")

    lines.append("## Provider/model completeness\n")
    lines.append("| Model/setting | Status |")
    lines.append("|---|---|")
    for label, info in loaded.items():
        status = "complete" if info["complete"] else f"IN PROGRESS ({info['data'].get('progress','?')})"
        lines.append(f"| {label} | {status} |")
    for label, reason in missing.items():
        lines.append(f"| {label} | **not available** -- {reason} |")
    lines.append("")

    lines.append("## Overall accuracy, ranked (scored against execution ground truth)\n")
    lines.append("| Rank | Model/setting | Valid answers | Questions w/ ground truth | Accuracy |")
    lines.append("|---|---|---|---|---|")
    ranked = sorted([l for l in overall_by_label if overall_by_label[l] is not None],
                     key=lambda l: -overall_by_label[l])
    for i, label in enumerate(ranked, 1):
        lines.append(f"| {i} | {label} | {n_valid_by_label[label]}/{n_total_by_label[label]} | "
                      f"{n_with_gt_by_label[label]} | {overall_by_label[label]:.1f}% |")
    lines.append("")

    lines.append("## Accuracy by category, every model\n")
    header = "| Category | " + " | ".join(loaded.keys()) + " |"
    lines.append(header)
    lines.append("|---|" + "---|" * len(loaded))
    for c in CATEGORIES:
        row = f"| {c} | " + " | ".join(
            f"{by_cat_by_label[l][c]:.0f}%" if by_cat_by_label[l][c] is not None else "n/a" for l in loaded
        ) + " |"
        lines.append(row)
    lines.append("")

    # thinking on/off
    lines.append("## Thinking/reasoning ON vs. OFF (same model)\n")
    any_pair = False
    for base in ["GPT-6 Luna", "Gemini 3.8 Flash", "Gemini 3.5 Flash-Lite", "Claude Haiku 5.5"]:
        off_l = next((l for l in loaded if l.startswith(base) and loaded[l]["thinking"] == "off"), None)
        on_l = next((l for l in loaded if l.startswith(base) and loaded[l]["thinking"] == "on"), None)
        off_a = overall_by_label.get(off_l) if off_l else None
        on_a = overall_by_label.get(on_l) if on_l else None
        if off_a is not None or on_a is not None:
            any_pair = True
            lines.append(f"- **{base}**: off={off_a:.1f}% " if off_a is not None else f"- **{base}**: off=n/a ")
            lines[-1] += f"| on={on_a:.1f}%" if on_a is not None else "| on=n/a"
            lines[-1] += "\n"
    if not any_pair:
        lines.append("(no complete on/off pairs yet)\n")
    lines.append("")

    lines.append("## Open-source vs. commercial; accuracy vs. size (Qwen family)\n")
    qwen_acc = {l: overall_by_label[l] for l, info in loaded.items() if info["family"] == "Qwen2.5-Coder" and overall_by_label.get(l) is not None}
    if qwen_acc:
        trend = sorted(qwen_acc.items(), key=lambda kv: loaded[kv[0]]["size"])
        monotonic = all(trend[i][1] <= trend[i + 1][1] for i in range(len(trend) - 1))
        lines.append(f"Qwen2.5-Coder accuracy by size: " + ", ".join(f"{l}={a:.1f}%" for l, a in trend) + "\n")
        lines.append(f"Accuracy **{'increased monotonically' if monotonic else 'did NOT increase monotonically'}** with size.\n")
    best_oss = max(((l, a) for l, a in overall_by_label.items() if a is not None and not loaded[l]["commercial"]), key=lambda kv: kv[1], default=(None, None))
    best_comm = max(((l, a) for l, a in overall_by_label.items() if a is not None and loaded[l]["commercial"]), key=lambda kv: kv[1], default=(None, None))
    if best_oss[0] and best_comm[0]:
        lines.append(f"\nBest open-source model: **{best_oss[0]}** ({best_oss[1]:.1f}%). "
                      f"Best commercial/API model so far: **{best_comm[0]}** ({best_comm[1]:.1f}%).\n")
    if any(l.startswith("Claude Haiku") for l in loaded):
        lines.append("\n**Caveat:** Claude Haiku is in the same model family as the question generator "
                      "(Claude Sonnet 5). It may have an advantage the other answering models don't have "
                      "(e.g. shared conventions in how Anthropic models phrase/parse this kind of question), "
                      "so its ranking above should be read with that in mind, not as a clean apples-to-apples "
                      "result.\n")
    lines.append("")

    lines.append("## Invalid-answer rates\n")
    lines.append("| Model/setting | Invalid answers |")
    lines.append("|---|---|")
    for label in loaded:
        n_valid = n_valid_by_label[label]
        n_tot = n_total_by_label[label]
        if n_tot == 0:
            lines.append(f"| {label} | n/a (0 answers so far) |")
            continue
        lines.append(f"| {label} | {n_tot - n_valid}/{n_tot} ({100*(n_tot-n_valid)/n_tot:.1f}%) |")
    lines.append("")

    lines.append("## Spend (from results/cost_log.csv and provider dashboards)\n")
    cost_log_path = os.path.join(RESULTS_DIR, "cost_log.csv")
    if os.path.exists(cost_log_path):
        with open(cost_log_path) as f:
            lines.append("```")
            lines.append(f.read().strip())
            lines.append("```")
    else:
        lines.append("(cost_log.csv not yet finalized -- see results/cost_projection.json for the pre-flight "
                      "20-question projections, which showed full-scale OpenAI costs of ~$0.05-0.09, far under "
                      "the $9 cap; Gemini is free-tier only, $0 spend.)\n")
    lines.append("")

    # hardest/easiest examples
    lines.append("## Example questions most models got wrong\n")
    gt_by_id = {q["id"]: q for q in questions}
    wrong_counts = {}
    for label, info in loaded.items():
        for r in info["data"]["results"]:
            q = gt_by_id.get(r["id"])
            if not q or q.get("ground_truth_option") is None:
                continue
            if not r.get("is_correct"):
                wrong_counts[r["id"]] = wrong_counts.get(r["id"], 0) + 1
    ranked_wrong = sorted(wrong_counts.items(), key=lambda kv: -kv[1])[:5]
    for qid, cnt in ranked_wrong:
        q = gt_by_id[qid]
        lines.append(f"### `{qid}` ({q['category']}, task `{q['question_id']}`) -- wrong for {cnt}/{len(loaded)} models\n")
        lines.append(f"**Question:** {q['question']}\n")
        lines.append("```python")
        lines.append(q["solution_code"])
        lines.append("```")
        for letter in ["A", "B", "C", "D"]:
            marker = " <- correct" if letter == q.get("ground_truth_option") else ""
            lines.append(f"- {letter}) {q['options'][letter]}{marker}")
        lines.append("")

    lines.append("## Draft poster sentences (real numbers only)\n")
    if ranked:
        lo = overall_by_label[ranked[-1]]
        hi = overall_by_label[ranked[0]]
        lines.append(f"> Across {len(loaded)} model/setting combinations (open-source models on a single "
                      f"NVIDIA RTX 4000 Ada GPU, plus commercial API models), accuracy on {n_gt} "
                      f"execution-verified AI-generated comprehension questions about real student code ranged "
                      f"from {lo:.0f}% ({ranked[-1]}) to {hi:.0f}% ({ranked[0]}).\n")
    if qwen_acc:
        lines.append(f"> Within the Qwen2.5-Coder family, accuracy rose from "
                      f"{trend[0][1]:.0f}% ({trend[0][0]}) to {trend[-1][1]:.0f}% ({trend[-1][0]}) as model size increased.\n")
    lines.append(f"> The question generator (Claude Sonnet 5), operating one-pass with no self-checking, "
                  f"produced {n_key_wrong} incorrect answer keys out of {n_gt} verifiable questions "
                  f"({100*n_key_wrong/n_gt:.1f}%) across 8 comprehension categories.\n")
    if missing:
        lines.append(f"> ({len(missing)} model/setting(s) were still pending or blocked when this report was "
                      f"generated: {', '.join(missing.keys())}.)\n")

    summary_path = os.path.join(RESULTS_DIR, "summary_v2.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
