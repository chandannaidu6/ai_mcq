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

Models spanned open-source (run locally via vLLM on a single NVIDIA RTX
4000 Ada, 20 GB VRAM) and commercial API models (OpenAI and Anthropic,
via their batch APIs), each at **temperature 0**, and — where the model
supports it — at both a minimal/disabled and an enabled reasoning/thinking
setting, to isolate the effect of reasoning on this task.

## 5. Budget discipline (API models)

For every paid model/setting, real token usage was measured on a 20-question
sample *before* committing to the full run, and the full-scale cost was
projected from that measurement (never estimated from pricing alone). One
candidate model (a maximum-reasoning flagship) was found to cost roughly
9× the available budget with no cheaper mode available and was dropped in
favor of a comparably strong but affordable alternative in the same model
family. All paid calls used each provider's batch API (50% discount);
real per-call token usage was logged throughout, and the running total was
checked against the budget before every new submission.
