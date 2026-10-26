# Procedure

**Written for:** poster viewers (methods section).

## 1. Dataset

We used the *Dataset of Student Solutions to Algorithm and Data Structure
Programming Assignments* (Petersen-Frey, Soll, Kobras, Johannsen, Kling,
Biemann — LREC 2022, Universität Hamburg), which collects real, grader-passed
student submissions across three academic years (2019–2022) for 21 distinct
algorithms/data-structures assignments (recursion, dynamic programming,
graph search, trees, sorting, stacks/queues, etc.), each with authentic
Moodle/CodeRunner test cases. We restricted to **Python** solutions (687
available) and filtered out any requiring external files or `input()`
(none needed filtering in practice). We randomly sampled **185 solutions**
(seed 42), spread as evenly as possible across all 21 tasks (round-robin
by task) to maximize topic coverage.

## 2. Question generation

For each sampled solution we generated multiple-choice questions across
**8 comprehension categories**: output, variable state, loop trace, control
flow, call count, edge case, code modification, and data-structure state.
Generation was template-based and fully automated (comparable to tools like
AutoMCQ): for each (solution, category) pair, a generator script used Python
`ast` analysis to locate the relevant construct (a loop, branch, function
call, assignment) and the dataset's own grading test cases
(`tests.csv` testcode/expected pairs, already validated against real student
code) as grounding for realistic inputs. A category was skipped for a given
solution when it did not apply (e.g. no loop to ask about), and every skip
was logged with a reason. Critically, **the generator never executed the
student's code to check its own proposed answer before saving** — answer
keys were written in a single pass, exactly as an automated tool would,
so that generation errors would surface honestly in the next step rather
than being silently corrected.

This produced **996 questions** (4 options each, one marked as the
generator's best guess at the correct answer).

### 2a. How each category's verification snippet ("checker") was built

Every question carries a `verification_code` snippet that, when run after
the student's (or a modified copy of the student's) code, prints the true
answer — this is the checker used in Step 3. Two shared primitives underlie
all 8 categories:

- **`build_call_fn_source()`** — AST-rewrites a dataset test's final
  `print(expr)` statement into `return expr`, producing a zero-argument
  function `__cf()` that can be executed under a tracer.
- **Three generic tracers**, all built on Python's `sys.settrace`:
  `__trace_hits(line, __cf)` counts how many times a given source line
  executes during the call; `__trace_lines([line1, line2], __cf)` does the
  same for several lines at once; `__trace_var(line, name, occurrence,
  __cf)` snapshots a local variable's value (via `copy.deepcopy`, so later
  mutation of the same object can't corrupt the snapshot) the Nth time a
  given line is reached.

| Category | Checker construction |
|---|---|
| `output` | The dataset's own real `testcode` from `tests.csv`, run **verbatim** — no synthesis. |
| `data_structure_state` | Same as `output`, restricted to candidate tests whose `expected` value parses (`ast.literal_eval`) as a `list` or `dict`. |
| `edge_case` | If a dataset test already looks like an edge case (literal markers such as `[]`, `= None`, `(0,`) in its testcode, run it verbatim under `try/except`, printing the real output or `"Raises " + type(e).__name__`. Otherwise, AST-mutate one literal argument of an existing test to an edge value (list→`[]`, int→`0`, str→`""`) and run that under the same `try/except`. |
| `code_modification` | Run the dataset's real testcode against a **mechanically altered copy of the student's code**: the first comparison operator found is flipped (`<`↔`>`, `==`↔`!=`, etc. via `ast.NodeTransformer`); if none exists, the first non-trivial integer literal is incremented by 1. |
| `loop_trace` | `build_call_fn_source` + `print(__trace_hits(line, __cf))`, where `line` is the first statement inside the function's first `for`/`while` loop (located via AST). |
| `call_count` | Same pattern, with `line` = the function's own first body statement, so each invocation (including every recursive re-entry) re-executes it exactly once — the hit count *is* the call count. |
| `variable_state` | Same pattern, `print(__trace_var(return_line, var_name, 1, __cf))`, where `var_name` is the last simple `x = ...` assignment found (via AST) textually before the function's `return`. |
| `control_flow` | Same pattern, `__trace_lines([if_body_line, else_body_line], __cf)` on the first `if` statement found in the function — whichever line is hit identifies the branch taken, and the checker prints that branch's text label. |

