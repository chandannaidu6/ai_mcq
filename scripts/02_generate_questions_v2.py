"""
Step 2 (v2, expanded): template-based (AutoMCQ-style) generator of up to 8
MCQ categories per solution, across the ~130-solution sample. Genuinely
automated -- for each solution it uses `ast` to locate loops/branches/
assignments and the dataset's own tests.csv (already-correct testcode +
expected pairs) and tester harnesses to ground questions, with NO execution
of student code during generation (consistent with the original pilot's
rule: the generator never runs code to check its own answers before
saving -- ground truth and any wrong-key findings come only from Step 3).

Where a category can be grounded in a real dataset test (output, edge_case
when a natural edge test exists, data_structure_state), the answer_key
should be reliably correct. Where it can't (loop_trace, control_flow,
call_count, variable_state, code_modification, edge_case when only a
mutated/un-run guess is available), the generator uses a clearly-labelled
heuristic guess and accepts that Step 3 may find it wrong -- that rate is
itself a reported finding, exactly as in the original pilot.

Processes solutions in chunks of 25 and prints progress per chunk.
"""
import ast
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_lib as gl  # noqa: E402
from harness import TRACER_CODE  # noqa: E402

ROOT = os.path.dirname(HERE)
SAMPLES_PATH = os.path.join(ROOT, "pilot_data", "sampled_solutions_v2.json")
OUT_PATH = os.path.join(ROOT, "results", "questions_v2.json")
SKIP_LOG_PATH = os.path.join(ROOT, "results", "category_skips.json")

CHUNK_SIZE = 25


def safe_literal(s):
    try:
        return ast.literal_eval(s)
    except Exception:
        return s  # keep as raw string (e.g. "True"/"False" still work with ast.literal_eval actually)


def build_distractors(correct_value, n=3):
    """Type-aware distractor generation. Returns up to n distractor strings
    (formatted the same way as the correct value will be displayed)."""
    out = []
    if isinstance(correct_value, bool):
        out = [not correct_value]
    elif isinstance(correct_value, (int, float)):
        out = gl.numeric_distractors(correct_value)
    elif isinstance(correct_value, list):
        if correct_value:
            rev = list(reversed(correct_value))
            if rev != correct_value:
                out.append(rev)
            dropped = correct_value[:-1]
            out.append(dropped)
            bumped = correct_value[:]
            if bumped and isinstance(bumped[0], (int, float)) and not isinstance(bumped[0], bool):
                bumped[0] = bumped[0] + 1
                out.append(bumped)
            out.append(correct_value + correct_value[:1])
        else:
            out = [[0], [None], [1, 2]]
    elif isinstance(correct_value, str):
        out = [correct_value[::-1] if correct_value else "x",
               (correct_value + "x"), (correct_value[:-1] if len(correct_value) > 1 else correct_value + "y")]
    elif correct_value is None:
        out = [0, [], False]
    else:
        out = []
    # dedupe, drop accidental matches to correct value
    uniq = []
    seen = set()
    for v in out:
        key = repr(v)
        if v == correct_value or key in seen:
            continue
        seen.add(key)
        uniq.append(v)
    return uniq[:n]


def fmt(v):
    """Display format matching how Python would print it (so string matching
    in Step 3 is exact)."""
    if isinstance(v, str) and not (v.startswith("[") or v.startswith("{") or v in ("True", "False", "None")):
        # this is a literal string value (not a stringified list/bool/None) -> show it printed, i.e. bare text match
        return v
    return str(v)


def make_question(sample, idx, qnum, category, question_text, options_raw, correct_raw, verification_body,
                   harness_code, harness_code_display="", solution_code_override=None, extra=None,
                   pre_harness_code=""):
    """options_raw: dict A-D -> python value (not yet formatted/shuffled).
    correct_raw: the python value that is correct (must match one options_raw value by equality)."""
    correct_letter = None
    options_fmt = {}
    for letter, val in options_raw.items():
        options_fmt[letter] = fmt(val)
        if val == correct_raw or fmt(val) == fmt(correct_raw):
            correct_letter = letter
    if correct_letter is None:
        return None  # shouldn't happen, but be safe
    qid = f"s{idx:03d}_q{qnum}"
    options_shuffled, answer_key = gl.shuffle_options(options_fmt, correct_letter, seed=qid)
    q = {
        "id": qid,
        "sample_index": idx,
        "question_id": sample["question_id"],
        "student_id": sample["student_id"],
        "title_eng": sample["title_eng"],
        "category": category,
        "question": question_text,
        "options": options_shuffled,
        "answer_key": answer_key,
        "verification_code": verification_body,
        "solution_code": solution_code_override or sample["solution_code"],
        "harness_code": harness_code,
        "harness_code_display": harness_code_display,
        "pre_harness_code": pre_harness_code,
    }
    if extra:
        q["generation_note"] = extra
    return q


