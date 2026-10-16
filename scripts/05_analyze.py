"""
Step 5: Analyze and report.

Reads results/questions_verified.json and results/model_answers_*.json
(whichever models succeeded, per results/model_run_log.json), and writes:
  results/questions.csv
  results/summary.md
  results/accuracy_by_category.png
  results/accuracy_by_size.png
"""
import glob
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "results")
QUESTIONS_PATH = os.path.join(RESULTS_DIR, "questions_verified.json")
LOG_PATH = os.path.join(RESULTS_DIR, "model_run_log.json")
SAMPLES_PATH = os.path.join(ROOT, "pilot_data", "sampled_solutions.json")

# model display config: slug -> (label, approx size in B params, family)
MODEL_META = {
    "qwen2.5-coder-3b-instruct": ("Qwen2.5-Coder-3B-Instruct", 3, "Qwen2.5-Coder"),
    "qwen2.5-coder-7b-instruct-awq": ("Qwen2.5-Coder-7B-Instruct-AWQ", 7, "Qwen2.5-Coder"),
    "qwen2.5-coder-14b-instruct-awq": ("Qwen2.5-Coder-14B-Instruct-AWQ", 14, "Qwen2.5-Coder"),
    "deepseek-coder-6.7b-instruct": ("DeepSeek-Coder-6.7B-Instruct", 6.7, "DeepSeek-Coder"),
}
MODEL_ORDER = ["qwen2.5-coder-3b-instruct", "qwen2.5-coder-7b-instruct-awq",
               "qwen2.5-coder-14b-instruct-awq", "deepseek-coder-6.7b-instruct"]

CATEGORIES = ["output", "variable_state", "loop_trace", "control_flow"]

# a clean, colorblind-friendly categorical palette
PALETTE = ["#4E79A7", "#F28E2B", "#59A14F", "#E15759", "#B07AA1"]


def load_model_results():
    hw_log = []
    if os.path.exists(LOG_PATH):
        hw_log = json.load(open(LOG_PATH, encoding="utf-8"))
    loaded = {}
    skipped = {}
    for slug in MODEL_ORDER:
        path = os.path.join(RESULTS_DIR, f"model_answers_{slug}.json")
        entry = next((e for e in hw_log if e["slug"] == slug), None)
        if os.path.exists(path):
            try:
                loaded[slug] = json.load(open(path, encoding="utf-8"))
            except Exception as e:
                skipped[slug] = f"failed to parse results file: {e}"
        elif entry is not None and not entry.get("success"):
            skipped[slug] = entry.get("stderr_tail", "")[-500:] or "non-zero exit"
        else:
            skipped[slug] = "not run / no results file found"
    return loaded, skipped


def write_questions_csv(questions, model_results):
    import csv
    model_slugs = [s for s in MODEL_ORDER if s in model_results]
    out_path = os.path.join(RESULTS_DIR, "questions.csv")

    model_answer_lookup = {}
    for slug, data in model_results.items():
        model_answer_lookup[slug] = {r["id"]: r for r in data["results"]}

    header = ["id", "task_question_id", "student_id", "category", "question",
              "option_A", "option_B", "option_C", "option_D",
              "answer_key", "ground_truth_option", "key_is_correct"]
    for slug in model_slugs:
        label = MODEL_META[slug][0]
        header += [f"{label}_answer", f"{label}_correct"]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for q in questions:
            row = [
                q["id"], q["question_id"], q["student_id"], q["category"], q["question"],
                q["options"]["A"], q["options"]["B"], q["options"]["C"], q["options"]["D"],
                q["answer_key"], q.get("ground_truth_option"), q.get("key_is_correct"),
            ]
            for slug in model_slugs:
                r = model_answer_lookup[slug].get(q["id"])
                if r is None:
                    row += ["", ""]
                else:
                    row += [r["model_answer"], r["is_correct"]]
            w.writerow(row)
    print(f"Wrote {out_path}")
    return out_path