For the four categories without a pre-existing dataset test to ground them
(`loop_trace`, `control_flow`, `call_count`, `variable_state`, and the
fallback path of `edge_case`), the generator's proposed *answer* is a naive,
unverified heuristic guess (e.g. "assume no recursion" for `call_count`),
while the *checker* itself always genuinely executes the real code via
`sys.settrace` — the guess and the checker are independent, which is
exactly why Step 3 can and does catch the generator's guess being wrong.

## 3. Execution-based verification

Every question's true answer was established by actually running the
student's code: the solution (or, for "code modification" questions, a
mechanically modified copy — e.g. a comparison operator flipped) was
executed together with a small verification snippet in an isolated
subprocess (5-second timeout, network access disabled), and the printed
result was matched against the four options. This gave:

- **759/996 questions (76%) with a verifiable, execution-grounded answer**
  (the rest were excluded from accuracy scoring but counted and reported —
  e.g. a category that had no applicable test case to drive it, or an
  execution error on an intentionally-broken modified solution);
- **146 of the generator's own answer keys (19.2% of verifiable questions)
  were wrong** when checked against execution. These were left uncorrected
  — this rate is itself a finding about automated MCQ generation, not a bug
  to silently fix.

One real bug was found and fixed mid-study: some dataset test cases check
coding-style constraints (e.g. "the source never calls `eval`") rather than
exercising the algorithm — the generator initially treated these as valid
inputs, which made ~26% of execution-trace questions (loop/branch/call-count
questions) meaningless, since the traced code was never actually reached.
These were excluded, and the full pipeline was re-run.

## 4. Answering models

Each model was shown **only** the student's code (plus any minimal support
class the task's grader provides, filtered to exclude anything not actually
referenced — so a bundled reference solution found in one task's grading
harness could never leak the answer), the question, and the four options,
using the model's native chat template, and asked to respond with a single
letter. Responses were parsed with a regex tolerant of common formats
("A", "(A)", "Answer: A"); anything that didn't resolve to A–D was scored
as invalid, separately from wrong.

The final comparison evaluates **7 commercial model/settings** across two
providers — OpenAI (GPT-6 Luna at minimal and enabled reasoning; GPT-6
Astra, the top-of-family model by price, at its minimum available
reasoning setting) and Anthropic (Claude Haiku 5.5 and Claude Opus 5, each
with thinking disabled and enabled) — each called at **temperature 0**
via the provider's batch API. (An earlier phase of this project also ran
4 open-source models locally via vLLM on a single NVIDIA RTX 4000 Ada GPU
for comparison; those results are not part of the final commercial-only
comparison reported here and were removed from `results/` per request,
though the answering pipeline that produced them is unchanged and
re-runnable.)

## 5. Budget discipline (API models)

For every paid model/setting, real token usage was measured on a 20-question
sample *before* committing to the full run, and the full-scale cost was
projected from that measurement (never estimated from pricing alone). One
candidate model (`gpt-5.5-pro`, OpenAI's flagship reasoning model, which
only accepts medium/high/xhigh reasoning effort — no cheaper mode) was
projected at roughly **9× the available budget (~$84)** on this basis and
was dropped before any full run, in favor of `gpt-6-astra` — a comparably
strong but far more affordable model in the same family. All paid calls
used each provider's batch API (50% discount); real per-call token usage
was logged throughout (`results/cost_log.csv`), and the running total was
checked against the budget before every new submission. **Actual total
spend across both providers: $6.78**, against a combined $10 cap.
