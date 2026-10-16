"""
Step 4 (v2, per-model): same design as the original pilot's
04_run_one_model.py (one model per OS process, vLLM, temperature=0,
max_tokens~10, chat template, robust letter parsing), pointed at the
expanded questions_v2_verified.json (8 categories, ~1000 questions) and
using harness_code_display (NOT harness_code, which may be larger/include
things only needed for execution) as the code shown to the model, so a
bundled reference solution never leaks into what the model sees.

Usage:
    python 04_run_one_model_v2.py <model_id> <out_path> [--quantization awq] [--dtype float16]
"""
import argparse
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUESTIONS_PATH = os.path.join(ROOT, "results", "questions_v2_verified.json")

LETTER_RE = re.compile(r"\b([ABCD])\b")


def build_prompt(q):
    code_parts = []
    display_harness = q.get("harness_code_display", "")
    if display_harness and display_harness.strip():
        code_parts.append("# --- supporting class definitions (not written by the student) ---")
        code_parts.append(display_harness.strip())
    code_parts.append(q["solution_code"].strip())
    code = "\n\n".join(code_parts)

    opts = q["options"]
    user_msg = (
        "You are given a Python function written by a student, and a multiple-choice "
        "question about its exact behavior on a specific input. Read the code and the "
        "question carefully, then answer with a single letter only: A, B, C, or D. Do "
        "not explain your reasoning.\n\n"
        "Student code:\n```python\n" + code + "\n```\n\n"
        f"Question: {q['question']}\n\n"
        f"A) {opts['A']}\n"
        f"B) {opts['B']}\n"
        f"C) {opts['C']}\n"
        f"D) {opts['D']}\n\n"
        "Answer (single letter only):"
    )
    return [{"role": "user", "content": user_msg}]


def parse_letter(text):
    if not text:
        return None
    text = text.strip()
    m = re.match(r"^\s*\(?([ABCD])\)?[\.\:\)]?\s*$", text, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    m = LETTER_RE.search(text.upper())
    if m:
        return m.group(1)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model_id")
    ap.add_argument("out_path")
    ap.add_argument("--quantization", default=None)
    ap.add_argument("--dtype", default="auto")
    ap.add_argument("--max-model-len", type=int, default=4096)
    ap.add_argument("--gpu-mem-util", type=float, default=0.85)
    ap.add_argument("--trust-remote-code", action="store_true", default=True)
    args = ap.parse_args()

    questions = json.load(open(QUESTIONS_PATH, encoding="utf-8"))

    from vllm import LLM, SamplingParams

    llm_kwargs = dict(
        model=args.model_id,
        max_model_len=args.max_model_len,
        gpu_memory_utilization=args.gpu_mem_util,
        dtype=args.dtype,
        trust_remote_code=True,
    )
    if args.quantization:
        llm_kwargs["quantization"] = args.quantization

    load_start = time.time()
    llm = LLM(**llm_kwargs)
    load_time = time.time() - load_start

    sampling_params = SamplingParams(temperature=0, max_tokens=10)

    message_lists = [build_prompt(q) for q in questions]

    gen_start = time.time()
    outputs = llm.chat(message_lists, sampling_params=sampling_params)
    gen_time = time.time() - gen_start

    results = []
    n_correct = 0
    n_valid = 0
    cat_stats = {}
    for q, out in zip(questions, outputs):
        raw_text = out.outputs[0].text if out.outputs else ""
        letter = parse_letter(raw_text)
        is_valid = letter is not None
        gt = q.get("ground_truth_option")
        is_correct = (letter == gt) if (is_valid and gt is not None) else False
        if is_valid:
            n_valid += 1
        if is_correct:
            n_correct += 1
        cat = q["category"]
        cs = cat_stats.setdefault(cat, {"n_with_gt": 0, "n_correct": 0, "n_valid": 0, "n_total": 0})
        cs["n_total"] += 1
        if is_valid:
            cs["n_valid"] += 1
        if gt is not None:
            cs["n_with_gt"] += 1
            if is_correct:
                cs["n_correct"] += 1
        results.append({
            "id": q["id"],
            "category": q["category"],
            "question_id": q["question_id"],
            "answer_key": q["answer_key"],
            "ground_truth_option": gt,
            "model_raw_output": raw_text,
            "model_answer": letter if is_valid else "invalid",
            "is_valid": is_valid,
            "is_correct": is_correct,
        })

    n_with_gt = sum(1 for q in questions if q.get("ground_truth_option") is not None)

    summary = {
        "model_id": args.model_id,
        "quantization": args.quantization,
        "dtype": args.dtype,
        "load_time_seconds": load_time,
        "generation_time_seconds": gen_time,
        "total_wall_time_seconds": load_time + gen_time,
        "n_questions": len(questions),
        "n_with_ground_truth": n_with_gt,
        "n_valid_answers": n_valid,
        "n_correct": n_correct,
        "accuracy_overall_pct": 100.0 * n_correct / n_with_gt if n_with_gt else None,
        "accuracy_by_category_pct": {
            c: (100.0 * s["n_correct"] / s["n_with_gt"] if s["n_with_gt"] else None)
            for c, s in cat_stats.items()
        },
        "results": results,
    }

    os.makedirs(os.path.dirname(args.out_path), exist_ok=True)
    with open(args.out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"MODEL {args.model_id}: load={load_time:.1f}s gen={gen_time:.1f}s "
          f"valid={n_valid}/{len(questions)} correct={n_correct}/{n_with_gt} "
          f"({summary['accuracy_overall_pct']:.1f}%)")


if __name__ == "__main__":
    main()
