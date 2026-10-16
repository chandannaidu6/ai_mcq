"""
Step 3 (v2): execution-based verification for the expanded 8-category
question set (results/questions_v2.json), same approach as the original
pilot's 03_verify_answer_keys.py, extended with:
  - network access disabled in the verification subprocess (NETWORK_BLOCK_CODE)
  - per-category reporting
Reuses the same subprocess-per-question / 5s-timeout / option-text-matching
design. Never modifies a question's answer_key -- wrong keys are recorded
and reported (results/questions_v2_verified.json), not fixed.
"""
import ast
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from harness import TRACER_CODE, NETWORK_BLOCK_CODE  # noqa: E402

ROOT = os.path.dirname(HERE)
QUESTIONS_PATH = os.path.join(ROOT, "results", "questions_v2.json")
OUT_PATH = os.path.join(ROOT, "results", "questions_v2_verified.json")

TIMEOUT_SECONDS = 5


def try_numeric_match(printed, option_text):
    p = printed.strip()
    o = option_text.strip()
    if p == o:
        return True
    try:
        pv = ast.literal_eval(p)
        ov = ast.literal_eval(o)
        if isinstance(pv, int) and isinstance(ov, int):
            return pv == ov
        if isinstance(pv, (int, float)) and isinstance(ov, (int, float)):
            return float(pv) == float(ov)
        return pv == ov
    except Exception:
        return False


def match_option(printed, options):
    for key in ["A", "B", "C", "D"]:
        if try_numeric_match(printed, options[key]):
            return key
    return None


def run_one(question):
    # Some of the dataset's own testcode (reused verbatim as verification_code
    # or inside it) references `__student_answer__`, a string the REAL grading
    # harness defines (the raw submission text, used e.g. to check "no import
    # used"). We never showed that definition since we only reuse the tester's
    # PRE-submission preamble -- define it here so such tests still run.
    student_answer_def = "__student_answer__ = " + repr(question["solution_code"])
    full_code = (
        question.get("pre_harness_code", "")
        + question["solution_code"]
        + "\n\n"
        + question.get("harness_code", "")
        + "\n\n"
        + student_answer_def
        + "\n\n"
        + NETWORK_BLOCK_CODE
        + "\n\n"
        + TRACER_CODE
        + "\n\n"
        + question["verification_code"]
        + "\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, dir=tempfile.gettempdir()) as tf:
        tf.write(full_code)
        tmp_path = tf.name
    try:
        proc = subprocess.run(
            [sys.executable, "-I", tmp_path],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        if proc.returncode != 0:
            return None, f"EXIT_{proc.returncode}: {stderr[-500:]}"
        if not stdout:
            return None, f"EMPTY_STDOUT; stderr={stderr[-500:]}"
        lines = [l for l in stdout.splitlines() if l.strip()]
        result_line = lines[-1] if lines else ""
        return result_line, None
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT"
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def main():
    questions = json.load(open(QUESTIONS_PATH, encoding="utf-8"))
    n_total = len(questions)
    n_with_gt = 0
    n_key_wrong = 0
    n_exec_error = 0
    cat_stats = {}

    for i, q in enumerate(questions):
        printed, error = run_one(q)
        q["raw_stdout"] = printed
        q["exec_error"] = error
        cat = q["category"]
        cs = cat_stats.setdefault(cat, {"total": 0, "with_gt": 0, "key_wrong": 0, "exec_error": 0})
        cs["total"] += 1

        if error is not None:
            q["ground_truth_option"] = None
            q["key_is_correct"] = None
            n_exec_error += 1
            cs["exec_error"] += 1
            continue
        gt_option = match_option(printed, q["options"])
        q["ground_truth_option"] = gt_option
        if gt_option is None:
            q["key_is_correct"] = None
            continue
        n_with_gt += 1
        cs["with_gt"] += 1
        q["key_is_correct"] = (gt_option == q["answer_key"])
        if not q["key_is_correct"]:
            n_key_wrong += 1
            cs["key_wrong"] += 1

        if (i + 1) % 100 == 0:
            print(f"  ...verified {i+1}/{n_total}")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)

    print(f"\nTotal questions: {n_total}")
    print(f"With verifiable ground truth: {n_with_gt} ({100*n_with_gt/n_total:.1f}%)")
    print(f"Execution errors / no ground truth: {n_exec_error}")
    print(f"Answer keys WRONG: {n_key_wrong}" +
          (f" ({100*n_key_wrong/n_with_gt:.1f}% of verifiable)" if n_with_gt else ""))
    print(f"Wrote {OUT_PATH}")

    print("\n--- Per-category breakdown ---")
    print(f"{'category':22s} {'total':>6s} {'with_gt':>8s} {'exec_err':>9s} {'key_wrong':>10s} {'wrong%':>7s}")
    for cat, cs in sorted(cat_stats.items()):
        wrong_pct = f"{100*cs['key_wrong']/cs['with_gt']:.1f}%" if cs["with_gt"] else "n/a"
        print(f"{cat:22s} {cs['total']:6d} {cs['with_gt']:8d} {cs['exec_error']:9d} {cs['key_wrong']:10d} {wrong_pct:>7s}")


if __name__ == "__main__":
    main()