# ---------- category builders ----------

def gen_output(sample, idx, qnum, task, tests, harness_code, harness_code_display, pre_harness_code=""):
    simple = gl.pick_simple_tests(tests, n=1)
    if not simple:
        return None, "no usable (single-value) test found"
    row = simple[0]
    correct = safe_literal(row["expected"])
    distractors = build_distractors(correct)
    if len(distractors) < 3:
        return None, "could not build 3 distinct distractors"
    options = {"A": correct, "B": distractors[0], "C": distractors[1], "D": distractors[2]}
    qtext = (f"What gets printed when the following is run immediately after the code above?\n"
             f"```python\n{row['testcode']}\n```")
    return make_question(sample, idx, qnum, "output", qtext, options, correct,
                          row["testcode"], harness_code, harness_code_display,
                          pre_harness_code=pre_harness_code), None


def gen_edge_case(sample, idx, qnum, task, tests, harness_code, harness_code_display, pre_harness_code=""):
    nat = gl.find_natural_edge_test(tests)
    if nat:
        correct = safe_literal(nat["expected"])
        distractors = build_distractors(correct)
        if len(distractors) < 3:
            for exc in ("IndexError", "ValueError", "TypeError", "ZeroDivisionError"):
                distractors.append(f"Raises {exc}")
                if len(distractors) >= 3:
                    break
        if len(distractors) < 3:
            return None, "could not build 3 distractors for natural edge test"
        options = {"A": correct, "B": distractors[0], "C": distractors[1], "D": distractors[2]}
        qtext = (f"This is an edge-case input. What gets printed when the following runs immediately "
                 f"after the code above?\n```python\n{nat['testcode']}\n```")
        verif = (f"try:\n"
                 f"{chr(10).join('    ' + l for l in nat['testcode'].splitlines())}\n"
                 f"except Exception as __e:\n"
                 f"    print('Raises ' + type(__e).__name__)")
        return make_question(sample, idx, qnum, "edge_case", qtext, options, correct, verif, harness_code, harness_code_display,
                              extra="grounded in a dataset-authored edge test", pre_harness_code=pre_harness_code), None

    simple = gl.pick_simple_tests(tests, n=1)
    if not simple:
        return None, "no natural edge test and no simple test to mutate"
    mutated = gl.mutate_call_for_edge(simple[0]["testcode"])
    if not mutated:
        return None, "edge mutation not applicable (no list/int/str literal arg found)"
    # naive guess: reuse the type of the original expected value for a plausible default
    orig_expected = safe_literal(simple[0]["expected"])
    if isinstance(orig_expected, list):
        guess = []
    elif isinstance(orig_expected, bool):
        guess = orig_expected
    elif isinstance(orig_expected, (int, float)):
        guess = 0
    elif isinstance(orig_expected, str):
        guess = ""
    else:
        guess = orig_expected
    distractors = [f"Raises IndexError", f"Raises ValueError", orig_expected if orig_expected != guess else f"Raises TypeError"]
    distractors = [d for d in distractors if d != guess][:3]
    while len(distractors) < 3:
        distractors.append(f"Raises {['TypeError','ZeroDivisionError','KeyError'][len(distractors)]}")
    options = {"A": guess, "B": distractors[0], "C": distractors[1], "D": distractors[2]}
    qtext = (f"This is an edge-case input (generator-constructed, unverified). What gets printed when the "
             f"following runs immediately after the code above?\n```python\n{mutated}\n```")
    verif = (f"try:\n"
             f"{chr(10).join('    ' + l for l in mutated.splitlines())}\n"
             f"except Exception as __e:\n"
             f"    print('Raises ' + type(__e).__name__)")
    return make_question(sample, idx, qnum, "edge_case", qtext, options, guess, verif, harness_code, harness_code_display,
                          extra="UNGROUNDED: generator guessed the answer via a naive heuristic, not execution",
                          pre_harness_code=pre_harness_code), None