def compute_accuracy_tables(questions, model_results):
    """Returns:
    overall[slug] = pct accuracy over questions with ground truth
    by_cat[slug][cat] = pct accuracy
    """
    gt_by_id = {q["id"]: q.get("ground_truth_option") for q in questions}
    cat_by_id = {q["id"]: q["category"] for q in questions}

    overall = {}
    by_cat = {}
    for slug, data in model_results.items():
        correct = 0
        total = 0
        cat_correct = {c: 0 for c in CATEGORIES}
        cat_total = {c: 0 for c in CATEGORIES}
        for r in data["results"]:
            gt = gt_by_id.get(r["id"])
            if gt is None:
                continue
            total += 1
            cat = cat_by_id[r["id"]]
            cat_total[cat] += 1
            if r["is_correct"]:
                correct += 1
                cat_correct[cat] += 1
        overall[slug] = 100.0 * correct / total if total else None
        by_cat[slug] = {c: (100.0 * cat_correct[c] / cat_total[c] if cat_total[c] else None) for c in CATEGORIES}
    return overall, by_cat


def plot_accuracy_by_category(by_cat, model_results, out_path):
    slugs = [s for s in MODEL_ORDER if s in model_results]
    n_models = len(slugs)
    n_cats = len(CATEGORIES)

    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=150)
    x = np.arange(n_cats)
    width = 0.8 / n_models

    for i, slug in enumerate(slugs):
        vals = [by_cat[slug][c] if by_cat[slug][c] is not None else 0 for c in CATEGORIES]
        offset = (i - (n_models - 1) / 2) * width
        bars = ax.bar(x + offset, vals, width, label=MODEL_META[slug][0], color=PALETTE[i % len(PALETTE)])
        for b, v in zip(bars, vals):
            if v > 0:
                ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.0f}", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels([c.replace("_", " ") for c in CATEGORIES])
    ax.set_ylabel("Accuracy vs. execution ground truth (%)")
    ax.set_ylim(0, 110)
    ax.set_title("MCQ accuracy by question category and model")
    ax.axhline(25, color="gray", linestyle=":", linewidth=1, label="chance (25%)")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_path}")


def plot_accuracy_by_size(overall, model_results, out_path):
    slugs = [s for s in MODEL_ORDER if s in model_results]
    fig, ax = plt.subplots(figsize=(7, 5), dpi=150)

    qwen_slugs = [s for s in slugs if MODEL_META[s][2] == "Qwen2.5-Coder"]
    qwen_slugs.sort(key=lambda s: MODEL_META[s][1])
    if qwen_slugs:
        sizes = [MODEL_META[s][1] for s in qwen_slugs]
        accs = [overall[s] for s in qwen_slugs]
        ax.plot(sizes, accs, "-o", color=PALETTE[0], label="Qwen2.5-Coder (AWQ for 7B/14B)", linewidth=2, markersize=8)
        for s, a in zip(sizes, accs):
            ax.annotate(f"{a:.0f}%", (s, a), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9)

    other_slugs = [s for s in slugs if MODEL_META[s][2] != "Qwen2.5-Coder"]
    for i, s in enumerate(other_slugs):
        size = MODEL_META[s][1]
        acc = overall[s]
        ax.scatter([size], [acc], color=PALETTE[(i + 1) % len(PALETTE)], s=90, zorder=5, label=MODEL_META[s][0])
        ax.annotate(f"{acc:.0f}%", (size, acc), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9)

    ax.axhline(25, color="gray", linestyle=":", linewidth=1, label="chance (25%)")
    ax.set_xlabel("Model size (billion parameters)")
    ax.set_ylabel("Overall accuracy vs. execution ground truth (%)")
    ax.set_ylim(0, 110)
    ax.set_title("Overall MCQ accuracy vs. model size")
    ax.legend(fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_path}")


