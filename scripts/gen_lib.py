"""
Shared library for the expanded (v2) template-based question generator.

Design: this is a genuinely automated, AutoMCQ-style generator (not hand-typed
per question) so it can scale from the pilot's 25 solutions / 4 categories to
~130 solutions / 8 categories (~1000 questions) in one pass, with NO execution
of student code during generation (ground truth is established later, purely
by Step 3's execution-based verification -- consistent with the pilot).

Key idea reused from the dataset itself: for every task, the dataset's own
`tests.csv` (testcode/expected pairs, already validated against real student
solutions) and `task_descriptions.csv`'s `tester` column (containing the
support classes/helpers the grading harness defines, e.g. Node/Queue-ish
harnesses) give us ready-made, trustworthy call expressions and expected
outputs -- we don't have to hand-derive a correct call or manually trace
every algorithm. Where no such grounding exists, the generator falls back to
best-effort heuristics (e.g. guessing an answer_key equal to the final
expected value) and simply accepts a nonzero wrong-key rate, which Step 3
measures and Step 6 reports as a finding -- exactly per the pilot's rules.
"""
import ast
import builtins
import csv
import os
import random
import sys

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data_extracted", "AD2022dataset")

TASK_FILES = ["19_20_task_descriptions.csv", "20_21_task_descriptions.csv", "21_22_task_descriptions.csv"]
TEST_FILES = ["19_20_tests.csv", "20_21_tests.csv", "21_22_tests.csv"]

RANDOM_MARKERS = ("random", "get_random", "randrange", "randint", "choice(")


def load_tasks():
    tasks = {}
    for fn in TASK_FILES:
        path = os.path.join(DATA_DIR, fn)
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                tasks[row["id"]] = row
    return tasks


def load_tests():
    """Returns {question_id: [test_row, ...]}, deterministic tests only
    (filters out anything that references the harness's random-number
    helpers, so generated questions are reproducible)."""
    tests = {}
    for fn in TEST_FILES:
        path = os.path.join(DATA_DIR, fn)
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                code = row["testcode"]
                if any(m in code for m in RANDOM_MARKERS):
                    continue
                tests.setdefault(row["question_id"], []).append(row)
    # prefer is_example=True tests first (simpler, hand-picked by the dataset authors)
    for qid in tests:
        tests[qid].sort(key=lambda r: r.get("is_example") != "True")
    return tests


def harness_for_task(task_row):
    """Extract the tester's support-code preamble (everything before the
    {{ STUDENT_ANSWER }} Jinja placeholder) -- these are harness
    classes/helpers the grading tool provides, not code the student wrote."""
    tester = task_row.get("tester", "") or ""
    if "{{ STUDENT_ANSWER }}" not in tester:
        return tester.strip()
    return tester.split("{{ STUDENT_ANSWER }}")[0].strip()


def filter_harness_to_needed(harness_code, needed_context_code):
    """The tester preamble sometimes bundles a full REFERENCE SOLUTION (used
    internally for comparison-based grading) alongside genuinely-needed
    support classes (Node, custom Stack, etc.). Showing a reference solution
    to an answering model would leak the answer and invalidate the
    comprehension test. Keep only top-level defs that are actually referenced
    by name somewhere in `needed_context_code` (pass solution_code + every
    test's testcode for the task, concatenated, so this is safe regardless of
    which specific test a given question ends up using), plus all imports
    (harmless). Drop everything else (e.g. unused alternate solutions)."""
    if not harness_code.strip():
        return harness_code
    try:
        harness_tree = ast.parse(harness_code)
    except SyntaxError:
        return harness_code  # can't safely filter -- leave as-is rather than break execution

    used_names = set()
    for snippet in needed_context_code if isinstance(needed_context_code, list) else [needed_context_code]:
        try:
            snippet_tree = ast.parse(snippet)
        except SyntaxError:
            continue
        used_names |= {node.id for node in ast.walk(snippet_tree) if isinstance(node, ast.Name)}

    kept = []
    defined_names = set()
    for node in harness_tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            kept.append(node)
        elif isinstance(node, (ast.ClassDef, ast.FunctionDef)):
            if node.name in used_names:
                kept.append(node)
                defined_names.add(node.name)
        elif isinstance(node, ast.Assign):
            kept.append(node)  # module-level constants etc. -- cheap to keep, rarely an answer leak
        # bare expressions / other statements (e.g. stray reference-solution
        # calls at module level) are dropped

    if not kept:
        return ""
    new_mod = ast.Module(body=kept, type_ignores=[])
    ast.fix_missing_locations(new_mod)
    try:
        return ast.unparse(new_mod)
    except Exception:
        return harness_code