def gen_loop_trace(sample, idx, qnum, task, tests, harness_code, harness_code_display, func_node, line_offset,
                    pre_harness_code=""):
    loop_info = gl.first_loop(func_node)
    if not loop_info:
        return None, "no loop found in entry function"
    loop_node, body_line = loop_info
    simple = gl.pick_simple_tests(tests, n=2)
    if not simple:
        return None, "no usable test to drive the loop"
    row = simple[min(1, len(simple) - 1)]
    call_src = gl.build_call_fn_source(row["testcode"], "__cf")
    if not call_src:
        return None, "could not build call_fn from test"
    # naive heuristic guess: length of the first list literal argument in the call, else a small constant
    try:
        call_ast = ast.parse(row["testcode"]).body[-1].value.args[0]
        list_lens = [len(n.elts) for n in ast.walk(call_ast) if isinstance(n, ast.List)]
        guess = list_lens[0] if list_lens else 3
    except Exception:
        guess = 3
    distractors = [max(guess - 1, 0), guess + 1, guess * 2 if guess > 0 else 2]
    distractors = [d for d in dict.fromkeys(distractors) if d != guess][:3]
    while len(distractors) < 3:
        distractors.append(guess + len(distractors) + 2)
    options = {"A": guess, "B": distractors[0], "C": distractors[1], "D": distractors[2]}
    qtext = (f"Consider calling the code above like this:\n```python\n{row['testcode']}\n```\n"
             f"How many times does the loop body starting at line {body_line} execute?")
    verif = f"{call_src}\nprint(__trace_hits({body_line + line_offset}, __cf))"
    return make_question(sample, idx, qnum, "loop_trace", qtext, options, guess, verif, harness_code, harness_code_display,
                          extra="UNGROUNDED: generator guessed the iteration count via a naive heuristic, not execution",
                          pre_harness_code=pre_harness_code), None


def gen_control_flow(sample, idx, qnum, task, tests, harness_code, harness_code_display, func_node, line_offset,
                      pre_harness_code=""):
    if_info = gl.first_if(func_node)
    if not if_info:
        return None, "no if-statement found in entry function"
    if_node, if_line, else_line = if_info
    simple = gl.pick_simple_tests(tests, n=1)
    if not simple:
        return None, "no usable test"
    row = simple[0]
    call_src = gl.build_call_fn_source(row["testcode"], "__cf")
    if not call_src:
        return None, "could not build call_fn from test"
    # deterministic 'coin flip' guess (no execution) based on the question id
    guess_if_branch = (hash(f"{sample['question_id']}_{sample['student_id']}_cf") % 2 == 0)
    if_label = f"the `if` branch executes (line {if_line})"
    else_label = f"the `else`/`elif` branch executes (line {else_line})" if else_line else "the `if` branch is skipped entirely (condition is False, no else)"
    guess = if_label if guess_if_branch else else_label
    other = else_label if guess_if_branch else if_label
    options = {"A": guess, "B": other, "C": "an exception is raised", "D": "neither branch is reached (unreachable code)"}
    qtext = (f"Consider calling the code above like this:\n```python\n{row['testcode']}\n```\n"
             f"At the first `if` statement in the function (line {if_line}), which branch executes?")
    if_line_exec = if_line + line_offset
    else_line_exec = (else_line + line_offset) if else_line else None
    lines = [if_line_exec] + ([else_line_exec] if else_line_exec else [])
    verif_lines = [call_src, f"__counts = __trace_lines({lines!r}, __cf)"]
    verif_lines.append(f"if __counts.get({if_line_exec}, 0) > 0:")
    verif_lines.append(f"    print({if_label!r})")
    verif_lines.append("else:")
    verif_lines.append(f"    print({else_label!r})")
    verif = "\n".join(verif_lines)
    return make_question(sample, idx, qnum, "control_flow", qtext, options, guess, verif, harness_code, harness_code_display,
                          extra="UNGROUNDED: generator guessed which branch via a coin flip, not execution",
                          pre_harness_code=pre_harness_code), None


