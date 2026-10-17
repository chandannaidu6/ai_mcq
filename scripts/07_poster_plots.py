"""
Poster-specific charts, built on the commercial-model comparison only (the
open-source GPU models are excluded per the poster's scope -- see
results/metadata.json scope_changes for why).

Uses the dataviz skill's validated default categorical palette (8 slots,
passes CVD/contrast checks on the adjacent pairlist) and single-hue
sequential blue ramp for magnitude/heatmap encodings. Three categorical
slots (aqua, yellow, magenta) sit under 3:1 contrast on a light surface,
so every chart using them carries direct value labels (the skill's
"relief" requirement) rather than relying on color alone.
"""
import csv
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "results")
QUESTIONS_PATH = os.path.join(RESULTS_DIR, "questions_v2_verified.json")

CATEGORIES = ["output", "variable_state", "loop_trace", "control_flow",
              "call_count", "edge_case", "code_modification", "data_structure_state"]

# validated 8-slot categorical palette (dataviz skill reference palette, light mode)
CAT_PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
# sequential blue ramp, 100 (near-zero) -> 700 (max), light->dark
SEQ_BLUE = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
            "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e2dc"

# Commercial models only, in a fixed display order. (slug_glob, display_label)
COMMERCIAL_MODELS = [
    ("model_answers_v2_openai_gpt-6-luna_reasoning-none.json", "GPT-6 Luna (reasoning off)"),
    ("model_answers_v2_openai_gpt-6-luna_reasoning-medium.json", "GPT-6 Luna (reasoning on)"),
    ("model_answers_v2_openai_gpt-6-astra_reasoning-low.json", "GPT-6 Astra (reasoning low)"),
    ("model_answers_v2_claude-haiku-5.5_thinking-off.json", "Claude Haiku 5.5 (thinking off)"),
    ("model_answers_v2_claude-haiku-5.5_thinking-on.json", "Claude Haiku 5.5 (thinking on)"),
    ("model_answers_v2_claude-opus-5_thinking-off.json", "Claude Opus 5 (thinking off)"),
    ("model_answers_v2_claude-opus-5_thinking-on.json", "Claude Opus 5 (thinking on)"),
]


def load_models():
    loaded = {}
    for fname, label in COMMERCIAL_MODELS:
        path = os.path.join(RESULTS_DIR, fname)
        if os.path.exists(path):
            loaded[label] = json.load(open(path, encoding="utf-8"))
    return loaded


def compute_accuracy(data):
    results = data["results"]
    gt_by_id = {r["id"]: r.get("ground_truth_option") for r in results}
    cat_by_id = {r["id"]: r["category"] for r in results}
    correct = total = 0
    cat_correct = {c: 0 for c in CATEGORIES}
    cat_total = {c: 0 for c in CATEGORIES}
    n_valid = sum(1 for r in results if r.get("is_valid"))
    for r in results:
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
    return overall, by_cat, n_valid, len(results)


def style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=TEXT_SECONDARY)
    ax.xaxis.label.set_color(TEXT_SECONDARY)
    ax.yaxis.label.set_color(TEXT_SECONDARY)
    ax.title.set_color(TEXT_PRIMARY)


def plot_category_difficulty(by_cat_by_label, out_path):
    """Mean accuracy per category across all commercial models, sorted --
    directly answers 'which question types are hardest'."""
    cat_avg = {c: np.mean([by_cat_by_label[l][c] for l in by_cat_by_label if by_cat_by_label[l][c] is not None])
               for c in CATEGORIES}
    # barh renders index 0 at the BOTTOM and the last index at the TOP, so to
    # get the hardest (lowest accuracy) category at the top of the chart, the
    # list must end with it: easiest-first (descending accuracy) order.
    ordered = sorted(cat_avg.items(), key=lambda kv: -kv[1])
    labels = [c.replace("_", " ") for c, v in ordered]
    vals = [v for c, v in ordered]

    fig, ax = plt.subplots(figsize=(8, 5.3), dpi=200)
    y = np.arange(len(labels))
    # single series (one magnitude per category) -> one hue, not categorical identity
    bars = ax.barh(y, vals, color=SEQ_BLUE[7], height=0.62)
    for b, v in zip(bars, vals):
        ax.text(v + 1.5, b.get_y() + b.get_height() / 2, f"{v:.0f}%", va="center", fontsize=10, color=TEXT_PRIMARY)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=11, color=TEXT_PRIMARY)
    ax.axvline(25, color=TEXT_SECONDARY, linestyle=":", linewidth=1)
    ax.text(27, len(labels) - 0.45, "chance (25%)", fontsize=8, color=TEXT_SECONDARY, va="top", ha="left")
    ax.set_xlim(0, 105)
    ax.set_ylim(-0.7, len(labels) - 0.3)
    ax.set_xlabel("Mean accuracy across commercial models (%)")
    ax.set_title("Which question types are hardest?", fontsize=15, fontweight="bold", pad=14)
    ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    style_ax(ax)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {out_path}")


def plot_heatmap(by_cat_by_label, out_path):
    labels = list(by_cat_by_label.keys())
    matrix = np.array([[by_cat_by_label[l][c] if by_cat_by_label[l][c] is not None else np.nan for c in CATEGORIES]
                        for l in labels])

    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("seq_blue", SEQ_BLUE)

    fig, ax = plt.subplots(figsize=(11, 0.62 * len(labels) + 2), dpi=200)
    im = ax.imshow(matrix, cmap=cmap, vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(CATEGORIES)))
    ax.set_xticklabels([c.replace("_", "\n") for c in CATEGORIES], fontsize=9, color=TEXT_PRIMARY)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=10, color=TEXT_PRIMARY)
    for i in range(len(labels)):
        for j in range(len(CATEGORIES)):
            v = matrix[i, j]
            if np.isnan(v):
                ax.text(j, i, "n/a", ha="center", va="center", fontsize=8, color=TEXT_SECONDARY)
                continue
            txt_color = "white" if v > 55 else TEXT_PRIMARY
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=9, color=txt_color)
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("Accuracy (%)", color=TEXT_SECONDARY)
    cbar.ax.tick_params(colors=TEXT_SECONDARY)
    ax.set_title("Accuracy by category x model", fontsize=15, fontweight="bold", color=TEXT_PRIMARY, pad=12)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {out_path}")