def find_wrong_examples(questions, model_results, n=3):
    """Find up to n questions that ALL (or most) models got wrong, with code snippets."""
    gt_by_id = {q["id"]: q for q in questions}
    wrong_counts = {}
    for slug, data in model_results.items():
        for r in data["results"]:
            if gt_by_id[r["id"]].get("ground_truth_option") is None:
                continue
            if not r["is_correct"]:
                wrong_counts[r["id"]] = wrong_counts.get(r["id"], 0) + 1

    n_models = len(model_results)
    ranked = sorted(wrong_counts.items(), key=lambda kv: -kv[1])
    examples = []
    for qid, cnt in ranked[:n]:
        q = gt_by_id[qid]
        per_model = {}
        for slug, data in model_results.items():
            r = next((x for x in data["results"] if x["id"] == qid), None)
            if r:
                per_model[MODEL_META[slug][0]] = r["model_answer"]
        examples.append({
            "id": qid,
            "task": q["question_id"],
            "category": q["category"],
            "question": q["question"],
            "options": q["options"],
            "correct_answer": q.get("ground_truth_option"),
            "wrong_count": cnt,
            "n_models": n_models,
            "model_answers": per_model,
            "code": (q.get("harness_code", "").strip() + "\n\n" + q["solution_code"]).strip(),
        })
    return examples