def gen_call_count(sample, idx, qnum, task, tests, harness_code, harness_code_display, func_node, line_offset,
                    pre_harness_code=""):
    body_line = gl.func_body_first_lineno(func_node)
    simple = gl.pick_simple_tests(tests, n=1)
    if not simple:
        return None, "no usable test"
    row = simple[0]
    call_src = gl.build_call_fn_source(row["testcode"], "__cf")
    if not call_src:
        return None, "could not build call_fn from test"
    guess = 1  # naive default: assume no recursion
    distractors = [2, 3, 5]
    options = {"A": guess, "B": distractors[0], "C": distractors[1], "D": distractors[2]}
    qtext = (f"Consider calling the code above like this:\n```python\n{row['testcode']}\n```\n"
             f"How many times total is `{func_node.name}` called (including any recursive calls)?")
    verif = f"{call_src}\nprint(__trace_hits({body_line + line_offset}, __cf))"
    return make_question(sample, idx, qnum, "call_count", qtext, options, guess, verif, harness_code, harness_code_display,
                          extra="UNGROUNDED: generator guessed call count (default: assumes no recursion), not execution",
                          pre_harness_code=pre_harness_code), None


def gen_variable_state(sample, idx, qnum, task, tests, harness_code, harness_code_display, func_node, line_offset,
                        pre_harness_code=""):
    info = gl.last_simple_assign_before_return(func_node)
    if not info:
        return None, "no simple assignment found before a return"
    var_name, ret_line = info
    simple = gl.pick_simple_tests(tests, n=1)
    if not simple:
        return None, "no usable test"
    row = simple[0]
    call_src = gl.build_call_fn_source(row["testcode"], "__cf")
    if not call_src:
        return None, "could not build call_fn from test"
    guess = safe_literal(row["expected"])  # naive: assume this variable equals the return value
    distractors = build_distractors(guess)
    if len(distractors) < 3:
        return None, "could not build 3 distractors"
    options = {"A": guess, "B": distractors[0], "C": distractors[1], "D": distractors[2]}
    qtext = (f"Consider calling the code above like this:\n```python\n{row['testcode']}\n```\n"
             f"What is the value of local variable `{var_name}` right before the function returns (line {ret_line})?")
    verif = f"{call_src}\nprint(__trace_var({ret_line + line_offset}, {var_name!r}, 1, __cf))"
    return make_question(sample, idx, qnum, "variable_state", qtext, options, guess, verif, harness_code, harness_code_display,
                          extra="UNGROUNDED: generator guessed the variable equals the return value, not execution",
                          pre_harness_code=pre_harness_code), None


def gen_code_modification(sample, idx, qnum, task, tests, harness_code, harness_code_display, pre_harness_code=""):
    mod = gl.flip_first_comparator(sample["solution_code"])
    mod_desc_prefix = "a comparison operator was flipped"
    if not mod:
        mod = gl.bump_first_const(sample["solution_code"])
        mod_desc_prefix = "a constant was changed"
    if not mod:
        return None, "no comparison operator or non-trivial constant found to modify"
    modified_code, desc = mod
    simple = gl.pick_simple_tests(tests, n=1)
    if not simple:
        return None, "no usable test"
    row = simple[0]
    guess = safe_literal(row["expected"])  # naive: assume the modification doesn't change this test's result
    distractors = build_distractors(guess)
    if len(distractors) < 3:
        return None, "could not build 3 distractors"
    options = {"A": guess, "B": distractors[0], "C": distractors[1], "D": distractors[2]}
    qtext = (f"The student's code is changed as follows ({mod_desc_prefix}, {desc}):\n```python\n{modified_code}\n```\n"
             f"With this change, what gets printed by:\n```python\n{row['testcode']}\n```")
    return make_question(sample, idx, qnum, "code_modification", qtext, options, guess, row["testcode"],
                          harness_code, harness_code_display, solution_code_override=modified_code,
                          extra="UNGROUNDED: generator guessed the modified output equals the original, not execution",
                          pre_harness_code=pre_harness_code), None


def gen_data_structure_state(sample, idx, qnum, task, tests, harness_code, harness_code_display, pre_harness_code=""):
    for row in gl.pick_simple_tests(tests, n=6):
        val = safe_literal(row["expected"])
        if isinstance(val, (list, dict)):
            distractors = build_distractors(val)
            if len(distractors) < 3:
                continue
            options = {"A": val, "B": distractors[0], "C": distractors[1], "D": distractors[2]}
            qtext = (f"What are the contents of the data structure printed by the following, run immediately "
                     f"after the code above?\n```python\n{row['testcode']}\n```")
            return make_question(sample, idx, qnum, "data_structure_state", qtext, options, val,
                                  row["testcode"], harness_code, harness_code_display,
                                  pre_harness_code=pre_harness_code), None
    return None, "no test with a list/dict-valued expected result found"