def entry_function_name(task_row, solution_code):
    """Best-effort: the skeleton tells us the real entry point's name."""
    skeleton = task_row.get("skeleton", "") or ""
    m = ast_first_def_name(skeleton)
    if m:
        return m
    # fall back to the last top-level function/class defined in the solution
    try:
        tree = ast.parse(solution_code)
    except SyntaxError:
        return None
    last = None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            last = node.name
    return last


def ast_first_def_name(code):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            return node.name
    return None


def detect_forward_ref_stub(solution_code):
    """Some solutions type-annotate a parameter/return with a name that's
    only defined in the task's harness (e.g. `def f(x: ListToSort) ->
    ListToSort:`). Python evaluates annotations EAGERLY at `def` time, so
    if the harness is placed after solution_code (as it must be, to keep
    solution_code's own line numbers 1:1 with what the generator computed
    via ast), such solutions raise NameError before ever running. Returns
    (stub_code, line_offset): stub_code is a single extra line to place
    BEFORE solution_code defining any such forward-referenced names as a
    harmless placeholder (stub_code is "" if none needed, in which case
    line_offset is 0). The generator must add `line_offset` to every
    absolute line number it embeds in verification_code (but NOT to line
    numbers mentioned in question text, since the model only ever sees
    solution_code unshifted)."""
    try:
        tree = ast.parse(solution_code)
    except SyntaxError:
        return "", 0

    defined = set(dir(builtins))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    defined.add(t.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                defined.add((alias.asname or alias.name).split(".")[0])

    needed = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            annots = [a.annotation for a in (node.args.args + node.args.kwonlyargs) if a.annotation]
            if node.returns:
                annots.append(node.returns)
            for ann in annots:
                for n in ast.walk(ann):
                    if isinstance(n, ast.Name) and n.id not in defined and n.id not in needed:
                        needed.append(n.id)

    if not needed:
        return "", 0
    stub = " = ".join(needed) + " = object\n"
    return stub, 1  # always exactly one extra line, regardless of how many names


def find_entry_func_node(solution_code, func_name):
    """Returns the ast.FunctionDef for func_name, searching top-level AND
    one level of nesting (methods inside a class), or None."""
    try:
        tree = ast.parse(solution_code)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return node
    return None


def first_loop(func_node):
    """First For/While loop anywhere inside func_node (not nested inside a
    different function). Returns (loop_node, body_first_lineno) or None."""
    for node in ast.walk(func_node):
        if node is func_node:
            continue
        if isinstance(node, (ast.FunctionDef,)):
            continue  # don't descend into nested function defs' own loops separately here
        if isinstance(node, (ast.For, ast.While)) and node.body:
            return node, node.body[0].lineno
    return None


def first_if(func_node):
    """First If statement inside func_node. Returns
    (if_node, body_first_lineno, orelse_first_lineno_or_None)."""
    for node in ast.walk(func_node):
        if node is func_node:
            continue
        if isinstance(node, ast.If) and node.body:
            orelse_line = node.orelse[0].lineno if node.orelse else None
            return node, node.body[0].lineno, orelse_line
    return None


def func_body_first_lineno(func_node):
    if func_node.body:
        return func_node.body[0].lineno
    return func_node.lineno


def last_simple_assign_before_return(func_node):
    """Find a Name target of a simple top-level Assign inside func_node,
    preferring the one closest (by source order) before a Return. Returns
    (var_name, return_lineno) or None."""
    # collect top-level statements of the function body only (not nested blocks)
    # fall back to scanning the whole subtree if nothing found at top level.
    def scan(stmts):
        last_name = None
        for stmt in stmts:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                last_name = stmt.targets[0].id
            if isinstance(stmt, ast.Return):
                if last_name:
                    return last_name, stmt.lineno
            # recurse into simple blocks (if/for/while bodies) to keep looking
            for field in ("body", "orelse"):
                sub = getattr(stmt, field, None)
                if sub:
                    res = scan(sub)
                    if res:
                        return res
        return None
    return scan(func_node.body)


def build_call_fn_source(testcode, fn_name):
    """Turn a dataset testcode snippet (ending in `print(EXPR)`, possibly
    with setup statements before it) into a zero-arg function definition
    `def fn_name(): <setup>; return EXPR` by AST-rewriting the final print
    call into a return. Returns the function source, or None if the
    testcode doesn't end in a print(...) call we can rewrite."""
    try:
        tree = ast.parse(testcode)
    except SyntaxError:
        return None
    if not tree.body:
        return None
    last = tree.body[-1]
    if not (isinstance(last, ast.Expr) and isinstance(last.value, ast.Call)):
        return None
    call = last.value
    if not (isinstance(call.func, ast.Name) and call.func.id == "print"):
        return None
    if not call.args:
        return None
    expr = call.args[0]
    setup_stmts = tree.body[:-1]

    # Some student solutions rely on a nested helper function reading a
    # module-level global that the ORIGINAL grading harness sets by running
    # testcode at true module/global scope (concatenated after the student's
    # code, not inside a function). Wrapping that setup in our own function
    # would make those names local instead, breaking such (sloppy but real)
    # solutions' global lookups. Re-declare them `global` to preserve the
    # original semantics.
    top_level_assigned_names = []
    for stmt in setup_stmts:
        if isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                if isinstance(t, ast.Name) and t.id not in top_level_assigned_names:
                    top_level_assigned_names.append(t.id)

    new_body = setup_stmts + [ast.Return(value=expr)]
    if top_level_assigned_names:
        new_body = [ast.Global(names=top_level_assigned_names)] + new_body

    func_node = ast.FunctionDef(
        name=fn_name,
        args=ast.arguments(posonlyargs=[], args=[], vararg=None, kwonlyargs=[],
                            kw_defaults=[], kwarg=None, defaults=[]),
        body=new_body,
        decorator_list=[],
        returns=None,
        lineno=1, col_offset=0,
    )
    mod = ast.Module(body=[func_node], type_ignores=[])
    try:
        ast.fix_missing_locations(mod)
        return ast.unparse(mod)
    except Exception:
        return None


def mutate_call_for_edge(testcode):
    """Best-effort: replace the first list/int/str literal argument of the
    final call in testcode with an 'edge' value ([] / 0 / ''). Returns
    mutated testcode (still ending in print(...)) or None."""
    try:
        tree = ast.parse(testcode)
    except SyntaxError:
        return None
    if not tree.body:
        return None
    last = tree.body[-1]
    if not (isinstance(last, ast.Expr) and isinstance(last.value, ast.Call)):
        return None
    print_call = last.value
    if not (isinstance(print_call.func, ast.Name) and print_call.func.id == "print" and print_call.args):
        return None
    call = print_call.args[0]  # the expression being printed, e.g. opt([...]) -- NOT the print(...) wrapper itself

    class EdgeMutator(ast.NodeTransformer):
        def __init__(self):
            self.done = False

        def visit_List(self, node):
            if not self.done and node.elts:
                self.done = True
                return ast.List(elts=[], ctx=ast.Load())
            return node

        def visit_Constant(self, node):
            if self.done:
                return node
            if isinstance(node.value, bool):
                return node
            if isinstance(node.value, int) and node.value not in (0, 1):
                self.done = True
                return ast.Constant(value=0)
            if isinstance(node.value, str) and node.value:
                self.done = True
                return ast.Constant(value="")
            return node

    mutator = EdgeMutator()
    new_call = mutator.visit(ast.parse(ast.unparse(call), mode="eval").body)
    if not mutator.done:
        return None
    new_tree = ast.Module(
        body=tree.body[:-1] + [ast.Expr(value=ast.Call(func=ast.Name(id="print", ctx=ast.Load()),
                                                         args=[new_call], keywords=[]))],
        type_ignores=[],
    )
    try:
        ast.fix_missing_locations(new_tree)
        return ast.unparse(new_tree)
    except Exception:
        return None


def flip_first_comparator(solution_code):
    """Flip the first comparison operator found in solution_code (Lt<->Gt,
    LtE<->GtE, Eq->NotEq) and return (modified_code, description) or None."""
    try:
        tree = ast.parse(solution_code)
    except SyntaxError:
        return None

    FLIP = {ast.Lt: (ast.Gt, "<", ">"), ast.Gt: (ast.Lt, ">", "<"),
            ast.LtE: (ast.GtE, "<=", ">="), ast.GtE: (ast.LtE, ">=", "<="),
            ast.Eq: (ast.NotEq, "==", "!=")}

    state = {}

    class FlipVisitor(ast.NodeTransformer):
        def visit_Compare(self, node):
            self.generic_visit(node)
            if state.get("done"):
                return node
            for i, op in enumerate(node.ops):
                t = type(op)
                if t in FLIP:
                    new_cls, old_sym, new_sym = FLIP[t]
                    node.ops[i] = new_cls()
                    state["done"] = True
                    state["line"] = node.lineno
                    state["old"] = old_sym
                    state["new"] = new_sym
                    break
            return node

    new_tree = FlipVisitor().visit(tree)
    if not state.get("done"):
        return None
    ast.fix_missing_locations(new_tree)
    try:
        modified = ast.unparse(new_tree)
    except Exception:
        return None
    return modified, f"line {state['line']}: `{state['old']}` changed to `{state['new']}`"


def bump_first_const(solution_code):
    """Fallback modification: add 1 to the first 'interesting' (not 0/1)
    integer literal found in solution_code. Returns (modified_code, desc)."""
    try:
        tree = ast.parse(solution_code)
    except SyntaxError:
        return None
    state = {}

    class BumpVisitor(ast.NodeTransformer):
        def visit_Constant(self, node):
            if state.get("done") or not isinstance(node.value, int) or isinstance(node.value, bool):
                return node
            if node.value in (0, 1):
                return node
            state["done"] = True
            state["line"] = node.lineno
            state["old"] = node.value
            state["new"] = node.value + 1
            return ast.Constant(value=node.value + 1)

    new_tree = BumpVisitor().visit(tree)
    if not state.get("done"):
        return None
    ast.fix_missing_locations(new_tree)
    try:
        modified = ast.unparse(new_tree)
    except Exception:
        return None
    return modified, f"line {state['line']}: the constant `{state['old']}` changed to `{state['new']}`"


def pick_simple_tests(task_tests, n=3):
    """Return up to n tests from task_tests that are single-value (expected
    has no newline), single print(...), and whose testcode we can rewrite
    into a zero-arg callable -- i.e. tests actually usable by this
    generator's category builders. Order follows task_tests' own order
    (is_example=True already sorted first by load_tests)."""
    out = []
    for row in task_tests:
        if "\n" in row["expected"].strip():
            continue
        if row["testcode"].count("print(") != 1:
            continue
        if not build_call_fn_source(row["testcode"], "__probe"):
            continue
        out.append(row)
        if len(out) >= n:
            break
    return out


EDGE_MARKERS = ("= None", "[]", "(0,", ", 0)", "(0)", "''", '""', "(1,", ", 1)")


def find_natural_edge_test(task_tests):
    """Look for a test the dataset authors already wrote that looks like an
    edge case (empty/zero/single/None), preferring is_example rows. Skips
    multi-output tests (loops with several prints) -- only single clean
    print(...) testcode we can rewrite into a zero-arg call is usable.
    Returns a test row or None."""
    for row in task_tests:
        code = row["testcode"]
        expected = row["expected"]
        if "\n" in expected.strip():
            continue  # multi-value test, not a simple single-answer case
        if code.count("print(") != 1:
            continue
        if any(m in code for m in EDGE_MARKERS) and build_call_fn_source(code, "__probe"):
            return row
    return None


def shuffle_options(options, correct_letter, seed):
    """Deterministically shuffle A-D -> content, returning (new_options, new_answer_key)."""
    letters = ["A", "B", "C", "D"]
    rng = random.Random(seed)
    shuffled = letters[:]
    rng.shuffle(shuffled)
    new_options = {}
    new_key = None
    for old_l, new_l in zip(letters, shuffled):
        new_options[new_l] = options[old_l]
        if old_l == correct_letter:
            new_key = new_l
    return new_options, new_key


def numeric_distractors(value):
    """Generate plausible numeric distractors for an int/float value."""
    out = []
    try:
        if isinstance(value, bool):
            return [not value]
        if isinstance(value, int):
            out = [value + 1, value - 1, -value if value != 0 else 1, value * 2 if value not in (0, 1) else value + 2]
        elif isinstance(value, float):
            out = [value + 1.0, value - 1.0, round(value * 2, 4), -value if value != 0 else 1.0]
    except Exception:
        pass
    # dedupe, drop any equal to the true value
    seen = set()
    uniq = []
    for v in out:
        if v == value or v in seen:
            continue
        seen.add(v)
        uniq.append(v)
    return uniq


def format_value(v):
    return repr(v)