def main():
    questions = json.load(open(QUESTIONS_PATH, encoding="utf-8"))
    samples = json.load(open(SAMPLES_PATH, encoding="utf-8"))
    model_results, skipped = load_model_results()

    if not model_results:
        print("No model results found yet -- run 04_run_all_models.py first.")
        return

    write_questions_csv(questions, model_results)
    overall, by_cat = compute_accuracy_tables(questions, model_results)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    plot_accuracy_by_category(by_cat, model_results, os.path.join(RESULTS_DIR, "accuracy_by_category.png"))
    plot_accuracy_by_size(overall, model_results, os.path.join(RESULTS_DIR, "accuracy_by_size.png"))

    # ---- summary.md ----
    n_total_q = len(questions)
    n_gt = sum(1 for q in questions if q.get("ground_truth_option") is not None)
    n_key_wrong = sum(1 for q in questions if q.get("key_is_correct") is False)
    n_tasks = len(set(s["question_id"] for s in samples))
    n_solutions = len(samples)

    cat_gt_counts = {c: sum(1 for q in questions if q["category"] == c) for c in CATEGORIES}
    cat_gt_verified = {c: sum(1 for q in questions if q["category"] == c and q.get("ground_truth_option") is not None) for c in CATEGORIES}

    # hardest / easiest category, averaged over models that ran
    cat_avg = {}
    for c in CATEGORIES:
        vals = [by_cat[s][c] for s in model_results if by_cat[s][c] is not None]
        cat_avg[c] = sum(vals) / len(vals) if vals else None
    hardest_cat = min(cat_avg, key=lambda c: cat_avg[c] if cat_avg[c] is not None else 1e9)
    easiest_cat = max(cat_avg, key=lambda c: cat_avg[c] if cat_avg[c] is not None else -1e9)

    qwen_slugs_present = [s for s in ["qwen2.5-coder-3b-instruct", "qwen2.5-coder-7b-instruct-awq", "qwen2.5-coder-14b-instruct-awq"] if s in model_results]
    size_trend_note = ""
    if len(qwen_slugs_present) >= 2:
        accs = [(MODEL_META[s][1], overall[s]) for s in qwen_slugs_present]
        accs.sort()
        monotonic_increase = all(accs[i][1] <= accs[i + 1][1] for i in range(len(accs) - 1))
        size_trend_note = (
            "accuracy increased monotonically with model size within the Qwen2.5-Coder family"
            if monotonic_increase else
            "accuracy did NOT increase monotonically with model size within the Qwen2.5-Coder family"
        )

    examples = find_wrong_examples(questions, model_results, n=3)

    lines = []
    lines.append("# Pilot results: Can AI models answer AI-generated MCQs about real student code?\n")
    lines.append("## Hardware & runtime\n")
    lines.append("- GPU: **NVIDIA RTX 4000 Ada Generation, 20475 MiB (~20 GB) VRAM**, driver CUDA 13.0\n")
    lines.append("- Python 3.10.12, vLLM 0.31.0, PyTorch 2.13.0+cu130\n")
    lines.append("")
    lines.append("| Model | Loaded? | Load time (s) | Generation time for 100 Q (s) | Total wall time (s) |")
    lines.append("|---|---|---|---|---|")
    for slug in MODEL_ORDER:
        label = MODEL_META[slug][0]
        if slug in model_results:
            d = model_results[slug]
            lines.append(f"| {label} | yes | {d['load_time_seconds']:.1f} | {d['generation_time_seconds']:.1f} | {d['total_wall_time_seconds']:.1f} |")
        else:
            reason = skipped.get(slug, "unknown")
            reason_short = reason.splitlines()[-1][:200] if reason else "unknown"
            lines.append(f"| {label} | **no** | - | - | - (skipped: {reason_short}) |")
    lines.append("")

    lines.append("## Dataset\n")
    lines.append(f"- Source: *Dataset of Student Solutions to Algorithm and Data Structure Programming "
                  f"Assignments* (Petersen-Frey et al., LREC 2022, Universität Hamburg), Python solutions only.\n")
    lines.append(f"- **{n_solutions} student solutions** sampled (seed=42), spanning **{n_tasks} distinct tasks** "
                  f"(21 of the 21 available Python tasks in the dataset were covered).\n")
    lines.append(f"- **{n_total_q} questions** generated (4 per solution x 25 solutions), split evenly across the "
                  f"4 categories ({n_total_q // 4} each): output, variable_state, loop_trace, control_flow.\n")
    lines.append("")

    lines.append("## Answer-key verification (Step 3)\n")
    lines.append(f"- **{n_gt}/{n_total_q} ({100*n_gt/n_total_q:.1f}%)** of generated questions had a verifiable "
                  f"execution ground truth (student code + verification snippet ran successfully and printed a "
                  f"value matching one of the 4 options).\n")
    lines.append(f"- **{n_key_wrong}/{n_gt} ({100*n_key_wrong/n_gt:.1f}%)** of the generator's (Claude's) own "
                  f"hand-written answer keys were WRONG when checked against execution -- i.e. the "
                  f"generator picked the wrong option as \"correct\" when first writing the question, one pass, "
                  f"no self-checking, by design (matching the AutoMCQ-style protocol). This was left uncorrected "
                  f"per the pilot's rules; accuracy below is scored against the execution ground truth, not the "
                  f"original answer key.\n")
    for q in questions:
        if q.get("key_is_correct") is False:
            lines.append(f"  - Example: `{q['id']}` ({q['category']}, task {q['question_id']}): generator's answer "
                          f"key was **{q['answer_key']}**, but execution showed the true answer is "
                          f"**{q['ground_truth_option']}** (code printed `{q['raw_stdout']}`).\n")
    lines.append("")
    lines.append("### Ground-truth verifiability by category\n")
    lines.append("| Category | Questions | With verifiable ground truth |")
    lines.append("|---|---|---|")
    for c in CATEGORIES:
        lines.append(f"| {c} | {cat_gt_counts[c]} | {cat_gt_verified[c]} ({100*cat_gt_verified[c]/cat_gt_counts[c]:.0f}%) |")
    lines.append("")

    lines.append("## Model accuracy (Step 4, scored against execution ground truth)\n")
    lines.append("| Model | Valid answers | Overall accuracy |")
    lines.append("|---|---|---|")
    for slug in MODEL_ORDER:
        if slug not in model_results:
            continue
        d = model_results[slug]
        lines.append(f"| {MODEL_META[slug][0]} | {d['n_valid_answers']}/{d['n_questions']} | {overall[slug]:.1f}% |")
    lines.append("")

    lines.append("### Accuracy per category per model\n")
    header = "| Category | " + " | ".join(MODEL_META[s][0] for s in MODEL_ORDER if s in model_results) + " |"
    sep = "|---|" + "---|" * len(model_results)
    lines.append(header)
    lines.append(sep)
    for c in CATEGORIES:
        row = f"| {c} | " + " | ".join(
            f"{by_cat[s][c]:.1f}%" if by_cat[s][c] is not None else "n/a"
            for s in MODEL_ORDER if s in model_results
        ) + " |"
        lines.append(row)
    lines.append("")

    lines.append(f"**Hardest category (lowest average accuracy across models): `{hardest_cat}`** "
                  f"({cat_avg[hardest_cat]:.1f}% avg)\n")
    lines.append(f"**Easiest category (highest average accuracy across models): `{easiest_cat}`** "
                  f"({cat_avg[easiest_cat]:.1f}% avg)\n")
    if size_trend_note:
        lines.append(f"\n**Model size trend:** {size_trend_note} "
                      f"({', '.join(f'{MODEL_META[s][0]}={overall[s]:.1f}%' for s in qwen_slugs_present)}).\n")
    lines.append("")

    lines.append("## Example questions the models got wrong\n")
    for ex in examples:
        lines.append(f"### `{ex['id']}` ({ex['category']}, task `{ex['task']}`) -- wrong for "
                      f"{ex['wrong_count']}/{ex['n_models']} models\n")
        lines.append(f"**Question:** {ex['question']}\n")
        lines.append("```python")
        lines.append(ex["code"])
        lines.append("```")
        for letter in ["A", "B", "C", "D"]:
            marker = " <- correct (execution ground truth)" if letter == ex["correct_answer"] else ""
            lines.append(f"- {letter}) {ex['options'][letter]}{marker}")
        lines.append("")
        lines.append("Model answers: " + ", ".join(f"{m}={a}" for m, a in ex["model_answers"].items()))
        lines.append("")

    lines.append("## Draft abstract sentences (real numbers only)\n")
    acc_vals = [overall[s] for s in model_results]
    lo, hi = (min(acc_vals), max(acc_vals)) if acc_vals else (None, None)
    best_slug = max(overall, key=lambda s: overall[s])
    lines.append(
        f"> In a pilot of {n_total_q} AI-generated multiple-choice comprehension questions "
        f"({n_gt} with execution-verified ground truth, {100*n_gt/n_total_q:.0f}%) about {n_solutions} real "
        f"student Python solutions to {n_tasks} distinct algorithms/data-structures assignments, open-source "
        f"code models ({', '.join(MODEL_META[s][0] for s in model_results)}, {len(model_results)} model(s), "
        f"{int(min(MODEL_META[s][1] for s in model_results))}B-{int(max(MODEL_META[s][1] for s in model_results))}B parameters) "
        f"run locally on a single NVIDIA RTX 4000 Ada (20GB) answered {lo:.0f}-{hi:.0f}% of verifiable questions correctly.\n"
    )
    lines.append(
        f"> Questions about **{hardest_cat.replace('_',' ')}** were hardest "
        f"({cat_avg[hardest_cat]:.0f}% average accuracy) and questions about **{easiest_cat.replace('_',' ')}** "
        f"were easiest ({cat_avg[easiest_cat]:.0f}% average accuracy) across models.\n"
    )
    lines.append(
        f"> {best_slug and MODEL_META[best_slug][0]} achieved the highest overall accuracy at {overall[best_slug]:.0f}%; "
        f"the pilot's own one-pass question generator produced {n_key_wrong} incorrect answer key(s) out of "
        f"{n_gt} verifiable questions ({100*n_key_wrong/n_gt:.0f}%), itself a finding about automated MCQ generation.\n"
    )

    if skipped:
        lines.append("\n## Models skipped or failed\n")
        for slug, reason in skipped.items():
            if slug in model_results:
                continue
            lines.append(f"- **{MODEL_META[slug][0]}**: {reason.splitlines()[-1][:300] if reason else 'unknown reason'}\n")

    summary_path = os.path.join(RESULTS_DIR, "summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