CATEGORY_ORDER = ["output", "variable_state", "loop_trace", "control_flow",
                  "call_count", "edge_case", "code_modification", "data_structure_state"]


def generate_for_sample(sample, idx, tasks, tests_by_task):
    qid = sample["question_id"]
    task = tasks[qid]
    code = sample["solution_code"]
    raw_harness_code = gl.harness_for_task(task)  # FULL preamble -- used for execution (must stay correct)
    tests = tests_by_task.get(qid, [])
    # filtered preamble -- used for what's SHOWN to answering models, so a bundled
    # reference solution (if any) in the tester never leaks the answer; safe to
    # compute from solution_code + every test's testcode (not just picked ones)
    display_context = [code] + [t["testcode"] for t in tests]
    harness_code_display = gl.filter_harness_to_needed(raw_harness_code, display_context)
    harness_code = raw_harness_code

    # a handful of solutions type-annotate a parameter/return with a name only
    # the (later-placed) harness defines, which Python evaluates eagerly at
    # `def` time -- see detect_forward_ref_stub's docstring. Affects ALL
    # categories uniformly (pre_harness_code), while the 4 categories that
    # embed absolute line numbers in verification_code also need line_offset.
    pre_harness_code, line_offset = gl.detect_forward_ref_stub(code)

    fn_name = gl.entry_function_name(task, code)
    func_node = gl.find_entry_func_node(code, fn_name) if fn_name else None

    questions = []
    skips = []
    qnum = 0

    def emit(builder_fn, *args):
        nonlocal qnum
        q, skip_reason = builder_fn(sample, idx, qnum, task, tests, harness_code, harness_code_display, *args,
                                     pre_harness_code=pre_harness_code)
        if q:
            questions.append(q)
            qnum += 1
        else:
            skips.append({"question_id": qid, "student_id": sample["student_id"],
                           "category": builder_fn.__name__.replace("gen_", ""), "reason": skip_reason})

    emit(gen_output)
    emit(gen_edge_case)
    emit(gen_code_modification)
    emit(gen_data_structure_state)
    if func_node is not None:
        emit(gen_loop_trace, func_node, line_offset)
        emit(gen_control_flow, func_node, line_offset)
        emit(gen_call_count, func_node, line_offset)
        emit(gen_variable_state, func_node, line_offset)
    else:
        for cat in ("loop_trace", "control_flow", "call_count", "variable_state"):
            skips.append({"question_id": qid, "student_id": sample["student_id"],
                          "category": cat, "reason": "no function-level entry point found (likely class-based task)"})

    return questions, skips


def main():
    tasks = gl.load_tasks()
    tests_by_task = gl.load_tests()
    samples = json.load(open(SAMPLES_PATH, encoding="utf-8"))

    all_questions = []
    all_skips = []

    for chunk_start in range(0, len(samples), CHUNK_SIZE):
        chunk = samples[chunk_start:chunk_start + CHUNK_SIZE]
        for i, sample in enumerate(chunk):
            idx = chunk_start + i
            qs, skips = generate_for_sample(sample, idx, tasks, tests_by_task)
            all_questions.extend(qs)
            all_skips.extend(skips)

        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(all_questions, f, indent=2, ensure_ascii=False)
        with open(SKIP_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(all_skips, f, indent=2, ensure_ascii=False)

        print(f"Chunk [{chunk_start}:{chunk_start+len(chunk)}] done. "
              f"Running total: {len(all_questions)} questions, {len(all_skips)} skips. "
              f"(saved to {OUT_PATH})")

    cat_counts = {}
    for q in all_questions:
        cat_counts[q["category"]] = cat_counts.get(q["category"], 0) + 1
    print("\nFinal category counts:", cat_counts)
    print("Total questions:", len(all_questions))
    print("Total skips:", len(all_skips))
    skip_by_cat = {}
    for s in all_skips:
        skip_by_cat[s["category"]] = skip_by_cat.get(s["category"], 0) + 1
    print("Skips by category:", skip_by_cat)


if __name__ == "__main__":
    main()
