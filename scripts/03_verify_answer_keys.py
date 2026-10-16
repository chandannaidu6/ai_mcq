"""
Step 3: Verify answer keys by execution.

For each question, assemble:
    student solution_code + harness_code + TRACER_CODE + verification_code
run it in a subprocess with a 5s timeout, capture stdout, and map the printed
result to whichever option's text matches it (exact match after normalizing
whitespace; falls back to numeric-aware comparison). Records:
    ground_truth_output : raw stdout
    ground_truth_option : "A"/"B"/"C"/"D"/None (None if no match or error/timeout)
    key_is_correct       : whether the hand-authored answer_key matches ground_truth_option
    exec_error           : any exception/timeout info (for diagnostics)

Per the pilot's rules: wrong keys are NOT fixed here, only recorded/reported.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from harness import TRACER_CODE  # noqa: E402

ROOT = os.path.dirname(HERE)
QUESTIONS_PATH = os.path.join(ROOT, "results", "questions.json")
OUT_PATH = os.path.join(ROOT, "results", "questions_verified.json")

TIMEOUT_SECONDS = 5


def try_numeric_match(printed, option_text):
    """Compare printed output to an option's text, tolerating int/float formatting
    differences (e.g. '220' vs '220.0') and python literal forms (e.g. True/False,
    lists). Returns True if they represent the same value."""
    p = printed.strip()
    o = option_text.strip()
    if p == o:
        return True
    # try evaluating both as python literals and compare
    try:
        import ast
        pv = ast.literal_eval(p)
        ov = ast.literal_eval(o)
        if isinstance(pv, int) and isinstance(ov, int):
            # exact integer comparison -- casting huge ints (>2**53) to float
            # silently loses precision and can make genuinely different
            # numbers compare equal, so never float() two ints.
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
    full_code = (
        question.get("pre_harness_code", "")
        + question["solution_code"]
        + "\n\n"
        + question.get("harness_code", "")
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
            return None, f"EXIT_{proc.returncode}: {stderr[-500:]}", full_code
        if not stdout:
            return None, f"EMPTY_STDOUT; stderr={stderr[-500:]}", full_code
        # take the LAST non-empty printed line as the result (in case of multiple prints)
        lines = [l for l in stdout.splitlines() if l.strip()]
        result_line = lines[-1] if lines else ""
        return result_line, None, full_code
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT", full_code
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def main():
    questions = json.load(open(QUESTIONS_PATH, encoding="utf-8"))

    n_total = len(questions)
    n_with_ground_truth = 0
    n_key_wrong = 0
    n_exec_error = 0

    for q in questions:
        printed, error, full_code = run_one(q)
        q["raw_stdout"] = printed
        q["exec_error"] = error
        if error is not None:
            q["ground_truth_option"] = None
            n_exec_error += 1
            continue
        gt_option = match_option(printed, q["options"])
        q["ground_truth_option"] = gt_option
        if gt_option is None:
            continue
        n_with_ground_truth += 1
        q["key_is_correct"] = (gt_option == q["answer_key"])
        if not q["key_is_correct"]:
            n_key_wrong += 1

    for q in questions:
        if "key_is_correct" not in q:
            q["key_is_correct"] = None

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)

    print(f"Total questions: {n_total}")
    print(f"With verifiable ground truth: {n_with_ground_truth} ({100*n_with_ground_truth/n_total:.1f}%)")
    print(f"Execution errors / no ground truth: {n_exec_error}")
    print(f"Answer keys WRONG (mismatch vs execution ground truth): {n_key_wrong}"
          + (f" ({100*n_key_wrong/n_with_ground_truth:.1f}% of verifiable)" if n_with_ground_truth else ""))
    print(f"Wrote {OUT_PATH}")

    print("\n--- Questions with no ground truth or exec errors ---")
    for q in questions:
        if q["ground_truth_option"] is None:
            print(f"  {q['id']} ({q['category']}, {q['question_id']}): {q['exec_error'] or 'no match for stdout=' + repr(q['raw_stdout'])}")

    print("\n--- Questions where the generated answer_key was WRONG ---")
    for q in questions:
        if q.get("key_is_correct") is False:
            print(f"  {q['id']} ({q['category']}, {q['question_id']}): answer_key={q['answer_key']} ground_truth_option={q['ground_truth_option']} (stdout={q['raw_stdout']!r})")


if __name__ == "__main__":
    main()
