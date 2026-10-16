"""
Step 2: Generate questions (the GENERATOR is Claude itself, authored by hand
in a single pass -- no execution/self-checking before saving, per the pilot
protocol; wrong answer keys are expected to surface in Step 3's execution-based
verification and are reported as a finding, not silently fixed).

For each of the 25 sampled solutions, 4 MCQs are written, one per category:
  output | variable_state | loop_trace | control_flow

Each question carries a `verification_code` snippet that, when run
immediately after (student code + any task-specific harness class +
TRACER_CODE), prints the ground-truth answer. Verification/execution happens
in 03_verify_answer_keys.py, not here.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from harness import HARNESS_BY_INDEX, PRE_HARNESS_BY_INDEX  # noqa: E402

ROOT = os.path.dirname(HERE)
SAMPLES_PATH = os.path.join(ROOT, "pilot_data", "sampled_solutions.json")
OUT_PATH = os.path.join(ROOT, "results", "questions.json")

samples = json.load(open(SAMPLES_PATH, encoding="utf-8"))

# questions[i] = list of 4 dicts (category, question, options A-D, answer_key, verification_code)
# for sample index i (0..24), matching the order in sampled_solutions.json

QUESTIONS = {}

QUESTIONS[0] = [
    dict(category="output",
         question="Given `opt([3, 2, 5, 10, 7])`, what value does the function return?",
         options={"A": "15", "B": "13", "C": "17", "D": "12"},
         answer_key="A",
         verification_code="print(opt([3, 2, 5, 10, 7]))"),
    dict(category="variable_state",
         question="Trace `opt([3, 2, 5, 10, 7])`. The loop body runs for i=2,3,4. What is the value of local variable `c` the 2nd time the line `a = b` executes (i.e. during the iteration where i=3)?",
         options={"A": "13", "B": "15", "C": "8", "D": "10"},
         answer_key="A",
         verification_code="print(__trace_var(9, 'c', 2, lambda: opt([3, 2, 5, 10, 7])))"),
    dict(category="loop_trace",
         question="How many times does the loop body line `c = max(W[i]+a, b)` execute when calling `opt([3, 2, 5, 10, 7])`?",
         options={"A": "3", "B": "5", "C": "2", "D": "4"},
         answer_key="A",
         verification_code="print(__trace_hits(8, lambda: opt([3, 2, 5, 10, 7])))"),
    dict(category="control_flow",
         question="When calling `opt([7])` (a single-element list), which branch runs?",
         options={
             "A": "Condition `len(W) < 2` is True; executes `return W[0]` (line 3)",
             "B": "Runs the main loop and returns `b`",
             "C": "Raises an IndexError",
             "D": "Executes `return max(W[0], W[1])`",
         },
         answer_key="A",
         verification_code=(
             "counts = __trace_lines([3], lambda: opt([7]))\n"
             "print('Condition `len(W) < 2` is True; executes `return W[0]` (line 3)' if counts[3] > 0 else 'OTHER')"
         )),
]

QUESTIONS[1] = [
    dict(category="output",
         question=(
             "Node objects have attributes key, left, right, parent. Build this tree: "
             "root(key=5) with left child (key=3) and right child (key=8); node(8) has left "
             "child (key=7) and right child (key=9); all parent links set accordingly. "
             "Call `delete(root, <the node with key 8>)`. What is the in-order traversal "
             "(list of keys) of the resulting tree?"
         ),
         options={"A": "[3, 5, 7, 9]", "B": "[3, 5, 7, 8, 9]", "C": "[3, 5, 9]", "D": "[3, 5, 8, 9]"},
         answer_key="A",
         verification_code=(
             "root = Node(); root.key = 5\n"
             "n3 = Node(); n3.key = 3; n3.parent = root; root.left = n3\n"
             "n8 = Node(); n8.key = 8; n8.parent = root; root.right = n8\n"
             "n7 = Node(); n7.key = 7; n7.parent = n8; n8.left = n7\n"
             "n9 = Node(); n9.key = 9; n9.parent = n8; n8.right = n9\n"
             "new_root = delete(root, n8)\n"
             "def inorder(n):\n"
             "    if n is None: return []\n"
             "    return inorder(n.left) + [n.key] + inorder(n.right)\n"
             "print(inorder(new_root))"
         )),
    dict(category="variable_state",
         question=(
             "Using the same tree as above (root=5, left=3, right=8(left=7,right=9)), "
             "call `delete(root, <node with key 8>)`. What is the key of local variable `y` "
             "right after it is assigned inside `delete`?"
         ),
         options={"A": "9", "B": "8", "C": "7", "D": "5"},
         answer_key="A",
         verification_code=(
             "root = Node(); root.key = 5\n"
             "n3 = Node(); n3.key = 3; n3.parent = root; root.left = n3\n"
             "n8 = Node(); n8.key = 8; n8.parent = root; root.right = n8\n"
             "n7 = Node(); n7.key = 7; n7.parent = n8; n8.left = n7\n"
             "n9 = Node(); n9.key = 9; n9.parent = n8; n8.right = n9\n"
             "y_node = __trace_var(7, 'y', 1, lambda: delete(root, n8))\n"
             "print(y_node.key)"
         )),
    dict(category="loop_trace",
         question=(
             "Using the same tree (root=5, left=3, right=8(left=7,right=9)), call "
             "`delete(root, root)` (deleting the root itself). How many times does the "
             "while-loop body `node = node.left` inside `t_min` execute?"
         ),
         options={"A": "1", "B": "0", "C": "2", "D": "3"},
         answer_key="A",
         verification_code=(
             "root = Node(); root.key = 5\n"
             "n3 = Node(); n3.key = 3; n3.parent = root; root.left = n3\n"
             "n8 = Node(); n8.key = 8; n8.parent = root; root.right = n8\n"
             "n7 = Node(); n7.key = 7; n7.parent = n8; n8.left = n7\n"
             "n9 = Node(); n9.key = 9; n9.parent = n8; n8.right = n9\n"
             "print(__trace_hits(25, lambda: delete(root, root)))"
         )),
    dict(category="control_flow",
         question=(
             "In `delete`, when deleting the node with key 8 (which has two children, 7 and 9), "
             "which branch of `if delete.left == None or delete.right == None:` executes?"
         ),
         options={
             "A": "Condition is False; executes `y = t_min(delete.right)` (line 6)",
             "B": "Condition is True; executes `y = delete` (line 4)",
             "C": "Raises a ValueError",
             "D": "Skips directly to `return root` without computing y",
         },
         answer_key="A",
         verification_code=(
             "root = Node(); root.key = 5\n"
             "n3 = Node(); n3.key = 3; n3.parent = root; root.left = n3\n"
             "n8 = Node(); n8.key = 8; n8.parent = root; root.right = n8\n"
             "n7 = Node(); n7.key = 7; n7.parent = n8; n8.left = n7\n"
             "n9 = Node(); n9.key = 9; n9.parent = n8; n8.right = n9\n"
             "counts = __trace_lines([4, 6], lambda: delete(root, n8))\n"
             "print('Condition is False; executes `y = t_min(delete.right)` (line 6)' if counts[6] > 0 else 'Condition is True; executes `y = delete` (line 4)')"
         )),
]

QUESTIONS[2] = [
    dict(category="output",
         question="What does `calc(4, [[1, 2], [2, 3], [1, 3], [3, 4]])` return?",
         options={"A": "3", "B": "2", "C": "4", "D": "1"},
         answer_key="A",
         verification_code="print(calc(4, [[1, 2], [2, 3], [1, 3], [3, 4]]))"),
    dict(category="variable_state",
         question=(
             "Trace `calc(4, [[1, 2], [2, 3], [1, 3], [3, 4]])`. What is the value of the "
             "`Lengths` list right after the outer loop has fully processed `e=1` (i.e. at "
             "the start of the `e=2` iteration of `for e in range(len(Connections))`)?"
         ),
         options={"A": "[0, 1, 2, 0]", "B": "[0, 1, 1, 0]", "C": "[1, 1, 2, 0]", "D": "[0, 1, 2, 3]"},
         answer_key="A",
         verification_code="print(__trace_var(13, 'Lengths', 3, lambda: calc(4, [[1, 2], [2, 3], [1, 3], [3, 4]])))"),
    dict(category="loop_trace",
         question="How many total times does the line `Lengths[u] = max(Lengths[e] + 1, Lengths[u])` execute during `calc(4, [[1, 2], [2, 3], [1, 3], [3, 4]])`?",
         options={"A": "4", "B": "3", "C": "5", "D": "2"},
         answer_key="A",
         verification_code="print(__trace_hits(15, lambda: calc(4, [[1, 2], [2, 3], [1, 3], [3, 4]])))"),
    dict(category="control_flow",
         question="What happens when `calc(2, [[2, 1]])` is called (an edge where the source label is greater than the target label)?",
         options={
             "A": "Raises an AssertionError from the `assert e[0] < e[1]` check",
             "B": "Silently ignores the invalid edge and returns 0",
             "C": "Returns a negative length",
             "D": "Loops forever",
         },
         answer_key="A",
         verification_code=(
             "try:\n"
             "    calc(2, [[2, 1]])\n"
             "    print('NO_ERROR')\n"
             "except AssertionError:\n"
             "    print('Raises an AssertionError from the `assert e[0] < e[1]` check')\n"
             "except Exception as e:\n"
             "    print('OTHER:' + type(e).__name__)"
         )),
]

QUESTIONS[3] = [
    dict(category="output",
         question=(
             "Node objects have key/left/right/parent attributes. Starting from an empty "
             "tree (root=None), call `root = insert(root, <new Node key=10>)`, then "
             "`root = insert(root, <new Node key=5>)`, then `root = insert(root, <new Node key=15>)`. "
             "What is the in-order traversal (list of keys) of the final tree?"
         ),
         options={"A": "[5, 10, 15]", "B": "[10, 5, 15]", "C": "[15, 10, 5]", "D": "[5, 15, 10]"},
         answer_key="A",
         verification_code=(
             "n10 = Node(); n10.key = 10\n"
             "root = insert(None, n10)\n"
             "n5 = Node(); n5.key = 5\n"
             "root = insert(root, n5)\n"
             "n15 = Node(); n15.key = 15\n"
             "root = insert(root, n15)\n"
             "def inorder(n):\n"
             "    if n is None: return []\n"
             "    return inorder(n.left) + [n.key] + inorder(n.right)\n"
             "print(inorder(root))"
         )),
    dict(category="variable_state",
         question=(
             "Using the tree {10 (root), left=5} built as above, call `insert(root, <new Node key=15>)`. "
             "What is the key of local variable `y` right before the loop exits (the line "
             "`insert.parent = y` right after the while-loop)?"
         ),
         options={"A": "10", "B": "5", "C": "15", "D": "None"},
         answer_key="A",
         verification_code=(
             "n10 = Node(); n10.key = 10\n"
             "root = insert(None, n10)\n"
             "n5 = Node(); n5.key = 5\n"
             "root = insert(root, n5)\n"
             "n15 = Node(); n15.key = 15\n"
             "y_node = __trace_var(17, 'y', 1, lambda: insert(root, n15))\n"
             "print(y_node.key)"
         )),
    dict(category="loop_trace",
         question="Using the tree {10 (root), left=5, right=None}, how many times does the while-loop body (lines 12-16) execute when calling `insert(root, <new Node key=15>)`?",
         options={"A": "1", "B": "2", "C": "0", "D": "3"},
         answer_key="A",
         verification_code=(
             "n10 = Node(); n10.key = 10\n"
             "root = insert(None, n10)\n"
             "n5 = Node(); n5.key = 5\n"
             "root = insert(root, n5)\n"
             "n15 = Node(); n15.key = 15\n"
             "print(__trace_hits(12, lambda: insert(root, n15)))"
         )),
    dict(category="control_flow",
         question="What does calling `treewalk(None)` return?",
         options={"A": "None", "B": "Raises an AttributeError", "C": "The parent of the node", "D": "An empty list"},
         answer_key="A",
         verification_code="print(treewalk(None))"),
]

QUESTIONS[4] = [
    dict(category="output",
         question="What does `knapSack([60, 100, 120], [10, 20, 30], 50)` return?",
         options={"A": "220", "B": "180", "C": "160", "D": "200"},
         answer_key="A",
         verification_code="print(knapSack([60, 100, 120], [10, 20, 30], 50))"),
    dict(category="variable_state",
         question="During `knapSack([60, 100, 120], [10, 20, 30], 50)`, what is the value of `table[2][50]` once row i=2 of the DP table has been fully computed?",
         options={"A": "160", "B": "60", "C": "100", "D": "220"},
         answer_key="A",
         verification_code=(
             "tbl = __trace_var(9, 'table', 4, lambda: knapSack([60, 100, 120], [10, 20, 30], 50))\n"
             "print(tbl[2][50])"
         )),
    dict(category="loop_trace",
         question="How many total times does the line `table[i][w] = max(value[i-1] + table[i-1][w-volume[i-1]], table[i-1][w])` (the elif branch) execute during `knapSack([60, 100, 120], [10, 20, 30], 50)`?",
         options={"A": "93", "B": "90", "C": "100", "D": "83"},
         answer_key="A",
         verification_code="print(__trace_hits(14, lambda: knapSack([60, 100, 120], [10, 20, 30], 50)))"),
    dict(category="control_flow",
         question="What happens when `knapSack([60], [10.5], 50)` is called (a non-integer volume)?",
         options={
             "A": "Raises an AssertionError from the `assert x == round(x)` check",
             "B": "Silently truncates the volume to an int",
             "C": "Returns 0",
             "D": "Raises a TypeError",
         },
         answer_key="A",
         verification_code=(
             "try:\n"
             "    knapSack([60], [10.5], 50)\n"
             "    print('NO_ERROR')\n"
             "except AssertionError:\n"
             "    print('Raises an AssertionError from the `assert x == round(x)` check')\n"
             "except Exception as e:\n"
             "    print('OTHER:' + type(e).__name__)"
         )),
]

QUESTIONS[5] = [
    dict(category="output",
         question="What does `knapSack([60, 100, 120], [10, 20, 30], 50)` return?",
         options={"A": "220.0", "B": "220", "C": "160.0", "D": "180.0"},
         answer_key="A",
         verification_code="print(knapSack([60, 100, 120], [10, 20, 30], 50))"),
    dict(category="variable_state",
         question="During `knapSack([60, 100, 120], [10, 20, 30], 50)`, what is the value of `tabelle[2][50]` once row i=2 of the DP table has been fully computed?",
         options={"A": "160.0", "B": "100.0", "C": "60.0", "D": "220.0"},
         answer_key="A",
         verification_code=(
             "tbl = __trace_var(7, 'tabelle', 4, lambda: knapSack([60, 100, 120], [10, 20, 30], 50))\n"
             "print(tbl[2][50])"
         )),
    dict(category="loop_trace",
         question="How many total times is the condition `value[i-1] + tabelle[i-1][w-volume[i-1]] >= tabelle[i-1][w]` (line 12) evaluated during `knapSack([60, 100, 120], [10, 20, 30], 50)`?",
         options={"A": "93", "B": "90", "C": "83", "D": "100"},
         answer_key="A",
         verification_code="print(__trace_hits(12, lambda: knapSack([60, 100, 120], [10, 20, 30], 50)))"),
    dict(category="control_flow",
         question="What happens when `knapSack([60], [10.5], 50)` is called (a non-integer volume)?",
         options={
             "A": "Raises an AssertionError from the `assert x == round(x)` check",
             "B": "Silently truncates the volume to an int",
             "C": "Returns 0",
             "D": "Raises a TypeError",
         },
         answer_key="A",
         verification_code=(
             "try:\n"
             "    knapSack([60], [10.5], 50)\n"
             "    print('NO_ERROR')\n"
             "except AssertionError:\n"
             "    print('Raises an AssertionError from the `assert x == round(x)` check')\n"
             "except Exception as e:\n"
             "    print('OTHER:' + type(e).__name__)"
         )),
]

QUESTIONS[6] = [
    dict(category="output",
         question="What does `calc(10)` return?",
         options={"A": "1023", "B": "1024", "C": "1022", "D": "511"},
         answer_key="A",
         verification_code="print(calc(10))"),
    dict(category="variable_state",
         question="What is the value of local variable `n_gerade` when `calc(1000)` is called?",
         options={"A": "1", "B": "0", "C": "2", "D": "488"},
         answer_key="A",
         verification_code="print(__trace_var(13, 'n_gerade', 1, lambda: calc(1000)))"),
    dict(category="loop_trace",
         question="How many times does the line `mod = n_int % split` (line 10) execute when calling `calc(0)`?",
         options={"A": "0", "B": "1", "C": "2", "D": "3"},
         answer_key="A",
         verification_code="print(__trace_hits(10, lambda: calc(0)))"),
    dict(category="control_flow",
         question="Which branch executes when calling `calc(0)`?",
         options={
             "A": "Returns 0 immediately via the `n_int == 0` check (line 8)",
             "B": "Computes `n_gerade` and returns the big expression",
             "C": "Raises a ZeroDivisionError",
             "D": "Loops inside t_min",
         },
         answer_key="A",
         verification_code=(
             "counts = __trace_lines([8], lambda: calc(0))\n"
             "print('Returns 0 immediately via the `n_int == 0` check (line 8)' if counts[8] > 0 else 'OTHER')"
         )),
]

QUESTIONS[7] = [
    dict(category="output",
         question="What does `calc([2, 4, 6, 8, 10], [[0, 2], [1, 3], [2, 2], [0, 4]])` return?",
         options={"A": "[12, 18, 6, 30]", "B": "[12, 18, 6, 20]", "C": "[2, 18, 6, 30]", "D": "[12, 18, 8, 30]"},
         answer_key="A",
         verification_code="print(calc([2, 4, 6, 8, 10], [[0, 2], [1, 3], [2, 2], [0, 4]]))"),
    dict(category="variable_state",
         question="During `calc([2, 4, 6, 8, 10], [[0, 2], [1, 3], [2, 2], [0, 4]])`, what is the value of the prefix-sum list `c` right after it is fully built (before the query loop starts)?",
         options={"A": "[2, 6, 12, 20, 30]", "B": "[2, 4, 6, 8, 10]", "C": "[2, 6, 12, 20, 0]", "D": "[0, 6, 12, 20, 30]"},
         answer_key="A",
         verification_code="print(__trace_var(7, 'c', 1, lambda: calc([2, 4, 6, 8, 10], [[0, 2], [1, 3], [2, 2], [0, 4]])))"),
    dict(category="loop_trace",
         question="How many times does the line `s[i] = c[r] - c[l-1]` (line 15) execute for `calc([2, 4, 6, 8, 10], [[0, 2], [1, 3], [2, 2], [0, 4]])`?",
         options={"A": "1", "B": "0", "C": "2", "D": "4"},
         answer_key="A",
         verification_code="print(__trace_hits(15, lambda: calc([2, 4, 6, 8, 10], [[0, 2], [1, 3], [2, 2], [0, 4]])))"),
    dict(category="control_flow",
         question="For the query `(2, 2)` (l==r), which branch of the if/elif/else executes?",
         options={
             "A": "`l == r` branch; executes `s[i] = a[l]` (line 11)",
             "B": "`l == 0` branch; executes `s[i] = c[r]`",
             "C": "else branch; executes `s[i] = c[r] - c[l-1]`",
             "D": "Raises an IndexError",
         },
         answer_key="A",
         verification_code=(
             "counts = __trace_lines([11, 13, 15], lambda: calc([2, 4, 6, 8, 10], [[2, 2]]))\n"
             "print('`l == r` branch; executes `s[i] = a[l]` (line 11)' if counts[11] > 0 else 'OTHER')"
         )),
]

QUESTIONS[8] = [
    dict(category="output",
         question="What does `bfs([[1, 2], [3], [3], []], 0)` return?",
         options={"A": "[0, 1, 2, 3]", "B": "[0, 1, 2, 3, 3]", "C": "[0, 2, 1, 3]", "D": "[0, 1, 3, 2]"},
         answer_key="A",
         verification_code="print(bfs([[1, 2], [3], [3], []], 0))"),
    dict(category="variable_state",
         question="During `bfs([[1, 2], [3], [3], []], 0)`, what is the value of `result` right after node 2 has just been processed (appended)?",
         options={"A": "[0, 1, 2]", "B": "[0, 1]", "C": "[0, 1, 2, 3]", "D": "[2, 1, 0]"},
         answer_key="A",
         verification_code="print(__trace_var(7, 'result', 4, lambda: bfs([[1, 2], [3], [3], []], 0)))"),
    dict(category="loop_trace",
         question="How many total iterations does the `while not a.empty():` loop run for `bfs([[1, 2], [3], [3], []], 0)`?",
         options={"A": "5", "B": "4", "C": "6", "D": "3"},
         answer_key="A",
         verification_code="print(__trace_hits(8, lambda: bfs([[1, 2], [3], [3], []], 0)))"),
    dict(category="control_flow",
         question="Node 3 ends up dequeued twice in this run. On the second dequeue of node 3, which branch of `if current not in result:` executes?",
         options={
             "A": "Condition is False (3 already in result); the append is skipped",
             "B": "Condition is True; 3 is appended again",
             "C": "Raises an error",
             "D": "queue.put fails",
         },
         answer_key="A",
         verification_code=(
             "counts = __trace_lines([8, 13], lambda: bfs([[1, 2], [3], [3], []], 0))\n"
             "print('Condition is False (3 already in result); the append is skipped' if counts[13] < counts[8] else 'Condition is True; 3 is appended again')"
         )),
]

QUESTIONS[9] = [
    dict(category="output",
         question="What does `calc([0, 1, 1, 2], [0, 2, 1, 0])` return?",
         options={"A": "'0111'", "B": "'1111'", "C": "'0110'", "D": "'0011'"},
         answer_key="A",
         verification_code="print(repr(calc([0, 1, 1, 2], [0, 2, 1, 0])))"),
    dict(category="variable_state",
         question="During `calc([0, 1, 1, 2], [0, 2, 1, 0])`, what is the value of the dict `count` right after the first for-loop (counting occurrences in A) completes?",
         options={"A": "{0: 1, 1: 2, 2: 1}", "B": "{0: 1, 1: 1, 2: 1}", "C": "{0: 2, 1: 2, 2: 1}", "D": "{1: 2, 2: 1}"},
         answer_key="A",
         verification_code="print(__trace_var(9, 'count', 1, lambda: calc([0, 1, 1, 2], [0, 2, 1, 0])))"),
    dict(category="loop_trace",
         question="How many times does the `except KeyError:` branch (line 16) execute during `calc([0, 1, 1, 2], [0, 2, 1, 0])`?",
         options={"A": "1", "B": "0", "C": "2", "D": "4"},
         answer_key="A",
         verification_code="print(__trace_hits(16, lambda: calc([0, 1, 1, 2], [0, 2, 1, 0])))"),
    dict(category="control_flow",
         question="For `calc([0], [0])` (so i=0, count[0]=1, B[0]=0), which branch executes?",
         options={
             "A": "else branch; appends '0' (line 14)",
             "B": "if branch; appends '1' (line 12)",
             "C": "except KeyError branch (line 16)",
             "D": "Raises an IndexError",
         },
         answer_key="A",
         verification_code=(
             "counts = __trace_lines([12, 14, 16], lambda: calc([0], [0]))\n"
             "print(\"else branch; appends '0' (line 14)\" if counts[14] > 0 else (\"if branch; appends '1' (line 12)\" if counts[12] > 0 else \"except KeyError branch (line 16)\"))"
         )),
]

QUESTIONS[10] = [
    dict(category="output",
         question="What does `calc([0, 0, 0, 1], [2, 1])` return? (`A` contains category indices into `B`, decrementing capacities.)",
         options={"A": "'01'", "B": "'10'", "C": "'00'", "D": "'11'"},
         answer_key="A",
         verification_code="print(repr(calc([0, 0, 0, 1], [2, 1])))"),
    dict(category="variable_state",
         question="During `calc([0, 0, 0, 1], [2, 1])`, what is the value of `B` right after the first for-loop (the decrementing loop) completes?",
         options={"A": "[-1, 0]", "B": "[2, 1]", "C": "[-1, 1]", "D": "[0, -1]"},
         answer_key="A",
         verification_code="print(__trace_var(4, 'B', 1, lambda: calc([0, 0, 0, 1], [2, 1])))"),
    dict(category="loop_trace",
         question="How many times does the line `B[i] = B[i]-1` (line 3) execute for `calc([0, 0, 0, 1], [2, 1])`?",
         options={"A": "4", "B": "2", "C": "3", "D": "1"},
         answer_key="A",
         verification_code="print(__trace_hits(3, lambda: calc([0, 0, 0, 1], [2, 1])))"),
    dict(category="control_flow",
         question="After decrementing, `B[0]` becomes -1. When the second loop reaches that -1 entry, which branch executes?",
         options={
             "A": "`i < 0` branch; appends '0' (line 7)",
             "B": "else branch; appends '1' (line 9)",
             "C": "Raises an IndexError",
             "D": "Raises a TypeError",
         },
         answer_key="A",
         verification_code=(
             "counts = __trace_lines([7, 9], lambda: calc([0, 0, 0, 1], [2, 1]))\n"
             "print(\"`i < 0` branch; appends '0' (line 7)\" if counts[7] > 0 else \"else branch; appends '1' (line 9)\")"
         )),
]

QUESTIONS[11] = [
    dict(category="output",
         question="What does `expo(2, 10, 1000)` return?",
         options={"A": "24", "B": "1024", "C": "4", "D": "1000"},
         answer_key="A",
         verification_code="print(expo(2, 10, 1000))"),
    dict(category="variable_state",
         question="Inside `expo(2, 10, 1000)`, what is the value of parameter `c` when the body executes?",
         options={"A": "1000", "B": "10", "C": "2", "D": "24"},
         answer_key="A",
         verification_code="print(__trace_var(2, 'c', 1, lambda: expo(2, 10, 1000)))"),
    dict(category="loop_trace",
         question="How many times does the single statement in the body of `expo` (line 2, `return pow(a,b,c)`) execute for one call `expo(2, 10, 1000)` (there is no explicit Python loop in this function)?",
         options={"A": "1", "B": "2", "C": "3", "D": "0"},
         answer_key="A",
         verification_code="print(__trace_hits(2, lambda: expo(2, 10, 1000)))"),
    dict(category="control_flow",
         question="The file contains a triple-quoted block defining `addiere(...)` below `expo`. Does calling `expo(...)` ever execute that block as real code (i.e. is `addiere` a callable function)?",
         options={
             "A": "No, it's a string literal (comment-like), never executed as logic -- calling addiere raises NameError",
             "B": "Yes, it defines a helper that's always called",
             "C": "It raises a SyntaxError on import",
             "D": "It's executed only when b == 0",
         },
         answer_key="A",
         verification_code=(
             "try:\n"
             "    addiere(1, 2, 3, 4, 5)\n"
             "    print('Yes, it defines a helper that is always called')\n"
             "except NameError:\n"
             "    print(\"No, it's a string literal (comment-like), never executed as logic -- calling addiere raises NameError\")"
         )),
]

QUESTIONS[12] = [
    dict(category="output",
         question="`q = Queue()`; call `q.enqueue(1)`, `q.enqueue(2)`, `q.enqueue(3)`, then `q.dequeue()` once (discard its result). What does a second `q.dequeue()` call now return?",
         options={"A": "2", "B": "1", "C": "3", "D": "None"},
         answer_key="A",
         verification_code=(
             "q = Queue()\n"
             "q.enqueue(1); q.enqueue(2); q.enqueue(3)\n"
             "q.dequeue()\n"
             "print(q.dequeue())"
         )),
    dict(category="variable_state",
         question="`q = Queue()`; call `q.enqueue(1)`, `q.enqueue(2)`, `q.enqueue(3)`, then `q.dequeue()` once. What is `q.elements` afterward?",
         options={"A": "[2, 3]", "B": "[1, 2, 3]", "C": "[3, 2]", "D": "[2, 3, 1]"},
         answer_key="A",
         verification_code=(
             "q = Queue()\n"
             "q.enqueue(1); q.enqueue(2); q.enqueue(3)\n"
             "q.dequeue()\n"
             "print(q.elements)"
         )),
    dict(category="loop_trace",
         question="How many times does `self.elements.append(x)` (line 31, inside `enqueue`) execute across 3 calls to `enqueue`?",
         options={"A": "3", "B": "1", "C": "2", "D": "4"},
         answer_key="A",
         verification_code=(
             "q = Queue()\n"
             "print(__trace_hits(31, lambda: (q.enqueue(1), q.enqueue(2), q.enqueue(3))))"
         )),
    dict(category="control_flow",
         question="What happens when `dequeue()` is called on an empty `Queue`?",
         options={"A": "Raises an IndexError (line 42)", "B": "Returns None", "C": "Returns 0", "D": "Raises a KeyError"},
         answer_key="A",
         verification_code=(
             "q = Queue()\n"
             "try:\n"
             "    q.dequeue()\n"
             "    print('NO_ERROR')\n"
             "except IndexError:\n"
             "    print('Raises an IndexError (line 42)')\n"
             "except Exception as e:\n"
             "    print('OTHER:' + type(e).__name__)"
         )),
]

QUESTIONS[13] = [
    dict(category="output",
         question="What does `solution([5, 3, 8, 1, 9, 2])` return?",
         options={"A": "[1, 2, 3, 5, 8, 9]", "B": "[1, 2, 3, 5, 9, 8]", "C": "[2, 1, 3, 5, 8, 9]", "D": "[1, 2, 3, 5, 8, 9, 2]"},
         answer_key="A",
         verification_code="print(solution([5, 3, 8, 1, 9, 2]))"),
    dict(category="variable_state",
         question="During `solution([5, 3, 8, 1, 9, 2])`, what is the value of local variable `m` the first time the line `m = (l + r) // 2` (line 25, inside mergeSort) executes?",
         options={"A": "2", "B": "3", "C": "1", "D": "5"},
         answer_key="A",
         verification_code="print(__trace_var(26, 'm', 1, lambda: solution([5, 3, 8, 1, 9, 2])))"),
    dict(category="loop_trace",
         question="How many total times is `merge(...)` called (line 28) while sorting `[5, 3, 8, 1, 9, 2]`?",
         options={"A": "5", "B": "6", "C": "4", "D": "3"},
         answer_key="A",
         verification_code="print(__trace_hits(28, lambda: solution([5, 3, 8, 1, 9, 2])))"),
    dict(category="control_flow",
         question="For the recursive call `mergeSort(A, 0, 0)` (a single-element subarray), which branch executes?",
         options={
             "A": "Condition `l < r` is False (0 < 0); the function returns immediately without recursing",
             "B": "Calls merge once",
             "C": "Recurses infinitely",
             "D": "Raises an IndexError",
         },
         answer_key="A",
         verification_code=(
             "counts = __trace_lines([25], lambda: mergeSort([1], 0, 0))\n"
             "print('Condition `l < r` is False (0 < 0); the function returns immediately without recursing' if counts[25] == 0 else 'OTHER')"
         )),
]

QUESTIONS[14] = [
    dict(category="output",
         question=(
             "A `stack` object supports `push(x)` and `pop()` (standard LIFO). Call "
             "`Calculator(['2', '3', '4', '*', '+'], stack)` with a fresh empty stack "
             "(reverse-Polish-notation evaluator). What does it return?"
         ),
         options={"A": "14", "B": "9", "C": "24", "D": "20"},
         answer_key="A",
         verification_code="print(Calculator(['2', '3', '4', '*', '+'], CustomStack()))"),
    dict(category="variable_state",
         question=(
             "Using `Calculator(['2', '3', '4', '*', '+'], stack)`, what is the value of local "
             "variable `result` the first time it is computed (for the '*' token)?"
         ),
         options={"A": "12", "B": "7", "C": "14", "D": "24"},
         answer_key="A",
         verification_code="print(__trace_var(23, 'result', 1, lambda: Calculator(['2', '3', '4', '*', '+'], CustomStack())))"),
    dict(category="loop_trace",
         question="How many operator tokens (entries into the `except ValueError:` block, line 10 `operand = c`) are processed for `Calculator(['2', '3', '4', '*', '+'], stack)`?",
         options={"A": "2", "B": "1", "C": "3", "D": "5"},
         answer_key="A",
         verification_code="print(__trace_hits(10, lambda: Calculator(['2', '3', '4', '*', '+'], CustomStack())))"),
    dict(category="control_flow",
         question="For the token `'/'`, which branch of the operand if/elif chain executes?",
         options={
             "A": "`elif operand == '/'`; uses integer division `num1 // num2` (line 21)",
             "B": "`if operand == '+'` branch",
             "C": "Always raises ZeroDivisionError",
             "D": "`elif operand == '-'` branch",
         },
         answer_key="A",
         verification_code=(
             "counts = __trace_lines([15, 17, 19, 21], lambda: Calculator(['8', '2', '/'], CustomStack()))\n"
             "print(\"`elif operand == '/'`; uses integer division `num1 // num2` (line 21)\" if counts[21] > 0 else 'OTHER')"
         )),
]

QUESTIONS[15] = [
    dict(category="output",
         question="Given a monotone 0/1 function `f` with `f(x) = 1 if x >= 37 else 0`, what does `calc(f)` return?",
         options={"A": "37", "B": "36", "C": "38", "D": "0"},
         answer_key="A",
         verification_code="print(calc(lambda x: 1 if x >= 37 else 0))"),
    dict(category="variable_state",
         question="With the same `f` (threshold 37), what is the value of local variable `c` the very first time it is computed (line 5, `c=(n+r)//2`)?",
         options={"A": "500000000000000000", "B": "499999999999999999", "C": "250000000000000000", "D": "1000000000000000000"},
         answer_key="A",
         verification_code="print(__trace_var(6, 'c', 1, lambda: calc(lambda x: 1 if x >= 37 else 0)))"),
    dict(category="loop_trace",
         question="With the same `f` (threshold 37), approximately how many total iterations does the `while r-n>=2:` loop (line 4) run before returning?",
         options={"A": "60", "B": "59", "C": "61", "D": "58"},
         answer_key="A",
         verification_code="print(__trace_hits(4, lambda: calc(lambda x: 1 if x >= 37 else 0)))"),
    dict(category="control_flow",
         question="When `f(c)` returns 0 (falsy), which branch of `if not f(c):` executes?",
         options={
             "A": "`not f(c)` is True; executes `n = c` (line 7)",
             "B": "executes `r = c` (line 9)",
             "C": "Raises a TypeError",
             "D": "The loop exits immediately",
         },
         answer_key="A",
         verification_code=(
             "counts = __trace_lines([7, 9], lambda: calc(lambda x: 0))\n"
             "print('`not f(c)` is True; executes `n = c` (line 7)' if counts[7] > 0 else 'executes `r = c` (line 9)')"
         )),
]

QUESTIONS[16] = [
    dict(category="output",
         question="What does `dfs([[1, 2], [3], [3], []], 0)` return?",
         options={"A": "[0, 1, 3, 2]", "B": "[0, 1, 2, 3]", "C": "[0, 2, 1, 3]", "D": "[0, 1, 3]"},
         answer_key="A",
         verification_code="print(dfs([[1, 2], [3], [3], []], 0))"),
    dict(category="variable_state",
         question="During `dfs([[1, 2], [3], [3], []], 0)`, what is the value of `visited` right after node 1 is first marked visited (right after the `besucht.append(start)` call for node 1, the 2nd call overall)?",
         options={"A": "[True, True, False, False]", "B": "[True, False, False, False]", "C": "[True, True, True, False]", "D": "[True, True, True, True]"},
         answer_key="A",
         verification_code="print(__trace_var(8, 'visited', 2, lambda: dfs([[1, 2], [3], [3], []], 0)))"),
    dict(category="loop_trace",
         question="How many total times is `dfs_visit` called (counted via the `besucht.append(start)` line, line 8) for `dfs([[1, 2], [3], [3], []], 0)`?",
         options={"A": "4", "B": "3", "C": "5", "D": "2"},
         answer_key="A",
         verification_code="print(__trace_hits(8, lambda: dfs([[1, 2], [3], [3], []], 0)))"),
    dict(category="control_flow",
         question="When `dfs_visit(2)` examines its neighbor 3 (which was already visited via node 1's path), which branch executes at `if visited[v] == False:`?",
         options={
             "A": "Condition is False (3 already visited); the recursive call is skipped",
             "B": "Condition is True; calls dfs_visit(3) again",
             "C": "Raises a RecursionError",
             "D": "graph[2] is empty, the loop body never runs",
         },
         answer_key="A",
         verification_code=(
             "counts = __trace_lines([9, 10], lambda: dfs([[1, 2], [3], [3], []], 0))\n"
             "print('Condition is False (3 already visited); the recursive call is skipped' if counts[9] > counts[10] else 'Condition is True; calls dfs_visit(3) again')"
         )),
]

QUESTIONS[17] = [
    dict(category="output",
         question="What does `editDistance('kitten', 'sitting')` return?",
         options={"A": "3", "B": "2", "C": "4", "D": "5"},
         answer_key="A",
         verification_code="print(editDistance('kitten', 'sitting'))"),
    dict(category="variable_state",
         question="During `editDistance('kitten', 'sitting')`, what is the value of `edelta[3][3]` (the edit distance between the prefixes 'kit' and 'sit') once row i=3 has been fully computed?",
         options={"A": "1", "B": "0", "C": "2", "D": "3"},
         answer_key="A",
         verification_code=(
             "tbl = __trace_var(18, 'edelta', 5, lambda: editDistance('kitten', 'sitting'))\n"
             "print(tbl[3][3])"
         )),
    dict(category="loop_trace",
         question="How many total times is `edelta_evaluate` called (line 20) during `editDistance('kitten', 'sitting')`?",
         options={"A": "56", "B": "49", "C": "42", "D": "63"},
         answer_key="A",
         verification_code="print(__trace_hits(20, lambda: editDistance('kitten', 'sitting')))"),
    dict(category="control_flow",
         question="When `edelta_evaluate` is called with `i=0` (e.g. `edelta_evaluate(None, 0, 3, 'kitten', 'sitting')`), which branch executes?",
         options={
             "A": "`i == 0` branch; returns `j` (line 3)",
             "B": "`j == 0` branch; returns `i`",
             "C": "Computes repcost and returns min(...)",
             "D": "Raises an IndexError",
         },
         answer_key="A",
         verification_code=(
             "counts = __trace_lines([3, 5, 12], lambda: edelta_evaluate(None, 0, 3, 'kitten', 'sitting'))\n"
             "print('`i == 0` branch; returns `j` (line 3)' if counts[3] > 0 else 'OTHER')"
         )),
]

QUESTIONS[18] = [
    dict(category="output",
         question="What does `LCM(48, 18)` return?",
         options={"A": "144.0", "B": "144", "C": "72.0", "D": "288.0"},
         answer_key="A",
         verification_code="print(LCM(48, 18))"),
    dict(category="variable_state",
         question="During `LCM(48, 18)`'s recursive `GCD` calls, what is the value of parameter `b` the 2nd time `GCD`'s body executes (i.e. the first recursive call)?",
         options={"A": "12", "B": "18", "C": "6", "D": "48"},
         answer_key="A",
         verification_code="print(__trace_var(5, 'b', 2, lambda: LCM(48, 18)))"),
    dict(category="loop_trace",
         question="How many total times is `GCD` called (including the initial call) to compute `LCM(48, 18)`?",
         options={"A": "3", "B": "2", "C": "4", "D": "1"},
         answer_key="A",
         verification_code="print(__trace_hits(5, lambda: LCM(48, 18)))"),
    dict(category="control_flow",
         question="In the final recursive call of computing `LCM(48, 18)` (where `a % b == 0`), which branch executes?",
         options={
             "A": "Condition `(a % b) == 0` is True; returns `b` directly (line 6)",
             "B": "Condition is False; recurses again",
             "C": "Raises a ZeroDivisionError",
             "D": "Infinite recursion",
         },
         answer_key="A",
         verification_code=(
             "counts = __trace_lines([6], lambda: LCM(48, 18))\n"
             "print('Condition `(a % b) == 0` is True; returns `b` directly (line 6)' if counts[6] > 0 else 'OTHER')"
         )),
]

QUESTIONS[19] = [
    dict(category="output",
         question=(
             "A `ListToSort` wraps a Python list and supports Swap/Larger/Smaller/Equal/Length. "
             "Build `ListToSort([5, 3, 4, 1, 2])` and call `listSorter` on it. What is the "
             "final sorted order of its underlying list?"
         ),
         options={"A": "[1, 2, 3, 4, 5]", "B": "[1, 2, 3, 5, 4]", "C": "[5, 4, 3, 2, 1]", "D": "[1, 2, 4, 3, 5]"},
         answer_key="A",
         verification_code=(
             "obj = ListToSort([5, 3, 4, 1, 2])\n"
             "listSorter(obj)\n"
             "print(obj.to_list())"
         )),
    dict(category="variable_state",
         question="With `ListToSort([5, 3, 4, 1, 2])`, what is the underlying list right after the first outer pass (i=0) of `listSorter` completes (i.e. at the start of i=1)?",
         options={"A": "[1, 5, 3, 4, 2]", "B": "[1, 2, 3, 4, 5]", "C": "[5, 3, 4, 1, 2]", "D": "[1, 3, 5, 4, 2]"},
         answer_key="A",
         verification_code=(
             "obj = ListToSort([5, 3, 4, 1, 2])\n"
             "snap = __trace_var(3, 'listToSort', 2, lambda: listSorter(obj))\n"
             "print(snap._lst)"
         )),
    dict(category="loop_trace",
         question="How many total times does `Swap` get called (line 6) while sorting `ListToSort([5, 3, 4, 1, 2])` to completion?",
         options={"A": "8", "B": "9", "C": "7", "D": "10"},
         answer_key="A",
         verification_code=(
             "obj = ListToSort([5, 3, 4, 1, 2])\n"
             "print(__trace_hits(7, lambda: listSorter(obj)))"
         )),
    dict(category="control_flow",
         question="If the input is already sorted, e.g. `ListToSort([1, 2, 3])`, which branch causes the function to exit via `break` (line 9)?",
         options={
             "A": "`noswap` remains True after the first pass, so `break` (line 9) executes",
             "B": "The inner loop never runs since Length()-1 == 0",
             "C": "An IndexError occurs",
             "D": "It still performs n-1 full passes without breaking",
         },
         answer_key="A",
         verification_code=(
             "obj = ListToSort([1, 2, 3])\n"
             "counts = __trace_lines([10], lambda: listSorter(obj))\n"
             "print(\"`noswap` remains True after the first pass, so `break` (line 9) executes\" if counts[10] > 0 else 'OTHER')"
         )),
]

QUESTIONS[20] = [
    dict(category="output",
         question="What does `calc(4, [[1, 2], [2, 3], [1, 3], [3, 4]])` return?",
         options={"A": "3", "B": "4", "C": "2", "D": "1"},
         answer_key="A",
         verification_code="print(calc(4, [[1, 2], [2, 3], [1, 3], [3, 4]]))"),
    dict(category="variable_state",
         question="For `calc(4, [[1, 2], [2, 3], [1, 3], [3, 4]])`, what is the DFS finishing order `endzeit_list` (as returned by the internal `dfs(knoten)` call) for this graph?",
         options={"A": "[4, 3, 2, 1]", "B": "[1, 2, 3, 4]", "C": "[1, 3, 2, 4]", "D": "[4, 2, 3, 1]"},
         answer_key="A",
         verification_code=(
             "N = 4; A = [[1, 2], [2, 3], [1, 3], [3, 4]]\n"
             "knoten = [KnotenImKopf(i) for i in range(N + 1)]\n"
             "for e in A:\n"
             "    knoten[e[0]].append_to_adj(e[1])\n"
             "print(dfs(knoten))"
         )),
    dict(category="loop_trace",
         question="How many total times is `dfs_visit` entered (counted via line 29, `u.farbe = \"g\"`) for `calc(4, [[1, 2], [2, 3], [1, 3], [3, 4]])`?",
         options={"A": "4", "B": "3", "C": "5", "D": "8"},
         answer_key="A",
         verification_code="print(__trace_hits(29, lambda: calc(4, [[1, 2], [2, 3], [1, 3], [3, 4]])))"),
    dict(category="control_flow",
         question="When node 1's second neighbor (node 3, already colored grey) is examined inside `dfs_visit`, which branch executes at `if v.farbe == \"w\":` (line 32)?",
         options={
             "A": "Condition is False (already visited); the recursive call is skipped",
             "B": "Condition is True; recurses into node 3 again",
             "C": "Raises a KeyError",
             "D": "Swaps the node's color back to white",
         },
         answer_key="A",
         verification_code=(
             "counts = __trace_lines([32, 34], lambda: calc(4, [[1, 2], [2, 3], [1, 3], [3, 4]]))\n"
             "print('Condition is False (already visited); the recursive call is skipped' if counts[32] > counts[34] else 'Condition is True; recurses into node 3 again')"
         )),
]

QUESTIONS[21] = [
    dict(category="output",
         question="Given `opt([3, 2, 5, 10, 7])`, what value does the function return?",
         options={"A": "15", "B": "13", "C": "17", "D": "12"},
         answer_key="A",
         verification_code="print(opt([3, 2, 5, 10, 7]))"),
    dict(category="variable_state",
         question="During `opt([3, 2, 5, 10, 7])`, what is the value of `best_incl` right after processing the 4th element (e=10), i.e. at the start of the 5th loop iteration (e=7)?",
         options={"A": "13", "B": "8", "C": "15", "D": "3"},
         answer_key="A",
         verification_code="print(__trace_var(5, 'best_incl', 5, lambda: opt([3, 2, 5, 10, 7])))"),
    dict(category="loop_trace",
         question="How many total iterations does `for e in W:` (line 5) run for `opt([3, 2, 5, 10, 7])`?",
         options={"A": "5", "B": "4", "C": "6", "D": "3"},
         answer_key="A",
         verification_code="print(__trace_hits(8, lambda: opt([3, 2, 5, 10, 7])))"),
    dict(category="control_flow",
         question="The file contains module-level `assert opt(...) == ...` statements below the function (lines 14-21), which already ran once when the file was loaded. If re-run, what happens?",
         options={
             "A": "They all pass silently since opt() produces the expected outputs",
             "B": "They raise an AssertionError on the first check",
             "C": "They are never executed",
             "D": "They raise a SyntaxError",
         },
         answer_key="A",
         verification_code=(
             "try:\n"
             "    assert opt([10, 2, 3, 4, 5]) == 18\n"
             "    assert opt([4, 9, 4]) == 9\n"
             "    assert opt([4, 7, 4]) == 8\n"
             "    assert opt([3, 2, 1]) == 4\n"
             "    assert opt([1, 2, 1, 4, 5]) == 7\n"
             "    assert opt([21, 2]) == 21\n"
             "    assert opt([5]) == 5\n"
             "    assert opt([30, 0, 0, 40]) == 70\n"
             "    print('They all pass silently since opt() produces the expected outputs')\n"
             "except AssertionError:\n"
             "    print('They raise an AssertionError on the first check')"
         )),
]

QUESTIONS[22] = [
    dict(category="output",
         question=(
             "Node objects have attributes key, left, right, parent. Build this tree: "
             "root(key=5) with left child (key=3) and right child (key=8); node(8) has left "
             "child (key=7) and right child (key=9); all parent links set accordingly. "
             "Call `delete(root, <the node with key 8>)`. What is the in-order traversal "
             "(list of keys) of the resulting tree?"
         ),
         options={"A": "[3, 5, 7, 9]", "B": "[3, 5, 7, 8, 9]", "C": "[3, 5, 9]", "D": "[3, 5, 8, 9]"},
         answer_key="A",
         verification_code=(
             "root = Node(); root.key = 5\n"
             "n3 = Node(); n3.key = 3; n3.parent = root; root.left = n3\n"
             "n8 = Node(); n8.key = 8; n8.parent = root; root.right = n8\n"
             "n7 = Node(); n7.key = 7; n7.parent = n8; n8.left = n7\n"
             "n9 = Node(); n9.key = 9; n9.parent = n8; n8.right = n9\n"
             "new_root = delete(root, n8)\n"
             "def inorder(n):\n"
             "    if n is None: return []\n"
             "    return inorder(n.left) + [n.key] + inorder(n.right)\n"
             "print(inorder(new_root))"
         )),
    dict(category="variable_state",
         question=(
             "Using the same tree, call `delete(root, <node with key 8>)`. What is the key "
             "of local variable `y` right after it is assigned?"
         ),
         options={"A": "9", "B": "8", "C": "7", "D": "5"},
         answer_key="A",
         verification_code=(
             "root = Node(); root.key = 5\n"
             "n3 = Node(); n3.key = 3; n3.parent = root; root.left = n3\n"
             "n8 = Node(); n8.key = 8; n8.parent = root; root.right = n8\n"
             "n7 = Node(); n7.key = 7; n7.parent = n8; n8.left = n7\n"
             "n9 = Node(); n9.key = 9; n9.parent = n8; n8.right = n9\n"
             "y_node = __trace_var(17, 'y', 1, lambda: delete(root, n8))\n"
             "print(y_node.key)"
         )),
    dict(category="loop_trace",
         question="Using the same tree, call `delete(root, root)` (deleting the root). How many times does the while-loop body `x = x.left` inside `TREE_MINIMUM` (line 5) execute?",
         options={"A": "1", "B": "0", "C": "2", "D": "3"},
         answer_key="A",
         verification_code=(
             "root = Node(); root.key = 5\n"
             "n3 = Node(); n3.key = 3; n3.parent = root; root.left = n3\n"
             "n8 = Node(); n8.key = 8; n8.parent = root; root.right = n8\n"
             "n7 = Node(); n7.key = 7; n7.parent = n8; n8.left = n7\n"
             "n9 = Node(); n9.key = 9; n9.parent = n8; n8.right = n9\n"
             "print(__trace_hits(5, lambda: delete(root, root)))"
         )),
    dict(category="control_flow",
         question="When deleting the node with key 8 (which has two children), which branch of the first if-statement executes?",
         options={
             "A": "Condition is False; executes `y = TREE_MINIMUM(delete.right)` (line 16)",
             "B": "Condition is True; executes `y = delete` (line 14)",
             "C": "Raises a ValueError",
             "D": "Skips directly to `return root` without computing y",
         },
         answer_key="A",
         verification_code=(
             "root = Node(); root.key = 5\n"
             "n3 = Node(); n3.key = 3; n3.parent = root; root.left = n3\n"
             "n8 = Node(); n8.key = 8; n8.parent = root; root.right = n8\n"
             "n7 = Node(); n7.key = 7; n7.parent = n8; n8.left = n7\n"
             "n9 = Node(); n9.key = 9; n9.parent = n8; n8.right = n9\n"
             "counts = __trace_lines([14, 16], lambda: delete(root, n8))\n"
             "print('Condition is False; executes `y = TREE_MINIMUM(delete.right)` (line 16)' if counts[16] > 0 else 'Condition is True; executes `y = delete` (line 14)')"
         )),
]

QUESTIONS[23] = [
    dict(category="output",
         question="What does `calc(4, [[1, 2], [2, 3], [1, 3], [3, 4]])` return?",
         options={"A": "3", "B": "4", "C": "2", "D": "1"},
         answer_key="A",
         verification_code="print(calc(4, [[1, 2], [2, 3], [1, 3], [3, 4]]))"),
    dict(category="variable_state",
         question="For `calc(4, [[1, 2], [2, 3], [1, 3], [3, 4]])`, what is the `dp` list right after the main DFS loop (lines 19-21) completes, right before the final max-reduction loop?",
         options={"A": "[0, 3, 2, 1, 0]", "B": "[0, 1, 2, 3, 0]", "C": "[0, 3, 2, 1, 1]", "D": "[0, 0, 0, 0, 0]"},
         answer_key="A",
         verification_code="print(__trace_var(23, 'dp', 1, lambda: calc(4, [[1, 2], [2, 3], [1, 3], [3, 4]])))"),
    dict(category="loop_trace",
         question="How many total times is `dfs` called (counted via line 2, `vis[node] = True`) for `calc(4, [[1, 2], [2, 3], [1, 3], [3, 4]])`?",
         options={"A": "4", "B": "5", "C": "3", "D": "2"},
         answer_key="A",
         verification_code="print(__trace_hits(2, lambda: calc(4, [[1, 2], [2, 3], [1, 3], [3, 4]])))"),
    dict(category="control_flow",
         question="When `dfs(1, ...)` processes its second neighbor (node 3, already visited via node 2's chain), which branch executes at `if not vis[adj[node][i]]:` (line 5)?",
         options={
             "A": "Condition is False; skips the recursive call, but still updates `dp[node]` at line 8",
             "B": "Condition is True; recurses into node 3 again",
             "C": "Raises a RecursionError",
             "D": "Breaks out of the for loop early",
         },
         answer_key="A",
         verification_code=(
             "counts = __trace_lines([6, 8], lambda: calc(4, [[1, 2], [2, 3], [1, 3], [3, 4]]))\n"
             "print('Condition is False; skips the recursive call, but still updates `dp[node]` at line 8' if counts[8] > counts[6] else 'Condition is True; recurses into node 3 again')"
         )),
]

QUESTIONS[24] = [
    dict(category="output",
         question=(
             "Node objects have key/left/right/parent attributes. Starting from an empty "
             "tree (root=None), call `root = insert(root, <new Node key=10>)`, then "
             "`root = insert(root, <new Node key=5>)`, then `root = insert(root, <new Node key=15>)`. "
             "What is the in-order traversal (list of keys) of the final tree?"
         ),
         options={"A": "[5, 10, 15]", "B": "[10, 5, 15]", "C": "[15, 10, 5]", "D": "[5, 15, 10]"},
         answer_key="A",
         verification_code=(
             "n10 = Node(); n10.key = 10\n"
             "root = insert(None, n10)\n"
             "n5 = Node(); n5.key = 5\n"
             "root = insert(root, n5)\n"
             "n15 = Node(); n15.key = 15\n"
             "root = insert(root, n15)\n"
             "def inorder(n):\n"
             "    if n is None: return []\n"
             "    return inorder(n.left) + [n.key] + inorder(n.right)\n"
             "print(inorder(root))"
         )),
    dict(category="variable_state",
         question=(
             "Using the tree {10 (root), left=5, right=None}, call `insert(root, <new Node key=15>)`. "
             "What is the value of local variable `is_left_child` right after the while-loop exits?"
         ),
         options={"A": "False", "B": "True", "C": "None", "D": "15"},
         answer_key="A",
         verification_code=(
             "n10 = Node(); n10.key = 10\n"
             "root = insert(None, n10)\n"
             "n5 = Node(); n5.key = 5\n"
             "root = insert(root, n5)\n"
             "n15 = Node(); n15.key = 15\n"
             "print(__trace_var(15, 'is_left_child', 1, lambda: insert(root, n15)))"
         )),
    dict(category="loop_trace",
         question="Using the tree {10 (root), left=5, right=None}, how many times does the while-loop body (line 7) execute when calling `insert(root, <new Node key=15>)`?",
         options={"A": "1", "B": "2", "C": "0", "D": "3"},
         answer_key="A",
         verification_code=(
             "n10 = Node(); n10.key = 10\n"
             "root = insert(None, n10)\n"
             "n5 = Node(); n5.key = 5\n"
             "root = insert(root, n5)\n"
             "n15 = Node(); n15.key = 15\n"
             "print(__trace_hits(7, lambda: insert(root, n15)))"
         )),
    dict(category="control_flow",
         question="When inserting into an empty tree (`root=None`), which branch executes at the end of `insert`?",
         options={
             "A": "`before` remains None; executes `return target` (line 23)",
             "B": "Executes `return root` (line 21)",
             "C": "Raises an AttributeError",
             "D": "Loops forever since current is None",
         },
         answer_key="A",
         verification_code=(
             "n10 = Node(); n10.key = 10\n"
             "counts = __trace_lines([21, 23], lambda: insert(None, n10))\n"
             "print('`before` remains None; executes `return target` (line 23)' if counts[23] > 0 else 'Executes `return root` (line 21)')"
         )),
]


def shuffle_options(options, answer_key, seed):
    """Every question above was hand-authored with the correct option written
    as "A" (a shortcut while authoring, since verification only checks option
    TEXT against execution output, never the letter). Left as-is, that's a
    severe positional confound: a model could score ~99% just by always
    answering "A", regardless of comprehension. This deterministically
    permutes each question's option->letter assignment (seeded on the
    question's own id, so it's stable and reproducible) before anything is
    shown to a model or scored."""
    import random as _random
    letters = ["A", "B", "C", "D"]
    rng = _random.Random(seed)
    shuffled_letters = letters[:]
    rng.shuffle(shuffled_letters)
    # shuffled_letters[i] tells us which NEW letter the content currently at
    # old letters[i] should move to.
    new_options = {}
    new_answer_key = None
    for old_letter, new_letter in zip(letters, shuffled_letters):
        new_options[new_letter] = options[old_letter]
        if old_letter == answer_key:
            new_answer_key = new_letter
    return new_options, new_answer_key


def main():
    out = []
    for idx, sample in enumerate(samples):
        harness_code = HARNESS_BY_INDEX.get(idx, "")
        pre_harness_code = PRE_HARNESS_BY_INDEX.get(idx, "")
        qs = QUESTIONS[idx]
        for qi, q in enumerate(qs):
            qid = f"s{idx:02d}_q{qi}"
            options, answer_key = shuffle_options(q["options"], q["answer_key"], seed=qid)
            out.append({
                "id": qid,
                "sample_index": idx,
                "question_id": sample["question_id"],
                "student_id": sample["student_id"],
                "title_eng": sample["title_eng"],
                "category": q["category"],
                "question": q["question"],
                "options": options,
                "answer_key": answer_key,
                "verification_code": q["verification_code"],
                "solution_code": sample["solution_code"],
                "harness_code": harness_code,
                "pre_harness_code": pre_harness_code,
            })

    assert len(out) == 100, f"expected 100 questions, got {len(out)}"
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(out)} questions to {OUT_PATH}")
    cats = {}
    for q in out:
        cats[q["category"]] = cats.get(q["category"], 0) + 1
    print("Category counts:", cats)


if __name__ == "__main__":
    main()