def plot_generator_reliability(questions, out_path):
    cat_gt_counts = {c: sum(1 for q in questions if q["category"] == c) for c in CATEGORIES}
    cat_gt_verified = {c: sum(1 for q in questions if q["category"] == c and q.get("ground_truth_option") is not None) for c in CATEGORIES}
    cat_key_wrong = {c: sum(1 for q in questions if q["category"] == c and q.get("key_is_correct") is False) for c in CATEGORIES}

    verifiable_pct = [100 * cat_gt_verified[c] / cat_gt_counts[c] for c in CATEGORIES]
    wrong_pct = [100 * cat_key_wrong[c] / cat_gt_verified[c] if cat_gt_verified[c] else 0 for c in CATEGORIES]

    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=200)
    x = np.arange(len(CATEGORIES))
    width = 0.36
    b1 = ax.bar(x - width / 2, verifiable_pct, width, label="Had verifiable ground truth", color=CAT_PALETTE[0])
    b2 = ax.bar(x + width / 2, wrong_pct, width, label="Generator's answer key was wrong", color=CAT_PALETTE[7])
    for b in list(b1) + list(b2):
        h = b.get_height()
        ax.text(b.get_x() + b.get_width() / 2, h + 1.5, f"{h:.0f}%", ha="center", fontsize=8, color=TEXT_PRIMARY)
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace("_", "\n") for c in CATEGORIES], fontsize=9)
    ax.set_ylabel("% of generated questions")
    ax.set_ylim(0, 110)
    ax.set_title("How reliable was the AI question generator?", fontsize=15, fontweight="bold")
    ax.legend(fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=False)
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    style_ax(ax)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {out_path}")


def plot_validity_vs_accuracy(loaded, overall_by_label, out_path):
    points = []
    for i, (label, data) in enumerate(loaded.items()):
        overall, by_cat, n_valid, n_total = compute_accuracy(data)
        invalid_pct = 100 * (n_total - n_valid) / n_total
        points.append((label, invalid_pct, overall, CAT_PALETTE[i % len(CAT_PALETTE)]))

    xmax = max(10, max(p[1] for p in points) * 1.15)

    fig, ax = plt.subplots(figsize=(9, 7), dpi=200)
    for label, x, y, color in points:
        ax.scatter(x, y, s=170, color=color, zorder=5, edgecolor="white", linewidth=1.2)

    # greedily stagger labels that are close together in (x,y) display space so
    # text never overlaps -- a label collision is an anti-pattern this skill
    # flags explicitly, so this isn't optional polish.
    placed = []  # list of (x_data, y_data_offset_used)
    for label, x, y, color in points:
        base_dx, base_dy = 10, 10
        dx, dy = base_dx, base_dy
        attempt = 0
        while any(abs((x + dx * 0.09) - px) < 2.0 and abs(y - py) < 5.0 for px, py in placed) and attempt < 6:
            attempt += 1
            dy = base_dy - attempt * 16  # drop the label further down each collision
        placed.append((x + dx * 0.09, y))
        ax.annotate(label, (x, y), textcoords="offset points", xytext=(dx, dy),
                    fontsize=9, color=TEXT_PRIMARY, ha="left",
                    arrowprops=dict(arrowstyle="-", color=GRID, lw=0.8) if dy != base_dy else None)

    ax.axhline(25, color=TEXT_SECONDARY, linestyle=":", linewidth=1)
    ax.text(xmax * 0.99, 26, "chance (25%)", fontsize=8, color=TEXT_SECONDARY, va="bottom", ha="right")
    ax.set_xlabel("Invalid (unparseable) answer rate (%)")
    ax.set_ylabel("Accuracy on verifiable questions (%)")
    ax.set_ylim(0, 108)
    ax.set_xlim(-xmax * 0.03, xmax)
    ax.set_title("Does format compliance track comprehension?", fontsize=15, fontweight="bold", pad=14)
    ax.grid(color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    style_ax(ax)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {out_path}")


def main():
    questions = json.load(open(QUESTIONS_PATH, encoding="utf-8"))
    loaded = load_models()
    if not loaded:
        print("No commercial model results found yet.")
        return
    print(f"Loaded {len(loaded)} commercial model/settings: {list(loaded.keys())}")

    overall_by_label = {}
    by_cat_by_label = {}
    for label, data in loaded.items():
        overall, by_cat, n_valid, n_total = compute_accuracy(data)
        overall_by_label[label] = overall
        by_cat_by_label[label] = by_cat

    plot_category_difficulty(by_cat_by_label, os.path.join(RESULTS_DIR, "poster_category_difficulty.png"))
    plot_heatmap(by_cat_by_label, os.path.join(RESULTS_DIR, "poster_heatmap.png"))
    plot_generator_reliability(questions, os.path.join(RESULTS_DIR, "poster_generator_reliability.png"))
    plot_validity_vs_accuracy(loaded, overall_by_label, os.path.join(RESULTS_DIR, "poster_validity_vs_accuracy.png"))


if __name__ == "__main__":
    main()
